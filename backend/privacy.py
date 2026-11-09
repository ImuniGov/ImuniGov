"""Versioned notice and evidence of explicit, purpose-specific acceptance."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field
from sqlalchemy import insert, select

from . import db, security
from .domain import event, now, uid
from .schemas import Input

POLICY_PATH = Path(__file__).parent / "legal" / "privacy-2026-11-08.json"
router = APIRouter()


def policy():
    raw = POLICY_PATH.read_bytes()
    return {**json.loads(raw), "hash": hashlib.sha256(raw).hexdigest()}


def record_acceptance(con, user_id, body):
    current = policy()
    if body.termsVersion != current["version"] or body.privacyHash != current["hash"]:
        raise HTTPException(409, "Os termos foram atualizados. Reabra o texto e confira a versão vigente.")
    item = dict(
        id=uid(),
        user_id=user_id,
        version=current["version"],
        policy_hash=current["hash"],
        terms_accepted=True,
        health_consent=True,
        adult_declaration=True,
        accepted_at=now(),
    )
    con.execute(insert(db.acceptances).values(**item))
    event(
        con,
        user_id,
        "privacy",
        item["id"],
        "aceite_termos_e_consentimento_saude",
        json.dumps({"version": current["version"], "sha256": current["hash"]}),
    )


@router.get("/api/v1/privacy/notice")
def notice():
    return policy()


class RightsRequest(Input):
    kind: Literal["acesso", "correcao", "eliminacao", "revogacao", "informacao", "outro"]
    message: str = Field(min_length=3, max_length=1000)


@router.get("/api/v1/privacy/requests")
def requests(request: Request, user=Depends(security.session_user)):
    with request.app.state.engine.connect() as con:
        return {
            "items": [
                dict(r)
                for r in con.execute(
                    select(db.privacy_requests)
                    .where(db.privacy_requests.c.user_id == user["id"])
                    .order_by(db.privacy_requests.c.created_at.desc())
                ).mappings()
            ],
            "acceptances": [
                dict(r)
                for r in con.execute(
                    select(db.acceptances).where(db.acceptances.c.user_id == user["id"])
                ).mappings()
            ],
        }


@router.post("/api/v1/privacy/requests", status_code=201)
def create_request(body: RightsRequest, request: Request, user=Depends(security.session_user)):
    security.rate_limit(request.app.state.engine, "rights:" + user["id"], limit=10, seconds=86400)
    item = dict(
        id=uid(),
        user_id=user["id"],
        kind=body.kind,
        message=body.message,
        status="recebida",
        response="",
        created_at=now(),
        answered_at=None,
    )
    with request.app.state.engine.begin() as con:
        con.execute(insert(db.privacy_requests).values(**item))
        event(con, user["id"], "privacy_request", item["id"], "solicitacao_recebida", body.kind)
    return {"item": item}
