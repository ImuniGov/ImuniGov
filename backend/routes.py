import hashlib
import io
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from PIL import Image
from pypdf import PdfReader
from sqlalchemy import delete, func, insert, select, update

from . import db, schemas as s, security as sec
from .access import document, one, person, public_document
from .domain import event, notify, now, recalculate, uid

router = APIRouter()
User = Depends(sec.session_user)
MAX_UPLOAD = 10 * 1024 * 1024
PRIVACY_VERSION = '2026-11-08'


@router.post('/api/v1/auth/register', status_code=201)
def register(body: s.Register, request: Request, response: Response):
    engine = request.app.state.engine
    sec.rate_limit(engine, f'register:{request.client.host}', limit=10)
    user = dict(id=uid(), name=body.name, email=body.email, role='familia', password_hash=sec.hasher.hash(body.password), created_at=now(), privacy_version=PRIVACY_VERSION)
    with engine.begin() as con:
        con.execute(insert(db.users).values(**user))
        event(con, user['id'], 'user', user['id'], 'cadastro_e_ciencia_privacidade', PRIVACY_VERSION)
        csrf = sec.start_session(con, user['id'], response, request.app.state.secure)
    return {'user': sec.public_user(user), 'csrf': csrf}


@router.post('/api/v1/auth/login')
def login(body: s.Login, request: Request, response: Response):
    engine = request.app.state.engine
    sec.rate_limit(engine, f'login-ip:{request.client.host}')
    sec.rate_limit(engine, f'login-account:{body.email}', limit=10)
    with engine.begin() as con:
        user = con.execute(select(db.users).where(db.users.c.email == body.email)).mappings().first()
        valid = sec.verify(user['password_hash'] if user else None, body.password)
        if not user or not valid:
            raise HTTPException(401, 'E-mail ou senha inválidos.')
        con.execute(delete(db.sessions).where(db.sessions.c.id == sec.token_hash(request.cookies.get('imuniguia_session', ''))))
        csrf = sec.start_session(con, user['id'], response, request.app.state.secure)
        event(con, user['id'], 'user', user['id'], 'login')
    return {'user': sec.public_user(user), 'csrf': csrf}


@router.get('/api/v1/me')
def me(user=User):
    return {'user': sec.public_user(user), 'csrf': user['csrf']}


@router.post('/api/v1/auth/logout', status_code=204)
def logout(request: Request, response: Response, user=User):
    with request.app.state.engine.begin() as con:
        con.execute(delete(db.sessions).where(db.sessions.c.id == sec.token_hash(request.cookies.get('imuniguia_session', ''))))
        event(con, user['id'], 'user', user['id'], 'logout')
    response.delete_cookie('imuniguia_session', path='/')


@router.get('/api/dependents')
def dependents(request: Request, user=User):
    sec.role(user, 'familia', 'ubs')
    query = select(db.dependents).order_by(db.dependents.c.name)
    if user['role'] == 'familia':
        query = query.where(db.dependents.c.owner_id == user['id'])
    with request.app.state.engine.connect() as con:
        return {'items': [{**dict(r), 'birthDate': r['birth_date'], 'document_count': con.scalar(select(func.count()).select_from(db.documents).where(db.documents.c.dependent_id == r['id']))} for r in con.execute(query).mappings()]}


@router.post('/api/dependents', status_code=201)
def add_dependent(body: s.Dependent, request: Request, user=User):
    sec.role(user, 'familia')
    item = dict(id=uid(), owner_id=user['id'], name=body.name, birth_date=body.birthDate.isoformat(), created_at=now())
    with request.app.state.engine.begin() as con:
        con.execute(insert(db.dependents).values(**item))
        event(con, user['id'], 'dependent', item['id'], 'dependente_criado')
        recalculate(con, item['id'], user['id'])
    return {'item': {**item, 'birthDate': item['birth_date'], 'document_count': 0}}


@router.patch('/api/dependents/{identifier}')
def edit_dependent(identifier: str, body: s.Dependent, request: Request, user=User):
    sec.role(user, 'familia')
    with request.app.state.engine.begin() as con:
        person(con, identifier, user)
        con.execute(update(db.dependents).where(db.dependents.c.id == identifier).values(name=body.name, birth_date=body.birthDate.isoformat()))
        event(con, user['id'], 'dependent', identifier, 'dependente_atualizado')
        recalculate(con, identifier, user['id'])
    return {'ok': True}


@router.delete('/api/dependents/{identifier}', status_code=204)
def remove_dependent(identifier: str, request: Request, user=User):
    sec.role(user, 'familia')
    with request.app.state.engine.begin() as con:
        person(con, identifier, user)
        for table in (db.documents, db.vaccinations, db.pendings):
            if con.scalar(select(func.count()).select_from(table).where(table.c.dependent_id == identifier)):
                raise HTTPException(409, 'Dependente possui histórico associado. Solicite avaliação de retenção à equipe.')
        con.execute(delete(db.dependents).where(db.dependents.c.id == identifier))
        event(con, user['id'], 'dependent', identifier, 'dependente_removido')


@router.get('/api/documents')
def documents(request: Request, status: str | None = None, user=User):
    sec.role(user, 'familia', 'ubs')
    if status and status not in ('pendente', 'aprovado', 'rejeitado'):
        raise HTTPException(400, 'Filtro de status inválido.')
    query = select(db.documents).join(db.dependents, db.dependents.c.id == db.documents.c.dependent_id)
    if user['role'] == 'familia':
        query = query.where(db.dependents.c.owner_id == user['id'])
    if status:
        query = query.where(db.documents.c.status == status)
    with request.app.state.engine.connect() as con:
        return {'items': [public_document(dict(r), one(con, db.dependents, r['dependent_id'])) for r in con.execute(query.order_by(db.documents.c.created_at.desc())).mappings()]}


def check_file(blob, mime):
    if not blob:
        raise HTTPException(400, 'Arquivo vazio.')
    if len(blob) > MAX_UPLOAD:
        raise HTTPException(413, 'O arquivo deve ter até 10 MB.')
    try:
        if mime in ('image/jpeg', 'image/png', 'image/webp'):
            with Image.open(io.BytesIO(blob)) as image:
                if Image.MIME.get(image.format) != mime or image.width * image.height > 40_000_000:
                    raise ValueError()
                image.verify()
        elif mime == 'application/pdf':
            if not blob.lstrip().startswith(b'%PDF-'):
                raise ValueError()
            pdf = PdfReader(io.BytesIO(blob), strict=True)
            if pdf.is_encrypted or not 0 < len(pdf.pages) <= 10:
                raise ValueError()
        else:
            raise ValueError()
    except Exception as exc:
        raise HTTPException(415, 'Envie JPG, PNG, WEBP ou PDF válido, sem senha e com até 10 páginas.') from exc


@router.post('/api/documents', status_code=201)
async def upload(request: Request, dependentId: str = Form(...), vaccine: str = Form(..., max_length=80), doseDate: str = Form(''), note: str = Form('', max_length=500), file: UploadFile = File(...), user=User):
    sec.role(user, 'familia')
    engine = request.app.state.engine
    sec.rate_limit(engine, f'upload:{user["id"]}', limit=30, seconds=3600)
    with engine.connect() as con:
        dependent = person(con, dependentId, user)
    if not vaccine.strip():
        raise HTTPException(400, 'Informe a vacina ou registro.')
    if doseDate:
        try:
            if date.fromisoformat(doseDate) > date.today() or (dependent['birth_date'] and doseDate < dependent['birth_date']):
                raise ValueError()
        except ValueError as exc:
            raise HTTPException(400, 'Data do registro inválida.') from exc
    blob = await file.read(MAX_UPLOAD + 1)
    check_file(blob, file.content_type)
    suffix = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'application/pdf': '.pdf'}[file.content_type]
    stored = uid() + suffix
    path = request.app.state.data / 'uploads' / stored
    path.write_bytes(blob)
    filename = Path((file.filename or 'caderneta').replace('\\', '/')).name
    filename = ''.join(c for c in filename if ord(c) >= 32)[:180] or 'caderneta' + suffix
    item = dict(id=uid(), dependent_id=dependentId, original_name=filename, stored_name=stored, content_type=file.content_type, size=len(blob), sha256=hashlib.sha256(blob).hexdigest(), vaccine=vaccine.strip(), dose_date=doseDate or None, family_note=note, status='pendente', review_note='', created_at=now(), reviewed_at=None, reviewer='')
    try:
        with engine.begin() as con:
            con.execute(insert(db.documents).values(**item))
            con.execute(insert(db.jobs).values(id=uid(), document_id=item['id'], status='queued', attempts=0, updated_at=now(), error='', raw_text=''))
            event(con, user['id'], 'document', item['id'], 'arquivo_enviado')
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {'item': public_document(item, dependent)}


@router.get('/api/documents/{identifier}')
def get_document(identifier: str, request: Request, user=User):
    with request.app.state.engine.connect() as con:
        item, dependent = document(con, identifier, user)
        return {'item': public_document(item, dependent)}


@router.get('/api/documents/{identifier}/file')
def document_file(identifier: str, request: Request, user=User):
    with request.app.state.engine.begin() as con:
        item, _ = document(con, identifier, user)
        event(con, user['id'], 'document', identifier, 'arquivo_consultado')
    root = request.app.state.data / 'uploads'
    path = (root / item['stored_name']).resolve()
    if path.parent != root or not path.is_file():
        raise HTTPException(404, 'Arquivo não encontrado.')
    return FileResponse(path, media_type=item['content_type'], filename=item['original_name'], content_disposition_type='inline', headers={'Content-Security-Policy': "sandbox; default-src 'none'; frame-ancestors 'self'"})


@router.post('/api/documents/{identifier}/decision')
def decide_document(identifier: str, body: s.Decision, request: Request, user=User):
    sec.role(user, 'ubs')
    if body.decision == 'rejeitado' and not body.note:
        raise HTTPException(400, 'Informe o motivo da devolução.')
    with request.app.state.engine.begin() as con:
        item, dependent = document(con, identifier, user)
        result = con.execute(update(db.documents).where(db.documents.c.id == identifier, db.documents.c.status == 'pendente').values(status=body.decision, reviewer=user['name'], reviewed_at=now(), review_note=body.note or 'Arquivo conferido pela equipe.'))
        if not result.rowcount:
            raise HTTPException(409, 'Documento já recebeu decisão.')
        event(con, user['id'], 'document', identifier, body.decision, body.note)
        notify(con, dependent['owner_id'], f'document:{identifier}:{body.decision}', 'A UBS atualizou a conferência de um arquivo.')
        return {'item': public_document(one(con, db.documents, identifier), dependent)}


@router.get('/api/audit')
def document_audit(documentId: str, request: Request, user=User):
    with request.app.state.engine.connect() as con:
        document(con, documentId, user)
        return {'items': [dict(r) for r in con.execute(select(db.audit).where(db.audit.c.target_type == 'document', db.audit.c.target_id == documentId).order_by(db.audit.c.created_at)).mappings()]}


from .clinical import router as clinical_router  # noqa: E402
router.include_router(clinical_router)
