"""Three-person independent review with fail-closed cross-geographic allocation."""

import hashlib
import json
import secrets
from itertools import combinations

from fastapi import HTTPException
from sqlalchemy import insert, or_, select, update

from . import db
from .consents import allowed
from .domain import event, notify, now, recalculate, uid
from .geography import compatible, profile_snapshot

QUORUM = 3


def lock_roster(con):
    # A short write lock works on both PostgreSQL and SQLite; take it BEFORE owner/document locks.
    result = con.execute(
        update(db.review_gate)
        .where(db.review_gate.c.id == "roster")
        .values(revision=db.review_gate.c.revision)
    )
    if result.rowcount != 1:
        raise RuntimeError("Trava de revisão ausente; execute as migrações.")


def work_pending(con, document_id):
    document = con.execute(select(db.documents).where(db.documents.c.id == document_id)).mappings().one()
    if document["status"] == "rejeitado":
        return False
    return (
        document["status"] == "pendente"
        or bool(
            con.execute(
                select(db.vaccinations.c.id).where(
                    db.vaccinations.c.document_id == document_id, db.vaccinations.c.status == "a_conferir"
                )
            ).first()
        )
        or bool(
            con.execute(
                select(db.jobs.c.id).where(
                    db.jobs.c.document_id == document_id, db.jobs.c.status.in_(["queued", "processing"])
                )
            ).first()
        )
    )


def restart_round(con, document_id, reason):
    current = con.execute(select(db.documents).where(db.documents.c.id == document_id)).mappings().one()
    event(
        con,
        None,
        "document",
        document_id,
        "rodada_anterior_preservada",
        json.dumps(
            {
                "round": current["review_round"],
                "status": current["status"],
                "reviewer": current["reviewer"],
                "note": current["review_note"],
                "guidance": current["review_guidance"],
                "at": current["reviewed_at"],
            },
            ensure_ascii=False,
        ),
    )
    con.execute(
        update(db.review_assignments)
        .where(db.review_assignments.c.document_id == document_id, db.review_assignments.c.status == "ativa")
        .values(status="substituida")
    )
    con.execute(
        update(db.documents)
        .where(db.documents.c.id == document_id)
        .values(
            review_round=current["review_round"] + 1,
            status="pendente",
            reviewer="",
            review_note="",
            review_guidance="",
            reviewed_at=None,
        )
    )
    event(con, None, "document", document_id, "nova_rodada_independente", reason)


def eligible_profiles(con):
    result = []
    query = (
        select(db.reviewer_profiles)
        .join(db.users, db.users.c.id == db.reviewer_profiles.c.user_id)
        .where(db.users.c.role == "ubs", db.reviewer_profiles.c.active.is_(True))
    )
    for profile in con.execute(query).mappings():
        if not profile["verified_at"] or not profile["verification_ref"] or not profile["professional_id"]:
            continue
        try:
            result.append({"user_id": profile["user_id"], "snapshot": profile_snapshot(profile)})
        except ValueError:
            continue
    return result


def choose_panel(profiles, fixed=()):
    candidates = [
        p for p in profiles if all(compatible(p["snapshot"], other["profile_snapshot"]) for other in fixed)
    ]
    secrets.SystemRandom().shuffle(candidates)
    needed = QUORUM - len(fixed)
    if needed <= 0:
        return []
    if needed == 1:
        return candidates[:1]
    # Compatibility bitsets avoid cubic scans when many staff share the same UF.
    neighbors = [0] * len(candidates)
    for i, j in combinations(range(len(candidates)), 2):
        if compatible(candidates[i]["snapshot"], candidates[j]["snapshot"]):
            neighbors[i] |= 1 << j
            neighbors[j] |= 1 << i
            if needed == 2:
                return [candidates[i], candidates[j]]
    if needed == 3:
        for i, bits in enumerate(neighbors):
            remaining = bits & ~((1 << (i + 1)) - 1)
            while remaining:
                bit = remaining & -remaining
                j = bit.bit_length() - 1
                common = neighbors[i] & neighbors[j] & ~((1 << (j + 1)) - 1)
                if common:
                    k = (common & -common).bit_length() - 1
                    return [candidates[i], candidates[j], candidates[k]]
                remaining ^= bit
    return []


def assignments(con, document_id, round_number=None, include_inactive=False):
    if round_number is None:
        round_number = con.scalar(select(db.documents.c.review_round).where(db.documents.c.id == document_id))
    query = select(db.review_assignments).where(
        db.review_assignments.c.document_id == document_id,
        db.review_assignments.c.review_round == round_number,
    )
    if not include_inactive:
        query = query.where(db.review_assignments.c.status == "ativa")
    return [dict(r) for r in con.execute(query).mappings()]


def assign_document(con, document_id):
    lock_roster(con)
    owner = con.execute(
        select(db.dependents.c.owner_id)
        .join(db.documents, db.documents.c.dependent_id == db.dependents.c.id)
        .where(db.documents.c.id == document_id)
    ).scalar()
    if not allowed(con, owner, lock=True):
        return assignments(con, document_id)
    con.execute(select(db.documents.c.id).where(db.documents.c.id == document_id).with_for_update())
    if con.execute(
        select(db.review_assignments.c.id).where(
            db.review_assignments.c.document_id == document_id,
            db.review_assignments.c.review_round
            == con.scalar(select(db.documents.c.review_round).where(db.documents.c.id == document_id)),
            db.review_assignments.c.status == "retirada",
        )
    ).first() and work_pending(con, document_id):
        restart_round(con, document_id, "Equipe anterior alterada; novas conferências exigem nova rodada.")
    current = assignments(con, document_id)
    round_number = con.scalar(select(db.documents.c.review_round).where(db.documents.c.id == document_id))
    if len(current) == QUORUM:
        return current
    previously = set(
        con.scalars(
            select(db.review_assignments.c.reviewer_id).where(
                db.review_assignments.c.document_id == document_id,
                or_(
                    db.review_assignments.c.review_round == round_number,
                    db.review_assignments.c.status == "impedido",
                ),
            )
        )
    )
    profiles = [p for p in eligible_profiles(con) if p["user_id"] not in previously]
    chosen = choose_panel(profiles, current)
    if len(chosen) != QUORUM - len(current):
        return current  # Never assign a partial new panel or relax geography constraints.
    for profile in chosen:
        item = dict(
            id=uid(),
            document_id=document_id,
            reviewer_id=profile["user_id"],
            created_at=now(),
            status="ativa",
            profile_snapshot=profile["snapshot"],
            review_round=round_number,
        )
        con.execute(insert(db.review_assignments).values(**item))
        event(
            con,
            None,
            "document",
            document_id,
            "revisor_sorteado",
            "Regra: três revisores; município/UF/RM/RIDE/AU cruzados. Catálogo: "
            + profile["snapshot"]["catalogVersion"],
        )
        current.append(item)
    return current


def assign_waiting(con):
    lock_roster(con)
    for document_id in list(
        con.scalars(
            select(db.documents.c.id)
            .join(db.dependents, db.dependents.c.id == db.documents.c.dependent_id)
            .order_by(db.dependents.c.owner_id, db.documents.c.created_at)
        )
    ):
        if work_pending(con, document_id) and len(assignments(con, document_id)) < QUORUM:
            assign_document(con, document_id)


def require_assignment(con, document_id, user):
    if user["role"] != "ubs":
        return None
    own = next((a for a in assignments(con, document_id) if a["reviewer_id"] == user["id"]), None)
    if not own:
        raise HTTPException(403, "Esta caderneta é restrita aos profissionais sorteados para sua revisão.")
    return own


def require_complete_panel(con, document_id):
    panel = assignments(con, document_id)
    if len(panel) != QUORUM:
        raise HTTPException(
            409, "Aguardando três revisores elegíveis. As regras geográficas não serão flexibilizadas."
        )
    valid = {p["user_id"]: p for p in eligible_profiles(con)}
    for assignment in panel:
        profile = valid.get(assignment["reviewer_id"])
        if not profile or profile["snapshot"]["fingerprint"] != assignment["profile_snapshot"]["fingerprint"]:
            raise HTTPException(409, "A equipe precisa de nova conferência cadastral antes de votar.")
    if any(not compatible(a["profile_snapshot"], b["profile_snapshot"]) for a, b in combinations(panel, 2)):
        raise HTTPException(409, "A equipe não satisfaz a separação geográfica exigida.")
    return panel


def votes(con, target_type, target_id, active_only=True, round_number=None):
    query = (
        select(db.review_votes, db.review_assignments.c.reviewer_id, db.users.c.name.label("reviewer_name"))
        .join(db.review_assignments, db.review_assignments.c.id == db.review_votes.c.assignment_id)
        .join(db.users, db.users.c.id == db.review_assignments.c.reviewer_id)
        .where(db.review_votes.c.target_type == target_type, db.review_votes.c.target_id == target_id)
    )
    if round_number is not None:
        query = query.where(db.review_assignments.c.review_round == round_number)
    if active_only:
        query = query.where(db.review_assignments.c.status == "ativa")
    return [dict(r) for r in con.execute(query.order_by(db.review_votes.c.created_at)).mappings()]


def summary(con, document_id, target_type, target_id, user, terminal=False):
    round_number = con.scalar(select(db.documents.c.review_round).where(db.documents.c.id == document_id))
    if terminal:
        historical = votes(con, target_type, target_id, active_only=False)
        if historical:
            assignment_ids = [v["assignment_id"] for v in historical]
            round_number = max(
                con.scalars(
                    select(db.review_assignments.c.review_round).where(
                        db.review_assignments.c.id.in_(assignment_ids)
                    )
                )
            )
    panel = assignments(con, document_id, round_number, include_inactive=terminal)
    decisions = votes(con, target_type, target_id, active_only=not terminal, round_number=round_number)
    own = next((v for v in decisions if v["reviewer_id"] == user["id"]), None)
    family = user["role"] == "familia"
    return {
        "round": round_number,
        "required": QUORUM,
        "assigned": len(panel),
        "waitingForTeam": not terminal and len(panel) < QUORUM,
        "votesReceived": len(decisions) if family or terminal else None,
        "approvals": sum(v["decision"] == "aprovar" for v in decisions) if family or terminal else None,
        "myVote": {
            "decision": own["decision"],
            "note": own["note"],
            "guidance": own["guidance"],
            "created_at": own["created_at"],
        }
        if own and not family
        else None,
        "reviewers": [
            {
                "name": v["reviewer_name"],
                "decision": v["decision"],
                "note": v["note"],
                "guidance": v["guidance"],
                "at": v["created_at"],
            }
            for v in decisions
        ]
        if terminal
        else [],
    }


def cast_vote(
    con, document_id, target_type, target_id, decision, note, guidance, user, independent, expected_round
):
    lock_roster(con)
    if not independent:
        raise HTTPException(400, "Confirme a declaração de independência ou informe um impedimento.")
    owner = con.execute(
        select(db.dependents.c.owner_id)
        .join(db.documents, db.documents.c.dependent_id == db.dependents.c.id)
        .where(db.documents.c.id == document_id)
    ).scalar()
    if not allowed(con, owner, lock=True):
        raise HTTPException(403, "Acompanhamento digital pausado pela família.")
    document = (
        con.execute(select(db.documents).where(db.documents.c.id == document_id).with_for_update())
        .mappings()
        .one()
    )
    if document["review_round"] != expected_round:
        raise HTTPException(409, "A equipe ou a rodada mudou. Atualize a caderneta antes de votar novamente.")
    assignment = require_assignment(con, document_id, user)
    require_complete_panel(con, document_id)
    table = db.documents if target_type == "document" else db.vaccinations
    target = con.execute(select(table).where(table.c.id == target_id)).mappings().one()
    pending = "pendente" if target_type == "document" else "a_conferir"
    if target["status"] != pending:
        raise HTTPException(409, "Esta conferência já foi encerrada.")
    if con.execute(
        select(db.review_votes.c.id).where(
            db.review_votes.c.assignment_id == assignment["id"],
            db.review_votes.c.target_type == target_type,
            db.review_votes.c.target_id == target_id,
        )
    ).first():
        raise HTTPException(409, "Seu voto já foi registrado e não pode ser alterado.")
    if decision == "recusar" and (len(note.strip()) < 3 or len(guidance.strip()) < 3):
        raise HTTPException(400, "Informe o motivo da recusa e a providência que a família deve tomar.")
    snapshot = {
        "documentSha256": document["sha256"],
        "targetType": target_type,
        "targetId": target_id,
        "round": document["review_round"],
    }
    if target_type == "vaccination":
        snapshot.update(vaccine=target["vaccine"], dose=target["dose"], date=target["dose_date"])
    con.execute(
        insert(db.review_votes).values(
            id=uid(),
            assignment_id=assignment["id"],
            target_type=target_type,
            target_id=target_id,
            decision=decision,
            note=note or "Evidência conferida.",
            guidance=guidance,
            independence_confirmed=True,
            evidence_hash=hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest(),
            created_at=now(),
        )
    )
    event(con, user["id"], target_type, target_id, "voto_independente_" + decision, note)
    decisions = votes(con, target_type, target_id, round_number=document["review_round"])
    final_rejection = next((v for v in decisions if v["decision"] == "recusar"), None)
    approved = sum(v["decision"] == "aprovar" for v in decisions) == QUORUM
    if final_rejection or approved:
        if final_rejection:
            state = "rejeitado" if target_type == "document" else "recusado"
            final_note, final_guidance = final_rejection["note"], final_rejection["guidance"]
            reviewers = final_rejection["reviewer_name"]
        else:
            state = "aprovado" if target_type == "document" else "validado"
            final_note = "\n".join(v["reviewer_name"] + ": " + v["note"] for v in decisions)
            final_guidance = "\n".join(
                v["reviewer_name"] + ": " + v["guidance"] for v in decisions if v["guidance"]
            )
            reviewers = ", ".join(v["reviewer_name"] for v in decisions)
        values = dict(status=state, review_note=final_note, review_guidance=final_guidance, reviewed_at=now())
        values.update({"reviewer": reviewers} if target_type == "document" else {"reviewer_id": user["id"]})
        con.execute(update(table).where(table.c.id == target_id).values(**values))
        event(con, user["id"], target_type, target_id, "revisao_tripla_" + state, final_note)
        dependent = (
            con.execute(select(db.dependents).where(db.dependents.c.id == document["dependent_id"]))
            .mappings()
            .one()
        )
        notify(
            con,
            dependent["owner_id"],
            f"review:{target_type}:{target_id}:{state}",
            f"{dependent['name']}: a UBS {'devolveu uma evidência ou recusou um registro. Veja o motivo e a próxima providência em Retornos da UBS.' if final_rejection else 'concluiu a conferência independente. Consulte Retornos da UBS.'}",
        )
        if target_type == "vaccination":
            recalculate(con, document["dependent_id"], user["id"])
    return summary(con, document_id, target_type, target_id, user, terminal=bool(final_rejection or approved))


def declare_impediment(con, document_id, user, reason):
    lock_roster(con)
    con.execute(select(db.documents.c.id).where(db.documents.c.id == document_id).with_for_update())
    own = require_assignment(con, document_id, user)
    if con.execute(select(db.review_votes.c.id).where(db.review_votes.c.assignment_id == own["id"])).first():
        raise HTTPException(
            409,
            "Já existe voto seu neste caso. A equipe administrativa deve avaliar o impedimento sem apagar o histórico.",
        )
    con.execute(
        update(db.review_assignments).where(db.review_assignments.c.id == own["id"]).values(status="impedido")
    )
    event(con, user["id"], "assignment", own["id"], "impedimento_declarado", reason)
    event(
        con,
        None,
        "document",
        document_id,
        "redistribuicao_solicitada",
        "Um revisor declarou impedimento; novo sorteio respeitará todas as restrições.",
    )
    assign_document(con, document_id)


def change_reviewer(
    con, email, active, birth_city, work_city, verification_ref, reason, apply=False, expected_version=None
):
    """Administrative change, atomic with panel invalidation; original votes are never edited."""
    from sqlalchemy import delete

    from .geography import location

    if not 3 <= len(reason.strip()) <= 500 or not 3 <= len(verification_ref.strip()) <= 200:
        raise ValueError("Informe motivo (3–500 caracteres) e referência da verificação (3–200).")
    lock_roster(con)
    profile = dict(
        con.execute(
            select(db.reviewer_profiles)
            .join(db.users, db.users.c.id == db.reviewer_profiles.c.user_id)
            .where(db.users.c.email == email.lower(), db.users.c.role == "ubs")
        )
        .mappings()
        .one()
    )
    after = {
        **profile,
        "active": active,
        "birth_city_code": birth_city or profile["birth_city_code"],
        "work_city_code": work_city or profile["work_city_code"],
        "verified_at": now(),
        "verification_ref": verification_ref.strip(),
    }
    location(after["birth_city_code"])
    location(after["work_city_code"])
    affected = sorted(
        set(
            con.scalars(
                select(db.review_assignments.c.document_id).where(
                    db.review_assignments.c.reviewer_id == profile["user_id"],
                    db.review_assignments.c.status == "ativa",
                )
            )
        )
    )
    unfinished = [identifier for identifier in affected if work_pending(con, identifier)]
    result = {
        "apply": apply,
        "expectedVersion": profile_snapshot(profile)["fingerprint"],
        "unfinishedRoundsToRestart": len(unfinished),
        "completedDecisionsPreserved": len(affected) - len(unfinished),
        "active": active,
    }
    if not apply:
        return result
    if expected_version != result["expectedVersion"]:
        raise ValueError(
            "O perfil mudou ou falta a versão esperada. Revise uma nova prévia antes de aplicar."
        )
    con.execute(
        update(db.reviewer_profiles)
        .where(db.reviewer_profiles.c.id == profile["id"])
        .values(
            **{
                k: after[k]
                for k in ("active", "birth_city_code", "work_city_code", "verified_at", "verification_ref")
            }
        )
    )
    con.execute(
        insert(db.reviewer_changes).values(
            id=uid(),
            profile_id=profile["id"],
            before=profile,
            after=after,
            reason=reason.strip(),
            verification_ref=verification_ref.strip(),
            created_at=now(),
        )
    )
    con.execute(delete(db.sessions).where(db.sessions.c.user_id == profile["user_id"]))
    event(
        con,
        None,
        "reviewer_profile",
        profile["id"],
        "perfil_reverificado" if active else "perfil_suspenso",
        reason,
    )
    owners = list(
        con.scalars(
            select(db.dependents.c.owner_id)
            .join(db.documents, db.documents.c.dependent_id == db.dependents.c.id)
            .where(db.documents.c.id.in_(affected))
        )
    )
    if owners:
        con.execute(
            select(db.users.c.id).where(db.users.c.id.in_(owners)).order_by(db.users.c.id).with_for_update()
        ).all()
    for identifier in affected:
        owner = con.scalar(
            select(db.dependents.c.owner_id)
            .join(db.documents, db.documents.c.dependent_id == db.dependents.c.id)
            .where(db.documents.c.id == identifier)
        )
        # Same roster -> owner -> document lock order used by voting and allocation.
        con.execute(select(db.users.c.id).where(db.users.c.id == owner).with_for_update())
        con.execute(select(db.documents.c.id).where(db.documents.c.id == identifier).with_for_update())
        if identifier in unfinished:
            restart_round(
                con, identifier, "Alteração administrativa de profissional; rodadas anteriores preservadas."
            )
            assign_document(con, identifier)
            round_number = con.scalar(
                select(db.documents.c.review_round).where(db.documents.c.id == identifier)
            )
            notify(
                con,
                owner,
                f"review-round:{identifier}:{round_number}",
                "Uma conferência em andamento recebeu nova equipe. Os votos anteriores foram preservados; acompanhe a nova rodada na caderneta.",
            )
        else:
            con.execute(
                update(db.review_assignments)
                .where(
                    db.review_assignments.c.document_id == identifier,
                    db.review_assignments.c.reviewer_id == profile["user_id"],
                    db.review_assignments.c.status == "ativa",
                )
                .values(status="retirada")
            )
    return result


def historical_votes(con, document_id, before_round=None):
    query = (
        select(
            db.review_votes.c.id,
            db.review_votes.c.target_type,
            db.review_votes.c.note,
            db.review_votes.c.guidance,
            db.review_votes.c.decision,
            db.review_votes.c.created_at,
            db.review_assignments.c.review_round,
            db.users.c.name.label("professional"),
            db.vaccinations.c.vaccine,
            db.vaccinations.c.dose,
        )
        .join(db.review_assignments, db.review_assignments.c.id == db.review_votes.c.assignment_id)
        .join(db.users, db.users.c.id == db.review_assignments.c.reviewer_id)
        .outerjoin(
            db.vaccinations,
            (db.review_votes.c.target_type == "vaccination")
            & (db.review_votes.c.target_id == db.vaccinations.c.id),
        )
        .where(db.review_assignments.c.document_id == document_id)
    )
    if before_round is not None:
        query = query.where(db.review_assignments.c.review_round < before_round)
    return [
        dict(row)
        for row in con.execute(
            query.order_by(db.review_assignments.c.review_round, db.review_votes.c.created_at)
        ).mappings()
    ]
