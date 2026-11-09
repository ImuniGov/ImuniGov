"""Versioned notice and evidence of explicit, purpose-specific acceptance."""

import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field
from sqlalchemy import insert, select, update

from . import db, security
from .consents import policy, state
from .domain import event, now, uid
from .schemas import Input

router = APIRouter()


def record_acceptance(con, user_id, body):
    con.execute(select(db.users.c.id).where(db.users.c.id == user_id).with_for_update())
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
    control = (
        con.execute(select(db.consent_controls).where(db.consent_controls.c.user_id == user_id))
        .mappings()
        .first()
    )
    if control:
        con.execute(
            update(db.consent_controls)
            .where(db.consent_controls.c.id == control["id"])
            .values(withdrawn=False, updated_at=now())
        )
    con.execute(update(db.users).where(db.users.c.id == user_id).values(privacy_version=current["version"]))
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
        if body.kind == "revogacao":
            security.role(user, "familia")
            con.execute(select(db.users.c.id).where(db.users.c.id == user["id"]).with_for_update())
            control = con.execute(
                select(db.consent_controls.c.id).where(db.consent_controls.c.user_id == user["id"])
            ).scalar()
            if control:
                con.execute(
                    update(db.consent_controls)
                    .where(db.consent_controls.c.id == control)
                    .values(withdrawn=True, updated_at=now())
                )
            else:
                con.execute(
                    insert(db.consent_controls).values(
                        id=uid(), user_id=user["id"], withdrawn=True, updated_at=now()
                    )
                )
            con.execute(
                update(db.push_subscriptions)
                .where(db.push_subscriptions.c.user_id == user["id"])
                .values(enabled=False)
            )
            event(
                con,
                user["id"],
                "user",
                user["id"],
                "autorizacao_saude_revogada",
                "Processamento voluntário suspenso; retenção exige análise separada.",
            )
        con.execute(insert(db.privacy_requests).values(**item))
        event(con, user["id"], "privacy_request", item["id"], "solicitacao_recebida", body.kind)
    return {"item": item}


class Acceptance(Input):
    consent: Literal[True]
    healthConsent: Literal[True]
    adultDeclaration: Literal[True]
    termsVersion: str = Field(min_length=1, max_length=80)
    privacyHash: str = Field(pattern=r"^[a-f0-9]{64}$")


@router.post("/api/v1/privacy/accept")
def accept(body: Acceptance, request: Request, user=Depends(security.session_user)):
    security.role(user, "familia")
    with request.app.state.engine.begin() as con:
        record_acceptance(con, user["id"], body)
        result = {**user, "privacy": state(con, user["id"])}
    return {"user": security.public_user(result)}
