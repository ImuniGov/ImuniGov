"""Three-person independent review with fail-closed cross-geographic allocation."""

import hashlib
import json
import secrets
from itertools import combinations

from fastapi import HTTPException
from sqlalchemy import insert, select, update

from . import db
from .domain import event, notify, now, recalculate, uid
from .geography import compatible, profile_snapshot

QUORUM = 3


def eligible_profiles(con):
    result = []
    query = (
        select(db.reviewer_profiles)
        .join(db.users, db.users.c.id == db.reviewer_profiles.c.user_id)
        .where(db.users.c.role == "ubs")
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


def assignments(con, document_id):
    return [
        dict(r)
        for r in con.execute(
            select(db.review_assignments).where(
                db.review_assignments.c.document_id == document_id, db.review_assignments.c.status == "ativa"
            )
        ).mappings()
    ]


def assign_document(con, document_id):
    con.execute(select(db.documents.c.id).where(db.documents.c.id == document_id).with_for_update())
    current = assignments(con, document_id)
    if len(current) == QUORUM:
        return current
    previously = set(
        con.scalars(
            select(db.review_assignments.c.reviewer_id).where(
                db.review_assignments.c.document_id == document_id
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
    for document_id in list(con.scalars(select(db.documents.c.id).order_by(db.documents.c.created_at))):
        if len(assignments(con, document_id)) < QUORUM:
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


def votes(con, target_type, target_id, active_only=True):
    query = (
        select(db.review_votes, db.review_assignments.c.reviewer_id, db.users.c.name.label("reviewer_name"))
        .join(db.review_assignments, db.review_assignments.c.id == db.review_votes.c.assignment_id)
        .join(db.users, db.users.c.id == db.review_assignments.c.reviewer_id)
        .where(db.review_votes.c.target_type == target_type, db.review_votes.c.target_id == target_id)
    )
    if active_only:
        query = query.where(db.review_assignments.c.status == "ativa")
    return [dict(r) for r in con.execute(query.order_by(db.review_votes.c.created_at)).mappings()]


def summary(con, document_id, target_type, target_id, user, terminal=False):
    panel = assignments(con, document_id)
    decisions = votes(con, target_type, target_id)
    own = next((v for v in decisions if v["reviewer_id"] == user["id"]), None)
    family = user["role"] == "familia"
    return {
        "required": QUORUM,
        "assigned": len(panel),
        "waitingForTeam": len(panel) < QUORUM,
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


def cast_vote(con, document_id, target_type, target_id, decision, note, guidance, user, independent):
    if not independent:
        raise HTTPException(400, "Confirme a declaração de independência ou informe um impedimento.")
    document = (
        con.execute(select(db.documents).where(db.documents.c.id == document_id).with_for_update())
        .mappings()
        .one()
    )
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
    snapshot = {"documentSha256": document["sha256"], "targetType": target_type, "targetId": target_id}
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
    decisions = votes(con, target_type, target_id)
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
