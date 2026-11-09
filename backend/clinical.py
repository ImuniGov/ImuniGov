import hashlib
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import insert, select, update

from . import db
from . import schemas as s
from . import security as sec
from .access import document, one, person
from .domain import event, notify, now, recalculate, schedule, uid

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
        document(con, identifier, user)
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
                dict(r)
                for r in con.execute(
                    select(db.vaccinations).where(db.vaccinations.c.document_id == identifier)
                ).mappings()
            ]
        }


@router.post("/api/v1/documents/{identifier}/candidates", status_code=201)
def manual_candidate(identifier: str, body: s.Candidate, request: Request, user=User):
    sec.role(user, "ubs")
    with request.app.state.engine.begin() as con:
        item, dependent = document(con, identifier, user)
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
                dict(r)
                for r in con.execute(
                    select(db.vaccinations)
                    .where(db.vaccinations.c.dependent_id == identifier)
                    .order_by(db.vaccinations.c.dose_date.desc())
                ).mappings()
            ]
        }


@router.post("/api/v1/vaccinations/{identifier}/decision")
def decide_record(identifier: str, body: s.RecordDecision, request: Request, user=User):
    sec.role(user, "ubs")
    with request.app.state.engine.begin() as con:
        record = one(con, db.vaccinations, identifier)
        dependent = person(con, record["dependent_id"], user)
        if body.decision == "validado":
            if (
                not record["dose_date"]
                or record["dose_date"] > date.today().isoformat()
                or (dependent["birth_date"] and record["dose_date"] < dependent["birth_date"])
            ):
                raise HTTPException(400, "Revise a data do candidato antes de validar.")
            if (
                record["document_id"]
                and one(con, db.documents, record["document_id"])["status"] != "aprovado"
            ):
                raise HTTPException(409, "Confira e aprove a evidência antes de confirmar o registro.")
        result = con.execute(
            update(db.vaccinations)
            .where(db.vaccinations.c.id == identifier, db.vaccinations.c.status == "a_conferir")
            .values(status=body.decision, reviewer_id=user["id"], review_note=body.note, reviewed_at=now())
        )
        if not result.rowcount:
            raise HTTPException(409, "Registro já recebeu decisão.")
        event(con, user["id"], "vaccination", identifier, body.decision, body.note)
        recalculate(con, record["dependent_id"], user["id"])
        notify(
            con,
            dependent["owner_id"],
            f"vaccination:{identifier}:{body.decision}",
            "Um registro foi conferido pela UBS. Consulte o histórico.",
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
        return {
            "items": [
                dict(r)
                for r in con.execute(
                    select(db.pendings, db.rules.c.version.label("rule_version"), db.rules.c.source)
                    .join(db.rules, db.rules.c.id == db.pendings.c.rule_set_id)
                    .where(db.pendings.c.dependent_id == identifier)
                    .order_by(db.pendings.c.updated_at.desc())
                ).mappings()
            ]
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
        if active:
            for dependent in con.execute(
                select(db.dependents).where(db.dependents.c.owner_id == user["id"])
            ).mappings():
                records = (
                    con.execute(
                        select(db.vaccinations).where(db.vaccinations.c.dependent_id == dependent["id"])
                    )
                    .mappings()
                    .all()
                )
                for item in schedule(dependent["birth_date"], records, active):
                    items.append({**item, "dependentId": dependent["id"], "dependent": dependent["name"]})
        return {
            "items": sorted(items, key=lambda i: (i["dueDate"], i["dependent"])),
            "coverage": {
                "version": active["version"] if active else None,
                "valid": bool(
                    active and active["valid_from"] <= date.today().isoformat() <= active["valid_until"]
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
        return {"item": item}


@router.get("/api/v1/dependents/{identifier}/guidance")
def guidance(identifier: str, request: Request, user=User):
    with request.app.state.engine.connect() as con:
        person(con, identifier, user)
        query = (
            select(db.guidance)
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
        for pending in con.execute(
            select(db.pendings).where(db.pendings.c.status == status).order_by(db.pendings.c.updated_at)
        ).mappings():
            dependent = one(con, db.dependents, pending["dependent_id"])
            owner = one(con, db.users, dependent["owner_id"]) if dependent["owner_id"] else None
            if q.lower() not in dependent["name"].lower():
                continue
            items.append(
                {
                    "id": pending["id"],
                    "dependent": dependent["name"],
                    "guardian": owner["name"] if owner else "Vínculo pendente",
                    "contact": owner["email"] if owner else "",
                    "reason": "Possível pendência vacinal requer acompanhamento da UBS.",
                    "priority": "alta"
                    if (date.today() - date.fromisoformat(pending["updated_at"][:10])).days >= 30
                    else "normal",
                    "updated_at": pending["updated_at"],
                }
            )
        return {"items": items}


@router.get("/api/v1/acs/cases/{identifier}/actions")
def contacts(identifier: str, request: Request, user=User):
    sec.role(user, "acs", "ubs")
    with request.app.state.engine.connect() as con:
        one(con, db.pendings, identifier)
        return {
            "items": [
                dict(r)
                for r in con.execute(
                    select(db.actions)
                    .where(db.actions.c.pending_id == identifier)
                    .order_by(db.actions.c.created_at.desc())
                ).mappings()
            ]
        }


@router.post("/api/v1/acs/cases/{identifier}/actions", status_code=201)
def add_contact(identifier: str, body: s.Contact, request: Request, user=User):
    sec.role(user, "acs")
    with request.app.state.engine.begin() as con:
        pending = one(con, db.pendings, identifier)
        if pending["status"] != "aberta":
            raise HTTPException(409, "Caso resolvido; consulte o histórico.")
        item = dict(
            id=uid(),
            pending_id=identifier,
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
            ]:
                rows = [
                    dict(r)
                    for r in con.execute(
                        select(table).where(table.c.dependent_id == dependent["id"])
                    ).mappings()
                ]
                for row in rows:
                    row.pop("stored_name", None)
                item[name] = rows
            result["dependents"].append(item)
        event(con, user["id"], "user", user["id"], "dados_exportados")
        return result
