import hashlib
import io
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from PIL import Image
from pypdf import PdfReader
from sqlalchemy import delete, func, insert, select, update

from . import clock, db
from . import schemas as s
from . import security as sec
from .access import document, one, person, public_document
from .consents import allowed, permitted_owner, state
from .domain import event, now, recalculate, uid
from .password_reset import redeem_reset_code
from .privacy import record_acceptance
from .reviews import assign_document, assign_waiting, cast_vote, lock_roster, next_review

router = APIRouter()
User = Depends(sec.session_user)
MAX_UPLOAD = 10 * 1024 * 1024


@router.post("/api/v1/auth/register", status_code=201)
def register(body: s.Register, request: Request, response: Response):
    engine = request.app.state.engine
    sec.rate_limit(engine, f"register:{request.client.host}", limit=10)
    user = dict(
        id=uid(),
        name=body.name,
        email=body.email,
        role="familia",
        password_hash=sec.hasher.hash(body.password),
        created_at=now(),
        privacy_version=body.termsVersion,
    )
    with engine.begin() as con:
        con.execute(insert(db.users).values(**user))
        record_acceptance(con, user["id"], body)
        user["privacy"] = state(con, user["id"])
        csrf = sec.start_session(con, user["id"], response, request.app.state.secure)
    return {"user": sec.public_user(user), "csrf": csrf}


@router.post("/api/v1/auth/login")
def login(body: s.Login, request: Request, response: Response):
    engine = request.app.state.engine
    sec.rate_limit(engine, f"login-ip:{request.client.host}")
    sec.rate_limit(engine, f"login-account:{body.email}", limit=10)
    with engine.begin() as con:
        user = con.execute(select(db.users).where(db.users.c.email == body.email)).mappings().first()
        valid = sec.verify(user["password_hash"] if user else None, body.password)
        if not user or not valid:
            raise HTTPException(401, "E-mail ou senha inválidos.")
        if user["role"] == "ubs":
            if con.scalar(
                select(db.reviewer_profiles.c.id).where(
                    db.reviewer_profiles.c.user_id == user["id"], db.reviewer_profiles.c.active.is_(False)
                )
            ):
                raise HTTPException(403, "Seu acesso profissional está suspenso. Procure a administração.")
            assign_waiting(con)
        # Coordinate with a password reset that may have happened during verification.
        password_hash = con.scalar(
            select(db.users.c.password_hash).where(db.users.c.id == user["id"]).with_for_update()
        )
        if password_hash != user["password_hash"]:
            raise HTTPException(401, "E-mail ou senha inválidos.")
        con.execute(
            delete(db.sessions).where(
                db.sessions.c.id == sec.token_hash(request.cookies.get("imuniguia_session", ""))
            )
        )
        user = dict(user)
        if user["role"] == "familia":
            user["privacy"] = state(con, user["id"])
        csrf = sec.start_session(con, user["id"], response, request.app.state.secure, remember=body.remember)
        event(con, user["id"], "user", user["id"], "login")
    return {"user": sec.public_user(user), "csrf": csrf}


@router.post("/api/v1/auth/reset-password", status_code=204)
def reset_password(body: s.ResetPassword, request: Request):
    engine = request.app.state.engine
    sec.rate_limit(engine, f"reset-ip:{request.client.host}", limit=10)
    redeem_reset_code(engine, body.code, body.password)


@router.get("/api/v1/me")
def me(user=User):
    return {"user": sec.public_user(user), "csrf": user["csrf"]}


@router.post("/api/v1/auth/logout", status_code=204)
def logout(request: Request, response: Response, user=User):
    with request.app.state.engine.begin() as con:
        con.execute(
            update(db.push_subscriptions)
            .where(
                db.push_subscriptions.c.session_id
                == sec.token_hash(request.cookies.get("imuniguia_session", ""))
            )
            .values(enabled=False)
        )
        con.execute(
            delete(db.sessions).where(
                db.sessions.c.id == sec.token_hash(request.cookies.get("imuniguia_session", ""))
            )
        )
        event(con, user["id"], "user", user["id"], "logout")
    response.delete_cookie("imuniguia_session", path="/")


@router.get("/api/dependents")
def dependents(request: Request, user=User):
    sec.role(user, "familia", "ubs")
    query = select(db.dependents).order_by(db.dependents.c.name)
    if user["role"] == "familia":
        query = query.where(db.dependents.c.owner_id == user["id"])
    else:
        query = (
            query.where(permitted_owner(db.dependents.c.owner_id))
            .join(db.documents, db.documents.c.dependent_id == db.dependents.c.id)
            .join(db.review_assignments, db.review_assignments.c.document_id == db.documents.c.id)
            .where(
                db.review_assignments.c.reviewer_id == user["id"], db.review_assignments.c.status == "ativa"
            )
            .distinct()
        )
    with request.app.state.engine.connect() as con:
        return {
            "items": [
                {
                    **dict(r),
                    "birthDate": r["birth_date"],
                    "document_count": con.scalar(
                        select(func.count())
                        .select_from(db.documents)
                        .where(db.documents.c.dependent_id == r["id"])
                    ),
                    "representationVerified": bool(
                        con.scalar(
                            select(func.count())
                            .select_from(db.audit)
                            .where(
                                db.audit.c.target_type == "dependent",
                                db.audit.c.target_id == r["id"],
                                db.audit.c.event == "representacao_familiar_verificada",
                            )
                        )
                    ),
                }
                for r in con.execute(query).mappings()
            ]
        }


@router.post("/api/dependents", status_code=201)
def add_dependent(body: s.Dependent, request: Request, user=User):
    sec.role(user, "familia")
    item = dict(
        id=uid(), owner_id=user["id"], name=body.name, birth_date=body.birthDate.isoformat(), created_at=now()
    )
    with request.app.state.engine.begin() as con:
        if not allowed(con, user["id"], lock=True):
            raise HTTPException(403, "Autorização para acompanhamento digital não está vigente.")
        con.execute(insert(db.dependents).values(**item))
        event(
            con,
            user["id"],
            "dependent",
            item["id"],
            "dependente_criado",
            "Responsável declarou titularidade ou representação legal.",
        )
        recalculate(con, item["id"], user["id"])
    return {
        "item": {
            **item,
            "birthDate": item["birth_date"],
            "document_count": 0,
            "representationVerified": False,
        }
    }


@router.patch("/api/dependents/{identifier}")
def edit_dependent(identifier: str, body: s.Dependent, request: Request, user=User):
    sec.role(user, "familia")
    with request.app.state.engine.begin() as con:
        person(con, identifier, user)
        con.execute(
            update(db.dependents)
            .where(db.dependents.c.id == identifier)
            .values(name=body.name, birth_date=body.birthDate.isoformat())
        )
        event(
            con,
            user["id"],
            "dependent",
            identifier,
            "dependente_atualizado",
            "Representação reafirmada pelo responsável.",
        )
        recalculate(con, identifier, user["id"])
    return {"ok": True}


@router.delete("/api/dependents/{identifier}", status_code=204)
def remove_dependent(identifier: str, request: Request, user=User):
    sec.role(user, "familia")
    with request.app.state.engine.begin() as con:
        person(con, identifier, user)
        for table in (db.documents, db.vaccinations, db.pendings):
            if con.scalar(select(func.count()).select_from(table).where(table.c.dependent_id == identifier)):
                raise HTTPException(
                    409, "Dependente possui histórico associado. Solicite avaliação de retenção à equipe."
                )
        con.execute(delete(db.dependents).where(db.dependents.c.id == identifier))
        event(con, user["id"], "dependent", identifier, "dependente_removido")


@router.get("/api/v1/review/next")
def next_review_document(request: Request, user=User):
    sec.role(user, "ubs")
    with request.app.state.engine.connect() as con:
        item = next_review(con, user["id"])
        return {
            "item": {"id": item["id"], "step": "arquivo" if item["status"] == "pendente" else "doses"}
            if item
            else None
        }


@router.get("/api/documents")
def documents(request: Request, status: str | None = None, user=User):
    sec.role(user, "familia", "ubs")
    if status and status not in ("pendente", "aprovado", "rejeitado"):
        raise HTTPException(400, "Filtro de status inválido.")
    query = select(db.documents).join(db.dependents, db.dependents.c.id == db.documents.c.dependent_id)
    if user["role"] == "familia":
        query = query.where(db.dependents.c.owner_id == user["id"])
    if user["role"] == "ubs":
        query = (
            query.where(permitted_owner(db.dependents.c.owner_id))
            .join(db.review_assignments, db.review_assignments.c.document_id == db.documents.c.id)
            .where(
                db.review_assignments.c.reviewer_id == user["id"], db.review_assignments.c.status == "ativa"
            )
        )
    if status:
        query = query.where(db.documents.c.status == status)
    with request.app.state.engine.connect() as con:
        return {
            "items": [
                public_document(dict(r), one(con, db.dependents, r["dependent_id"]), con, user)
                for r in con.execute(query.order_by(db.documents.c.created_at.desc())).mappings()
            ]
        }


def check_file(blob, mime):
    if not blob:
        raise HTTPException(400, "Arquivo vazio.")
    if len(blob) > MAX_UPLOAD:
        raise HTTPException(413, "O arquivo deve ter até 10 MB.")
    try:
        if mime in ("image/jpeg", "image/png", "image/webp"):
            with Image.open(io.BytesIO(blob)) as image:
                if Image.MIME.get(image.format) != mime or image.width * image.height > 40_000_000:
                    raise ValueError()
                image.verify()
        elif mime == "application/pdf":
            if not blob.lstrip().startswith(b"%PDF-"):
                raise ValueError()
            pdf = PdfReader(io.BytesIO(blob), strict=True)
            if pdf.is_encrypted or not 0 < len(pdf.pages) <= 10:
                raise ValueError()
        else:
            raise ValueError()
    except Exception as exc:
        raise HTTPException(
            415, "Envie JPG, PNG, WEBP ou PDF válido, sem senha e com até 10 páginas."
        ) from exc


@router.post("/api/documents", status_code=201)
async def upload(
    request: Request,
    dependentId: str = Form(...),
    vaccine: str = Form(..., max_length=80),
    doseDate: str = Form(""),
    note: str = Form("", max_length=500),
    file: UploadFile = File(...),
    user=User,
):
    sec.role(user, "familia")
    engine = request.app.state.engine
    sec.rate_limit(engine, f"upload:{user['id']}", limit=30, seconds=3600)
    with engine.connect() as con:
        dependent = person(con, dependentId, user)
    if not vaccine.strip():
        raise HTTPException(400, "Informe a vacina ou registro.")
    if doseDate:
        try:
            if date.fromisoformat(doseDate) > clock.today() or (
                dependent["birth_date"] and doseDate < dependent["birth_date"]
            ):
                raise ValueError()
        except ValueError as exc:
            raise HTTPException(400, "Data do registro inválida.") from exc
    blob = await file.read(MAX_UPLOAD + 1)
    check_file(blob, file.content_type)
    suffix = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "application/pdf": ".pdf"}[
        file.content_type
    ]
    stored = uid() + suffix
    path = request.app.state.data / "uploads" / stored
    path.write_bytes(blob)
    filename = Path((file.filename or "caderneta").replace("\\", "/")).name
    filename = "".join(c for c in filename if ord(c) >= 32)[:180] or "caderneta" + suffix
    item = dict(
        id=uid(),
        dependent_id=dependentId,
        original_name=filename,
        stored_name=stored,
        content_type=file.content_type,
        size=len(blob),
        sha256=hashlib.sha256(blob).hexdigest(),
        vaccine=vaccine.strip(),
        dose_date=doseDate or None,
        family_note=note,
        status="pendente",
        review_note="",
        created_at=now(),
        reviewed_at=None,
        reviewer="",
    )
    try:
        with engine.begin() as con:
            lock_roster(con)
            if not allowed(con, user["id"], lock=True):
                raise HTTPException(403, "Autorização para acompanhamento digital não está vigente.")
            con.execute(insert(db.documents).values(**item))
            con.execute(
                insert(db.jobs).values(
                    id=uid(),
                    document_id=item["id"],
                    status="queued",
                    attempts=0,
                    updated_at=now(),
                    error="",
                    raw_text="",
                )
            )
            event(con, user["id"], "document", item["id"], "arquivo_enviado")
            assign_document(con, item["id"])
            public_item = public_document(item, dependent, con, user)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {"item": public_item}


@router.get("/api/documents/{identifier}")
def get_document(identifier: str, request: Request, user=User):
    with request.app.state.engine.connect() as con:
        item, dependent = document(con, identifier, user)
        return {"item": public_document(item, dependent, con, user)}


@router.get("/api/documents/{identifier}/file")
def document_file(identifier: str, request: Request, user=User):
    with request.app.state.engine.begin() as con:
        item, _ = document(con, identifier, user)
        event(con, user["id"], "document", identifier, "arquivo_consultado")
    root = request.app.state.data / "uploads"
    path = (root / item["stored_name"]).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(404, "Arquivo não encontrado.")
    return FileResponse(
        path,
        media_type=item["content_type"],
        filename=item["original_name"],
        content_disposition_type="inline",
        headers={"Content-Security-Policy": "sandbox; default-src 'none'; frame-ancestors 'self'"},
    )


@router.post("/api/documents/{identifier}/decision")
def decide_document(identifier: str, body: s.Decision, request: Request, user=User):
    sec.role(user, "ubs")
    with request.app.state.engine.begin() as con:
        lock_roster(con)
        item, dependent = document(con, identifier, user)
        cast_vote(
            con,
            identifier,
            "document",
            identifier,
            "aprovar" if body.decision == "aprovado" else "recusar",
            body.note,
            body.guidance,
            user,
            body.independenceConfirmed,
            body.reviewRound,
        )
        return {"item": public_document(one(con, db.documents, identifier), dependent, con, user)}


@router.get("/api/audit")
def document_audit(documentId: str, request: Request, user=User):
    with request.app.state.engine.connect() as con:
        current, _ = document(con, documentId, user)
        return {
            "items": [
                dict(r)
                for r in con.execute(
                    select(db.audit)
                    .where(db.audit.c.target_type == "document", db.audit.c.target_id == documentId)
                    .order_by(db.audit.c.created_at)
                ).mappings()
                if not (
                    user["role"] == "ubs"
                    and current["status"] == "pendente"
                    and (
                        (r["event"].startswith("voto_independente_") and r["actor_id"] != user["id"])
                        or r["event"]
                        in ("rodada_anterior_preservada", "decisao_documento_suspensa_impedimento")
                    )
                )
            ]
        }


from .clinical import router as clinical_router  # noqa: E402

router.include_router(clinical_router)
