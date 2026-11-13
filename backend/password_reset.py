"""Short-lived recovery codes issued after an operator verifies account ownership."""

import secrets
import time

from fastapi import HTTPException
from sqlalchemy import delete, insert, select, update

from . import db
from .domain import event
from .security import hasher, token_hash

RESET_TTL = 30 * 60


def lock_account(con, condition):
    return con.scalar(
        update(db.users)
        .where(condition)
        .values(password_hash=db.users.c.password_hash)
        .returning(db.users.c.id)
    )


def issue_reset_code(engine, email):
    code = secrets.token_urlsafe(32)
    with engine.begin() as con:
        user_id = lock_account(con, db.users.c.email == email.strip().lower())
        if user_id is None:
            raise ValueError("Conta não encontrada.")
        con.execute(delete(db.password_resets).where(db.password_resets.c.user_id == user_id))
        con.execute(
            insert(db.password_resets).values(
                id=token_hash(code), user_id=user_id, expires=int(time.time()) + RESET_TTL
            )
        )
        event(con, None, "user", user_id, "codigo_de_recuperacao_emitido")
    return code


def redeem_reset_code(engine, code, password):
    with engine.begin() as con:
        identifier = db.password_resets.c.id == token_hash(code)
        owner = select(db.password_resets.c.user_id).where(identifier).scalar_subquery()
        user_id = lock_account(con, db.users.c.id == owner)
        consumed = user_id and con.scalar(
            delete(db.password_resets)
            .where(
                identifier,
                db.password_resets.c.user_id == user_id,
                db.password_resets.c.expires > int(time.time()),
            )
            .returning(db.password_resets.c.user_id)
        )
        if not consumed:
            raise HTTPException(400, "Código inválido ou vencido. Peça outro à administração.")
        con.execute(
            update(db.users).where(db.users.c.id == user_id).values(password_hash=hasher.hash(password))
        )
        con.execute(delete(db.sessions).where(db.sessions.c.user_id == user_id))
        con.execute(
            update(db.push_subscriptions)
            .where(db.push_subscriptions.c.user_id == user_id)
            .values(enabled=False)
        )
        event(con, user_id, "user", user_id, "senha_redefinida")
