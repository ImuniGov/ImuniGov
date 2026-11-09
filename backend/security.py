import hashlib
import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import HTTPException, Request
from sqlalchemy import delete, insert, select, update

from . import db
from .consents import state

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(24))


def verify(encoded, password):
    try:
        return hasher.verify(encoded or DUMMY_HASH, password)
    except VerificationError:
        return False


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def session_user(request: Request):
    token = request.cookies.get("imuniguia_session", "")
    with request.app.state.engine.begin() as con:
        row = (
            con.execute(
                select(db.users, db.sessions.c.csrf)
                .join(db.sessions, db.sessions.c.user_id == db.users.c.id)
                .where(db.sessions.c.id == token_hash(token), db.sessions.c.expires > int(time.time()))
            )
            .mappings()
            .first()
        )
    if not row:
        raise HTTPException(401, "Entre na sua conta para continuar.")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not secrets.compare_digest(request.headers.get("X-CSRF-Token", ""), row["csrf"]):
            raise HTTPException(403, "Sessão de formulário inválida. Atualize a página.")
    if row["role"] == "ubs":
        with request.app.state.engine.connect() as con:
            if con.scalar(
                select(db.reviewer_profiles.c.id).where(
                    db.reviewer_profiles.c.user_id == row["id"], db.reviewer_profiles.c.active.is_(False)
                )
            ):
                raise HTTPException(401, "Seu acesso profissional está suspenso.")
    result = dict(row)
    result["_write"] = request.method not in ("GET", "HEAD", "OPTIONS")
    if row["role"] == "familia":
        with request.app.state.engine.connect() as con:
            result["privacy"] = state(con, row["id"])
        if request.method not in ("GET", "HEAD", "OPTIONS") and not result["privacy"]["current"]:
            if (
                not request.url.path.startswith("/api/v1/privacy/")
                and request.url.path != "/api/v1/auth/logout"
            ):
                raise HTTPException(
                    403,
                    "O acompanhamento digital está pausado. Confira os termos e a autorização na sua conta.",
                )
    return result


def role(user, *roles):
    if user["role"] not in roles:
        raise HTTPException(403, "Seu perfil não permite esta operação.")


def public_user(user):
    return {
        **{k: user[k] for k in ("id", "name", "email", "role")},
        **({"privacy": user["privacy"]} if "privacy" in user else {}),
    }


def start_session(con, user_id, response, secure):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    con.execute(delete(db.sessions).where(db.sessions.c.expires <= int(time.time())))
    con.execute(
        insert(db.sessions).values(
            id=token_hash(token), user_id=user_id, csrf=csrf, expires=int(time.time()) + 28800
        )
    )
    response.set_cookie(
        "imuniguia_session", token, httponly=True, secure=secure, samesite="strict", max_age=28800, path="/"
    )
    return csrf


def rate_limit(engine, identity, limit=15, seconds=900):
    key = token_hash(identity)
    instant = int(time.time())
    with engine.begin() as con:
        row = (
            con.execute(select(db.attempts).where(db.attempts.c.id == key).with_for_update())
            .mappings()
            .first()
        )
        if row and row["expires"] > instant:
            if row["count"] >= limit:
                raise HTTPException(429, "Muitas tentativas. Aguarde alguns minutos.")
            con.execute(update(db.attempts).where(db.attempts.c.id == key).values(count=row["count"] + 1))
        elif row:
            con.execute(
                update(db.attempts).where(db.attempts.c.id == key).values(count=1, expires=instant + seconds)
            )
        else:
            con.execute(insert(db.attempts).values(id=key, count=1, expires=instant + seconds))
