"""Opt-in Web Push. No medical content is transmitted to the push provider."""

import base64
import hashlib
import os
import time
from pathlib import Path
from urllib.parse import urlparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field, field_validator
from pywebpush import WebPushException, webpush
from sqlalchemy import insert, select, update

from . import db
from . import security as sec
from .domain import event, now
from .schemas import Input

router = APIRouter()


def ensure_keys(directory):
    path = Path(directory) / "push-private.pem"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        key = ec.generate_private_key(ec.SECP256R1())
        try:
            with path.open("xb") as stream:
                stream.write(
                    key.private_bytes(
                        serialization.Encoding.PEM,
                        serialization.PrivateFormat.PKCS8,
                        serialization.NoEncryption(),
                    )
                )
            path.chmod(0o600)
        except FileExistsError:
            pass
    return path


def public_key(directory):
    key = serialization.load_pem_private_key(ensure_keys(directory).read_bytes(), password=None)
    raw = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


class PushKeys(Input):
    p256dh: str = Field(min_length=87, max_length=88, pattern=r"^[A-Za-z0-9_-]+=*$")
    auth: str = Field(min_length=22, max_length=24, pattern=r"^[A-Za-z0-9_-]+=*$")


class Endpoint(Input):
    endpoint: str = Field(max_length=2048)

    @field_validator("endpoint")
    @classmethod
    def allowed(cls, value):
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower()
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
            or parsed.fragment
        ):
            raise ValueError("Endpoint inválido.")
        if host not in {
            "fcm.googleapis.com",
            "updates.push.services.mozilla.com",
            "web.push.apple.com",
        } and not host.endswith(".notify.windows.com"):
            raise ValueError("Provedor de notificações não permitido.")
        return value


class Subscription(Endpoint):
    keys: PushKeys
    expirationTime: int | None = None


@router.get("/api/v1/push/config")
def config(request: Request, user=Depends(sec.session_user)):
    return {"publicKey": public_key(request.app.state.data)}


@router.post("/api/v1/push/subscriptions", status_code=201)
def subscribe(body: Subscription, request: Request, user=Depends(sec.session_user)):
    sec.role(user, "familia")
    sec.rate_limit(request.app.state.engine, f"push:{user['id']}", limit=30)
    identifier = hashlib.sha256(body.endpoint.encode()).hexdigest()
    values = {
        "user_id": user["id"],
        "session_id": sec.token_hash(request.cookies.get("imuniguia_session", "")),
        "endpoint": body.endpoint,
        "keys": body.keys.model_dump(),
        "enabled": True,
        "last_sent_at": now(),
        "failures": 0,
        "next_attempt": 0,
    }
    with request.app.state.engine.begin() as con:
        old = (
            con.execute(select(db.push_subscriptions).where(db.push_subscriptions.c.id == identifier))
            .mappings()
            .first()
        )
        if old and old["user_id"] != user["id"]:
            raise HTTPException(
                409, "Este aparelho está vinculado a outra conta. Desative os avisos e tente novamente."
            )
        if old:
            con.execute(
                update(db.push_subscriptions).where(db.push_subscriptions.c.id == identifier).values(**values)
            )
        else:
            con.execute(insert(db.push_subscriptions).values(id=identifier, created_at=now(), **values))
        event(con, user["id"], "device", identifier, "avisos_ativados")
    return {"ok": True}


@router.post("/api/v1/push/unsubscribe")
def unsubscribe(body: Endpoint, request: Request, user=Depends(sec.session_user)):
    identifier = hashlib.sha256(body.endpoint.encode()).hexdigest()
    with request.app.state.engine.begin() as con:
        con.execute(
            update(db.push_subscriptions)
            .where(db.push_subscriptions.c.id == identifier, db.push_subscriptions.c.user_id == user["id"])
            .values(enabled=False)
        )
        event(con, user["id"], "device", identifier, "avisos_desativados")
    return {"ok": True}


def deliver(engine, directory, sender=webpush):
    instant = int(time.time())
    with engine.connect() as con:
        devices = (
            con.execute(
                select(db.push_subscriptions).where(
                    db.push_subscriptions.c.enabled.is_(True), db.push_subscriptions.c.next_attempt <= instant
                )
            )
            .mappings()
            .all()
        )
    for device in devices:
        with engine.connect() as con:
            latest = con.execute(
                select(db.notifications.c.created_at)
                .where(
                    db.notifications.c.user_id == device["user_id"],
                    db.notifications.c.created_at > device["last_sent_at"],
                    db.notifications.c.read.is_(False),
                )
                .order_by(db.notifications.c.created_at.desc())
                .limit(1)
            ).scalar()
        if not latest:
            continue
        try:
            sender(
                subscription_info={"endpoint": device["endpoint"], "keys": device["keys"]},
                data='{"type":"care-update"}',
                vapid_private_key=str(ensure_keys(directory)),
                vapid_claims={"sub": os.environ.get("VAPID_SUBJECT", "https://localhost")},
                timeout=10,
                ttl=86400,
            )
            with engine.begin() as con:
                con.execute(
                    update(db.push_subscriptions)
                    .where(
                        db.push_subscriptions.c.id == device["id"],
                        db.push_subscriptions.c.user_id == device["user_id"],
                    )
                    .values(last_sent_at=latest, failures=0, next_attempt=0)
                )
        except Exception as exc:
            gone = (
                isinstance(exc, WebPushException)
                and exc.response is not None
                and exc.response.status_code in (404, 410)
            )
            with engine.begin() as con:
                con.execute(
                    update(db.push_subscriptions)
                    .where(db.push_subscriptions.c.id == device["id"])
                    .values(
                        enabled=not gone and device["failures"] < 7,
                        failures=device["failures"] + 1,
                        next_attempt=instant + min(86400, 60 * 2 ** device["failures"]),
                    )
                )
