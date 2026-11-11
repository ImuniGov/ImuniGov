import hashlib
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import insert, select, update

from . import clock, db
from . import schemas as s
from . import security as sec
from .access import document, one, person
from .consents import allowed
from .domain import event, individual_schedule, notify, now, recalculate, schedule, uid
from .reviews import cast_vote, declare_impediment, historical_votes, lock_roster, require_assignment, summary

router = APIRouter()
User = Depends(sec.session_user)


@router.get("/api/v1/documents/{identifier}/processing")
def processing(identifier: str, request: Request, user=User):
    with request.app.state.engine.connect() as con:
        document(con, identifier, user)
        job = con.execute(select(db.jobs).where(db.jobs.c.document_id == identifier)).mappings().first()
        return {
            "item": {k: job[k] for k in ("id", "status", "attempts", "error", "updated_at")} if job else None
        }


@router.post("/api/v1/documents/{identifier}/retry")
def retry(identifier: str, request: Request, user=User):
    sec.role(user, "ubs")
    with request.app.state.engine.begin() as con:
        item, _ = document(con, identifier, user)
        if item["review_hold"]:
            raise HTTPException(
                409, "Conferência suspensa por impedimento após voto. Aguarde a resolução administrativa."
            )
        result = con.execute(
            update(db.jobs)
            .where(db.jobs.c.document_id == identifier, db.jobs.c.status.in_(["failed", "unreadable"]))
            .values(status="queued", attempts=0, error="", updated_at=now())
        )
        if not result.rowcount:
            raise HTTPException(409, "Não há processamento com falha para repetir.")
        event(con, user["id"], "document", identifier, "ocr_reagendado")
    return {"ok": True}


@router.get("/api/v1/documents/{identifier}/extractions")
def extractions(identifier: str, request: Request, user=User):
    with request.app.state.engine.connect() as con:
        document(con, identifier, user)
        return {
            "items": [
                {
                    **dict(r),
                    "review": summary(
                        con,
                        r["document_id"],
                        "vaccination",
                        r["id"],
                        user,
                        terminal=r["status"] != "a_conferir",
                    ),
                }
                for r in con.execute(
                    select(db.vaccinations, db.users.c.name.label("reviewer_name"))
                    .outerjoin(db.users, db.users.c.id == db.vaccinations.c.reviewer_id)
                    .where(db.vaccinations.c.document_id == identifier)
                ).mappings()
            ]
        }


@router.post("/api/v1/documents/{identifier}/candidates", status_code=201)
def manual_candidate(identifier: str, body: s.Candidate, request: Request, user=User):
    sec.role(user, "ubs")
    with request.app.state.engine.begin() as con:
        item, dependent = document(con, identifier, user)
        if item["review_hold"]:
            raise HTTPException(
                409, "Conferência suspensa por impedimento após voto. Aguarde a resolução administrativa."
            )
        if dependent["birth_date"] and body.doseDate.isoformat() < dependent["birth_date"]:
            raise HTTPException(400, "Data anterior ao nascimento.")
        key = hashlib.sha256(f"{identifier}:{body.vaccine}:{body.dose}:{body.doseDate}".encode()).hexdigest()
        record = dict(
            id=uid(),
            dependent_id=dependent["id"],
            document_id=identifier,
            vaccine=body.vaccine,
            dose=body.dose,
            dose_date=body.doseDate.isoformat(),
            status="a_conferir",
            origin="transcricao_ubs",
            confidence=None,
            source_key=key,
            reviewer_id=None,
            review_note="",
            created_at=now(),
            reviewed_at=None,
        )
        con.execute(insert(db.vaccinations).values(**record))
        event(con, user["id"], "vaccination", record["id"], "candidato_criado")
        recalculate(con, dependent["id"], user["id"])
        return {"item": record}


@router.get("/api/v1/dependents/{identifier}/vaccinations")
def history(identifier: str, request: Request, user=User):
    with request.app.state.engine.connect() as con:
        person(con, identifier, user)
        return {
            "items": [
                {
                    **dict(r),
                    "review": summary(
                        con,
                        r["document_id"],
                        "vaccination",
                        r["id"],
                        user,
                        terminal=r["status"] != "a_conferir",
                    ),
                }
                for r in con.execute(
                    select(db.vaccinations, db.users.c.name.label("reviewer_name"))
                    .outerjoin(db.users, db.users.c.id == db.vaccinations.c.reviewer_id)
                    .where(db.vaccinations.c.dependent_id == identifier)
                    .order_by(db.vaccinations.c.dose_date.desc())
                ).mappings()
            ]
        }


@router.post("/api/v1/vaccinations/{identifier}/decision")
def decide_record(identifier: str, body: s.RecordDecision, request: Request, user=User):
    sec.role(user, "ubs")
    with request.app.state.engine.begin() as con:
        lock_roster(con)
        record = one(con, db.vaccinations, identifier)
        dependent = person(con, record["dependent_id"], user)
        if body.decision == "validado":
            if (
                not record["dose_date"]
                or record["dose_date"] > clock.today().isoformat()
                or (dependent["birth_date"] and record["dose_date"] < dependent["birth_date"])
            ):
                raise HTTPException(400, "Revise a data do candidato antes de validar.")
            if (
                record["document_id"]
                and one(con, db.documents, record["document_id"])["status"] != "aprovado"
            ):
                raise HTTPException(409, "Confira e aprove a evidência antes de confirmar o registro.")
        require_assignment(con, record["document_id"], user)
        cast_vote(
            con,
            record["document_id"],
            "vaccination",
            identifier,
            "aprovar" if body.decision == "validado" else "recusar",
            body.note,
            body.guidance,
            user,
            body.independenceConfirmed,
            body.reviewRound,
        )
        return {"item": one(con, db.vaccinations, identifier)}


@router.get("/api/v1/vaccine-rules")
def rule_sets(request: Request, user=User):
    with request.app.state.engine.connect() as con:
        return {
            "items": [
                dict(r)
                for r in con.execute(select(db.rules).order_by(db.rules.c.created_at.desc())).mappings()
            ]
        }


@router.get("/api/v1/dependents/{identifier}/pendings")
def pending_list(identifier: str, request: Request, user=User):
    with request.app.state.engine.connect() as con:
        person(con, identifier, user)
        rows = [
            {
                **dict(r),
                "reason": r["reason"]
                if r["status"] == "aberta"
                else f"Motivo anterior (resolvido): {r['reason']}",
                "historical_reason": r["reason"] if r["status"] == "resolvida" else None,
                "evaluation_type": "calculo_automatico_sujeito_a_conferencia_ubs"
                if r["status"] == "aberta"
                else "conferida_e_resolvida_pela_ubs",
            }
            for r in con.execute(
                select(db.pendings, db.rules.c.version.label("rule_version"), db.rules.c.source)
                .join(db.rules, db.rules.c.id == db.pendings.c.rule_set_id)
                .where(db.pendings.c.dependent_id == identifier)
                .order_by(db.pendings.c.status.asc(), db.pendings.c.updated_at.desc())
            ).mappings()
        ]
        return {
            "items": rows,
            "open": [r for r in rows if r["status"] == "aberta"],
            "resolved": [r for r in rows if r["status"] == "resolvida"],
        }


@router.post("/api/v1/dependents/{identifier}/recalculate")
def recalc(identifier: str, request: Request, user=User):
    sec.role(user, "ubs")
    with request.app.state.engine.begin() as con:
        person(con, identifier, user)
        recalculate(con, identifier, user["id"])
    return {"ok": True}


@router.get("/api/v1/family/schedule")
def family_schedule(request: Request, user=User):
    sec.role(user, "familia")
    with request.app.state.engine.connect() as con:
        active = con.execute(select(db.rules).where(db.rules.c.active.is_(True))).mappings().first()
        items = []
        for dependent in con.execute(
            select(db.dependents).where(db.dependents.c.owner_id == user["id"])
        ).mappings():
            records = (
                con.execute(select(db.vaccinations).where(db.vaccinations.c.dependent_id == dependent["id"]))
                .mappings()
                .all()
            )
            individual = individual_schedule(con, dependent["id"])
            overrides = {(i["vaccine"], i["dose"]) for i in individual}
            routine = (
                [
                    i
                    for i in schedule(dependent["birth_date"], records, active)
                    if (i["vaccine"], i["dose"]) not in overrides
                ]
                if active and allowed(con, user["id"])
                else []
            )
            for item in routine + individual:
                items.append({**item, "dependentId": dependent["id"], "dependent": dependent["name"]})
        return {
            "items": sorted(items, key=lambda i: (i["dueDate"], i["dependent"])),
            "coverage": {
                "version": active["version"] if active else None,
                "source": active["source"] if active else None,
                "valid": bool(
                    active and active["valid_from"] <= clock.today().isoformat() <= active["valid_until"]
                ),
                "vaccines": sorted({r["vaccine"] for r in active["rules"]}) if active else [],
            },
        }


@router.post("/api/v1/pendings/{identifier}/guidance", status_code=201)
def add_guidance(identifier: str, body: s.Guidance, request: Request, user=User):
    sec.role(user, "ubs")
    with request.app.state.engine.begin() as con:
        pending = one(con, db.pendings, identifier)
        dependent = person(con, pending["dependent_id"], user)
        item = dict(
            id=uid(),
            pending_id=identifier,
            author_id=user["id"],
            text=body.text,
            released=body.released,
            created_at=now(),
        )
        con.execute(insert(db.guidance).values(**item))
        event(con, user["id"], "guidance", item["id"], "orientacao_registrada")
        if body.released:
            notify(
                con, dependent["owner_id"], f"guidance:{item['id']}", "Uma orientação da UBS está disponível."
            )
        return {"item": {**item, "author_name": user["name"]}}


@router.get("/api/v1/dependents/{identifier}/dose-plans")
def dose_plans(identifier: str, request: Request, user=User):
    with request.app.state.engine.connect() as con:
        person(con, identifier, user)
        return {
            "items": [
                dict(r)
                for r in con.execute(
                    select(db.dose_plans)
                    .where(db.dose_plans.c.dependent_id == identifier)
                    .order_by(db.dose_plans.c.created_at.desc())
                ).mappings()
            ]
        }


@router.post("/api/v1/dependents/{identifier}/dose-plans", status_code=201)
def add_dose_plan(identifier: str, body: s.DosePlan, request: Request, user=User):
    sec.role(user, "ubs")
    with request.app.state.engine.begin() as con:
        dependent = person(con, identifier, user)
        con.execute(select(db.dependents.c.id).where(db.dependents.c.id == identifier).with_for_update())
        if (
            dependent["birth_date"] and body.dueDate.isoformat() < dependent["birth_date"]
        ) or body.dueDate.year > clock.today().year + 20:
            raise HTTPException(400, "Data do acompanhamento inválida.")
        existing = con.execute(
            select(db.dose_plans.c.id).where(
                db.dose_plans.c.dependent_id == identifier,
                db.dose_plans.c.vaccine == body.vaccine,
                db.dose_plans.c.dose == body.dose,
                db.dose_plans.c.status == "ativa",
            )
        ).first()
        if existing:
            raise HTTPException(
                409, "Já há uma data ativa para esta vacina e dose. Cancele a anterior para registrar outra."
            )
        item = dict(
            id=uid(),
            dependent_id=identifier,
            vaccine=body.vaccine,
            dose=body.dose,
            due_date=body.dueDate.isoformat(),
            author_id=user["id"],
            note=body.note,
            status="ativa",
            created_at=now(),
            updated_at=now(),
            record_id=None,
        )
        con.execute(insert(db.dose_plans).values(**item))
        event(con, user["id"], "dose_plan", item["id"], "data_acompanhamento_registrada")
        recalculate(con, identifier, user["id"])
        return {"item": one(con, db.dose_plans, item["id"])}


@router.post("/api/v1/dose-plans/{identifier}/cancel")
def cancel_plan(identifier: str, body: s.CancelPlan, request: Request, user=User):
    sec.role(user, "ubs")
    with request.app.state.engine.begin() as con:
        plan = one(con, db.dose_plans, identifier)
        person(con, plan["dependent_id"], user)
        result = con.execute(
            update(db.dose_plans)
            .where(db.dose_plans.c.id == identifier, db.dose_plans.c.status == "ativa")
            .values(status="cancelada", updated_at=now())
        )
        if not result.rowcount:
            raise HTTPException(409, "Este acompanhamento não está ativo.")
        event(con, user["id"], "dose_plan", identifier, "data_acompanhamento_cancelada", body.note)
        recalculate(con, plan["dependent_id"], user["id"])
    return {"ok": True}


@router.get("/api/v1/dependents/{identifier}/guidance")
def guidance(identifier: str, request: Request, user=User):
    with request.app.state.engine.connect() as con:
        person(con, identifier, user)
        query = (
            select(
                db.guidance,
                db.users.c.name.label("author_name"),
                db.pendings.c.vaccine,
                db.pendings.c.dose,
            )
            .join(db.users, db.users.c.id == db.guidance.c.author_id)
            .join(db.pendings, db.pendings.c.id == db.guidance.c.pending_id)
            .where(db.pendings.c.dependent_id == identifier)
        )
        if user["role"] == "familia":
            query = query.where(db.guidance.c.released.is_(True))
        return {
            "items": [
                dict(r) for r in con.execute(query.order_by(db.guidance.c.created_at.desc())).mappings()
            ]
        }


@router.get("/api/v1/notifications")
def notifications(request: Request, user=User):
    with request.app.state.engine.connect() as con:
        return {
            "items": [
                dict(r)
                for r in con.execute(
                    select(db.notifications)
                    .where(db.notifications.c.user_id == user["id"])
                    .order_by(db.notifications.c.created_at.desc())
                ).mappings()
            ]
        }


@router.patch("/api/v1/notifications/{identifier}")
def read_notification(identifier: str, body: s.ReadNotification, request: Request, user=User):
    with request.app.state.engine.begin() as con:
        result = con.execute(
            update(db.notifications)
            .where(db.notifications.c.id == identifier, db.notifications.c.user_id == user["id"])
            .values(read=True)
        )
        if not result.rowcount:
            raise HTTPException(404, "Notificação não encontrada.")
    return {"ok": True}


@router.get("/api/v1/acs/cases")
def cases(request: Request, q: str = "", status: str = "aberta", user=User):
    sec.role(user, "acs", "ubs")
    if status not in ("aberta", "resolvida"):
        raise HTTPException(400, "Situação inválida.")
    with request.app.state.engine.connect() as con:
        items = []
        for case in con.execute(
            select(db.outreach_cases)
            .where(db.outreach_cases.c.status == status)
            .order_by(db.outreach_cases.c.updated_at)
        ).mappings():
            dependent = one(con, db.dependents, case["dependent_id"])
            if not allowed(con, dependent["owner_id"]):
                continue
            owner = one(con, db.users, dependent["owner_id"]) if dependent["owner_id"] else None
            if q.lower() not in (dependent["name"] + " " + (owner["name"] if owner else "")).lower():
                continue
            items.append(
                {
                    "id": case["id"],
                    "dependent": dependent["name"],
                    "guardian": owner["name"] if owner else "Vínculo pendente",
                    "contact": owner["email"] if owner else "",
                    "reason": "Acompanhamento com a UBS: possíveis pendências ou data de retorno ultrapassada."
                    if status == "aberta"
                    else "Acompanhamento resolvido; histórico de contatos preservado.",
                    "priority": "alta"
                    if (clock.today() - date.fromisoformat(case["updated_at"][:10])).days >= 30
                    else "normal",
                    "updated_at": case["updated_at"],
                }
            )
        return {"items": items}


@router.get("/api/v1/acs/cases/{identifier}/actions")
def contacts(identifier: str, request: Request, user=User):
    sec.role(user, "acs", "ubs")
    with request.app.state.engine.connect() as con:
        case = one(con, db.outreach_cases, identifier)
        dependent = one(con, db.dependents, case["dependent_id"])
        if not allowed(con, dependent["owner_id"], lock=True):
            raise HTTPException(403, "Acompanhamento digital pausado pela família.")
        query = (
            select(db.actions, db.users.c.name.label("author_name"))
            .join(db.users, db.users.c.id == db.actions.c.author_id)
            .where(db.actions.c.case_id == identifier)
            .order_by(db.actions.c.created_at.desc())
        )
        return {"items": [dict(row) for row in con.execute(query).mappings()]}


@router.post("/api/v1/acs/cases/{identifier}/actions", status_code=201)
def add_contact(identifier: str, body: s.Contact, request: Request, user=User):
    sec.role(user, "acs")
    with request.app.state.engine.begin() as con:
        case = one(con, db.outreach_cases, identifier)
        dependent = one(con, db.dependents, case["dependent_id"])
        if not allowed(con, dependent["owner_id"], lock=True):
            raise HTTPException(403, "Acompanhamento digital pausado pela família.")
        if case["status"] != "aberta":
            raise HTTPException(409, "Caso resolvido; consulte o histórico.")
        item = dict(
            id=uid(),
            pending_id=None,
            case_id=identifier,
            author_id=user["id"],
            kind=body.kind,
            note=body.note,
            contact_date=body.contactDate.isoformat(),
            created_at=now(),
        )
        con.execute(insert(db.actions).values(**item))
        event(con, user["id"], "outreach", identifier, "contato_registrado")
        return {"item": item}


@router.get("/api/v1/audit-events")
def audit_events(targetType: str, targetId: str, request: Request, user=User):
    sec.role(user, "ubs")
    with request.app.state.engine.begin() as con:
        event(con, user["id"], targetType, targetId, "auditoria_consultada")
        return {
            "items": [
                dict(r)
                for r in con.execute(
                    select(db.audit)
                    .where(db.audit.c.target_type == targetType, db.audit.c.target_id == targetId)
                    .order_by(db.audit.c.created_at)
                ).mappings()
            ]
        }


@router.get("/api/v1/privacy/export")
def export(request: Request, user=User):
    sec.role(user, "familia")
    with request.app.state.engine.begin() as con:
        people = (
            con.execute(select(db.dependents).where(db.dependents.c.owner_id == user["id"])).mappings().all()
        )
        result = {"user": sec.public_user(user), "privacyVersion": user["privacy_version"], "dependents": []}
        for dependent in people:
            item = dict(dependent)
            for name, table in [
                ("documents", db.documents),
                ("vaccinations", db.vaccinations),
                ("pendings", db.pendings),
                ("dosePlans", db.dose_plans),
            ]:
                rows = [
                    dict(r)
                    for r in con.execute(
                        select(table).where(table.c.dependent_id == dependent["id"])
                    ).mappings()
                ]
                for row in rows:
                    row.pop("stored_name", None)
                if name == "documents":
                    for row in rows:
                        row["reviewHistory"] = historical_votes(con, row["id"])
                item[name] = rows
            result["dependents"].append(item)
        event(con, user["id"], "user", user["id"], "dados_exportados")
        return result


@router.post("/api/v1/documents/{identifier}/impediment")
def impediment(identifier: str, body: s.Impediment, request: Request, user=User):
    sec.role(user, "ubs")
    with request.app.state.engine.begin() as con:
        lock_roster(con)
        document(con, identifier, user)
        result = declare_impediment(con, identifier, user, body.reason)
    return {"ok": True, **result}


@router.get("/api/v1/family/feedback")
def family_feedback(request: Request, user=User):
    sec.role(user, "familia")
    items = []
    with request.app.state.engine.connect() as con:
        for table, kind, pending in (
            (db.documents, "document", "pendente"),
            (db.vaccinations, "vaccination", "a_conferir"),
        ):
            query = (
                select(table, db.dependents.c.name.label("dependent"))
                .join(db.dependents, db.dependents.c.id == table.c.dependent_id)
                .where(db.dependents.c.owner_id == user["id"], table.c.status != pending)
            )
            for row in con.execute(query).mappings():
                document_id = row["id"] if kind == "document" else row["document_id"]
                review = summary(con, document_id, kind, row["id"], user, terminal=True)
                items.append(
                    {
                        "id": row["id"],
                        "kind": kind,
                        "documentId": document_id,
                        "dependentId": row["dependent_id"],
                        "dependent": row["dependent"],
                        "label": row["original_name"]
                        if kind == "document"
                        else f"{row['vaccine']} · Dose {row['dose']}",
                        "status": row["status"],
                        "reason": row["review_note"],
                        "nextStep": row["review_guidance"],
                        "at": row["reviewed_at"],
                        "reviewers": review["reviewers"],
                    }
                )
    return {"items": sorted(items, key=lambda i: i["at"] or "", reverse=True)}


@router.get("/api/v1/documents/{identifier}/review-history")
def review_history(identifier: str, request: Request, user=User):
    sec.role(user, "familia")
    with request.app.state.engine.connect() as con:
        item, _ = document(con, identifier, user)
        return {"items": historical_votes(con, identifier, before_round=item["review_round"])}
