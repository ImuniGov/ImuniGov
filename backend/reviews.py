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
    if document["status"] == "rejeitado" or document["review_hold"]:
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
    if con.scalar(select(db.documents.c.review_hold).where(db.documents.c.id == document_id)):
        return assignments(con, document_id)
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
    doc = (
        con.execute(
            select(db.documents.c.review_round, db.documents.c.review_hold).where(
                db.documents.c.id == document_id
            )
        )
        .mappings()
        .one()
    )
    round_number = doc["review_round"]
    on_hold = bool(doc["review_hold"])
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
        "onHold": on_hold,
        "required": QUORUM,
        "assigned": len(panel),
        "waitingForTeam": not terminal and (on_hold or len(panel) < QUORUM),
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
    if document["review_hold"]:
        raise HTTPException(
            409, "Conferência suspensa por impedimento após voto. Aguarde a resolução administrativa."
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


def _record_late_incident(con, doc, assignment, reporter_id, reason, origin, administrative_ref):
    if con.execute(
        select(db.review_incidents.c.id).where(db.review_incidents.c.assignment_id == assignment["id"])
    ).first():
        raise HTTPException(409, "Impedimento pós-voto já registrado para esta atribuição.")
    incident_id = uid()
    con.execute(
        insert(db.review_incidents).values(
            id=incident_id,
            document_id=doc["id"],
            assignment_id=assignment["id"],
            reporter_id=reporter_id,
            source_round=doc["review_round"],
            reason=reason.strip(),
            origin=origin,
            administrative_ref=administrative_ref.strip(),
            created_at=now(),
        )
    )
    con.execute(
        update(db.review_assignments)
        .where(db.review_assignments.c.id == assignment["id"])
        .values(status="impedido")
    )
    if doc["status"] != "pendente":
        event(
            con,
            reporter_id,
            "document",
            doc["id"],
            "decisao_documento_suspensa_impedimento",
            json.dumps(
                {
                    "round": doc["review_round"],
                    "status": doc["status"],
                    "reviewer": doc["reviewer"],
                    "note": doc["review_note"],
                    "guidance": doc["review_guidance"],
                    "at": doc["reviewed_at"],
                },
                ensure_ascii=False,
            ),
        )
    con.execute(
        update(db.documents)
        .where(db.documents.c.id == doc["id"])
        .values(
            review_hold=True,
            status="pendente",
            reviewer="",
            review_note="",
            review_guidance="",
            reviewed_at=None,
        )
    )
    for rec in (
        con.execute(
            select(db.vaccinations).where(
                db.vaccinations.c.document_id == doc["id"],
                db.vaccinations.c.status != "a_conferir",
            )
        )
        .mappings()
        .all()
    ):
        event(
            con,
            reporter_id,
            "vaccination",
            rec["id"],
            "decisao_registro_suspensa_impedimento",
            json.dumps(
                {
                    "round": doc["review_round"],
                    "status": rec["status"],
                    "reviewer_id": rec["reviewer_id"],
                    "note": rec["review_note"],
                    "guidance": rec["review_guidance"],
                    "at": rec["reviewed_at"],
                },
                ensure_ascii=False,
            ),
        )
        con.execute(
            update(db.vaccinations)
            .where(db.vaccinations.c.id == rec["id"])
            .values(
                status="a_conferir",
                reviewer_id=None,
                review_note="",
                review_guidance="",
                reviewed_at=None,
            )
        )
        con.execute(
            update(db.dose_plans)
            .where(db.dose_plans.c.record_id == rec["id"], db.dose_plans.c.status == "concluida")
            .values(status="ativa", record_id=None, updated_at=now())
        )
    event(con, reporter_id, "assignment", assignment["id"], "impedimento_pos_voto_declarado", reason.strip())
    event(
        con,
        reporter_id,
        "document",
        doc["id"],
        "conferencia_suspensa_impedimento",
        f"Impedimento após voto ({origin}); conferência suspensa aguardando análise administrativa.",
    )
    dependent = (
        con.execute(select(db.dependents).where(db.dependents.c.id == doc["dependent_id"])).mappings().one()
    )
    recalculate(con, doc["dependent_id"], reporter_id)
    notify(
        con,
        dependent["owner_id"],
        f"review-hold:{doc['id']}:{incident_id}",
        f"{dependent['name']}: uma conferência foi suspensa por impedimento declarado após voto e aguarda nova equipe independente.",
    )
    return {"hold": True, "incidentId": incident_id}


def declare_impediment(con, document_id, user, reason):
    lock_roster(con)
    owner = con.scalar(
        select(db.dependents.c.owner_id)
        .join(db.documents, db.documents.c.dependent_id == db.dependents.c.id)
        .where(db.documents.c.id == document_id)
    )
    if owner:
        con.execute(select(db.users.c.id).where(db.users.c.id == owner).with_for_update())
    doc = (
        con.execute(select(db.documents).where(db.documents.c.id == document_id).with_for_update())
        .mappings()
        .one()
    )
    own = require_assignment(con, document_id, user)
    if con.execute(select(db.review_votes.c.id).where(db.review_votes.c.assignment_id == own["id"])).first():
        return _record_late_incident(
            con,
            doc,
            own,
            user["id"],
            reason,
            origin="profissional",
            administrative_ref="pendente_analise_administrativa",
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
    if not doc["review_hold"]:
        assign_document(con, document_id)
    return {"hold": False, "incidentId": None}


def report_incident(con, document_id, reviewer_email, administrative_ref, reason):
    if not 3 <= len(reason.strip()) <= 500 or not 3 <= len(administrative_ref.strip()) <= 200:
        raise ValueError("Informe motivo (3–500 caracteres) e referência administrativa (3–200).")
    lock_roster(con)
    owner = con.scalar(
        select(db.dependents.c.owner_id)
        .join(db.documents, db.documents.c.dependent_id == db.dependents.c.id)
        .where(db.documents.c.id == document_id)
    )
    if owner:
        con.execute(select(db.users.c.id).where(db.users.c.id == owner).with_for_update())
    doc = (
        con.execute(select(db.documents).where(db.documents.c.id == document_id).with_for_update())
        .mappings()
        .first()
    )
    if not doc:
        raise ValueError("Caderneta não encontrada.")
    reviewer_id = con.scalar(
        select(db.users.c.id).where(db.users.c.email == reviewer_email.lower(), db.users.c.role == "ubs")
    )
    if not reviewer_id:
        raise ValueError("Profissional não encontrado.")
    assignment = (
        con.execute(
            select(db.review_assignments).where(
                db.review_assignments.c.document_id == document_id,
                db.review_assignments.c.reviewer_id == reviewer_id,
                db.review_assignments.c.review_round == doc["review_round"],
            )
        )
        .mappings()
        .first()
    )
    if not assignment:
        raise ValueError("Profissional não pertence à rodada atual desta caderneta.")
    if not con.execute(
        select(db.review_votes.c.id).where(db.review_votes.c.assignment_id == assignment["id"])
    ).first():
        raise ValueError("Não há voto registrado nesta atribuição; use o impedimento antes do voto.")
    try:
        return _record_late_incident(
            con,
            doc,
            dict(assignment),
            reviewer_id,
            reason,
            origin="administracao",
            administrative_ref=administrative_ref,
        )
    except HTTPException as exc:
        raise ValueError(exc.detail) from exc


def resolve_incident(con, incident_id, administrative_ref, note):
    if not 3 <= len(note.strip()) <= 500 or not 3 <= len(administrative_ref.strip()) <= 200:
        raise ValueError("Informe nota de análise (3–500 caracteres) e referência administrativa (3–200).")
    lock_roster(con)
    incident = (
        con.execute(select(db.review_incidents).where(db.review_incidents.c.id == incident_id))
        .mappings()
        .first()
    )
    if not incident:
        raise ValueError("Ocorrência de impedimento não encontrada.")
    if con.execute(
        select(db.review_resolutions.c.id).where(db.review_resolutions.c.incident_id == incident_id)
    ).first():
        raise ValueError("Ocorrência já resolvida; histórico imutável.")
    document_id = incident["document_id"]
    owner = con.scalar(
        select(db.dependents.c.owner_id)
        .join(db.documents, db.documents.c.dependent_id == db.dependents.c.id)
        .where(db.documents.c.id == document_id)
    )
    if owner:
        con.execute(select(db.users.c.id).where(db.users.c.id == owner).with_for_update())
    con.execute(select(db.documents.c.id).where(db.documents.c.id == document_id).with_for_update())
    resolution_id = uid()
    con.execute(
        insert(db.review_resolutions).values(
            id=resolution_id,
            incident_id=incident_id,
            administrative_ref=administrative_ref.strip(),
            note=note.strip(),
            created_at=now(),
        )
    )
    event(
        con,
        None,
        "review_incident",
        incident_id,
        "impedimento_pos_voto_resolvido",
        f"{administrative_ref.strip()}: {note.strip()}",
    )
    unresolved = con.scalar(
        select(db.review_incidents.c.id)
        .outerjoin(db.review_resolutions, db.review_resolutions.c.incident_id == db.review_incidents.c.id)
        .where(
            db.review_incidents.c.document_id == document_id,
            db.review_resolutions.c.id.is_(None),
        )
        .limit(1)
    )
    if unresolved:
        return {
            "resolved": True,
            "resolutionId": resolution_id,
            "documentId": document_id,
            "hold": True,
        }
    con.execute(update(db.documents).where(db.documents.c.id == document_id).values(review_hold=False))
    restart_round(
        con,
        document_id,
        f"Impedimento pós-voto avaliado administrativamente ({administrative_ref.strip()}); nova rodada independente aberta.",
    )
    panel = assign_document(con, document_id)
    new_round = con.scalar(select(db.documents.c.review_round).where(db.documents.c.id == document_id))
    notify(
        con,
        owner,
        f"review-round:{document_id}:{new_round}",
        "O impedimento informado após voto foi analisado pela administração. Uma nova equipe independente conferirá a caderneta, preservando o histórico anterior.",
    )
    return {
        "resolved": True,
        "resolutionId": resolution_id,
        "documentId": document_id,
        "hold": False,
        "newRound": new_round,
        "assigned": len(panel),
        "waitingForTeam": len(panel) < QUORUM,
    }


def list_incidents(con, only_open=False):
    query = (
        select(
            db.review_incidents,
            db.users.c.email.label("reporter_email"),
            db.review_resolutions.c.id.label("resolution_id"),
            db.review_resolutions.c.administrative_ref.label("resolution_ref"),
            db.review_resolutions.c.note.label("resolution_note"),
            db.review_resolutions.c.created_at.label("resolved_at"),
        )
        .join(db.users, db.users.c.id == db.review_incidents.c.reporter_id)
        .outerjoin(db.review_resolutions, db.review_resolutions.c.incident_id == db.review_incidents.c.id)
        .order_by(db.review_incidents.c.created_at.desc())
    )
    if only_open:
        query = query.where(db.review_resolutions.c.id.is_(None))
    return [dict(r) for r in con.execute(query).mappings()]


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
