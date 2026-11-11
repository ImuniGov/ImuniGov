"""Versioned notice and evidence of explicit, purpose-specific acceptance."""

import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field
from sqlalchemy import delete, func, insert, select, update

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


def verify_representation(con, dependent_id, verification_ref, note):
    if not 3 <= len(verification_ref.strip()) <= 200 or not 3 <= len(note.strip()) <= 500:
        raise ValueError("Informe referência documental (3–200) e nota de verificação (3–500).")
    dep = con.execute(select(db.dependents).where(db.dependents.c.id == dependent_id)).mappings().first()
    if not dep or not dep["owner_id"]:
        raise ValueError("Dependente não encontrado ou sem responsável vinculado.")
    details = json.dumps(
        {
            "dependent_id": dependent_id,
            "owner_id": dep["owner_id"],
            "verification_ref": verification_ref.strip(),
            "note": note.strip(),
            "verified_at": now(),
        },
        ensure_ascii=False,
    )
    event(con, dep["owner_id"], "dependent", dependent_id, "representacao_familiar_verificada", details)
    return {
        "dependentId": dependent_id,
        "ownerId": dep["owner_id"],
        "verificationRef": verification_ref.strip(),
        "verified": True,
    }


def execute_privacy_deletion(con, data_dir, request_id, administrative_ref, note):
    if not 3 <= len(administrative_ref.strip()) <= 200 or not 3 <= len(note.strip()) <= 2000:
        raise ValueError("Informe referência administrativa (3–200) e fundamentação (3–2000).")
    req = (
        con.execute(select(db.privacy_requests).where(db.privacy_requests.c.id == request_id))
        .mappings()
        .first()
    )
    if not req:
        raise ValueError("Solicitação de privacidade não encontrada.")
    if req["kind"] != "eliminacao":
        raise ValueError("Apenas solicitações do tipo 'eliminacao' podem acionar expurgo de dados.")
    if req["status"] == "executada":
        raise ValueError("Solicitação de eliminação já foi executada.")
    user_id = req["user_id"]
    con.execute(select(db.users.c.id).where(db.users.c.id == user_id).with_for_update())
    control = con.scalar(select(db.consent_controls.c.id).where(db.consent_controls.c.user_id == user_id))
    if control:
        con.execute(
            update(db.consent_controls)
            .where(db.consent_controls.c.id == control)
            .values(withdrawn=True, updated_at=now())
        )
    else:
        con.execute(
            insert(db.consent_controls).values(id=uid(), user_id=user_id, withdrawn=True, updated_at=now())
        )
    con.execute(delete(db.sessions).where(db.sessions.c.user_id == user_id))
    con.execute(delete(db.push_subscriptions).where(db.push_subscriptions.c.user_id == user_id))
    con.execute(delete(db.notifications).where(db.notifications.c.user_id == user_id))

    dependents = list(con.scalars(select(db.dependents.c.id).where(db.dependents.c.owner_id == user_id)))
    scrubbed_jobs = 0
    deleted_unconfirmed_vaccinations = 0
    retained_validated_vaccinations = 0
    retained_documents = 0
    files_to_remove = []
    root = Path(data_dir).resolve() / "uploads"

    for dep_id in dependents:
        docs = con.execute(select(db.documents).where(db.documents.c.dependent_id == dep_id)).mappings().all()
        for doc in docs:
            res = con.execute(
                update(db.jobs)
                .where(db.jobs.c.document_id == doc["id"], db.jobs.c.raw_text != "")
                .values(
                    raw_text="", error="Texto bruto eliminado por solicitação do titular.", updated_at=now()
                )
            )
            scrubbed_jobs += res.rowcount or 0
            # Candidate vaccinations without votes can be deleted; voted/validated records are retained under LGPD Art. 16.
            candidates = (
                con.execute(
                    select(db.vaccinations).where(
                        db.vaccinations.c.document_id == doc["id"],
                        db.vaccinations.c.status == "a_conferir",
                    )
                )
                .mappings()
                .all()
            )
            for cand in candidates:
                has_vote = con.scalar(
                    select(func.count())
                    .select_from(db.review_votes)
                    .where(
                        db.review_votes.c.target_type == "vaccination",
                        db.review_votes.c.target_id == cand["id"],
                    )
                )
                if not has_vote:
                    con.execute(
                        update(db.dose_plans)
                        .where(db.dose_plans.c.record_id == cand["id"])
                        .values(record_id=None)
                    )
                    con.execute(delete(db.vaccinations).where(db.vaccinations.c.id == cand["id"]))
                    deleted_unconfirmed_vaccinations += 1
            validated_count = con.scalar(
                select(func.count())
                .select_from(db.vaccinations)
                .where(
                    db.vaccinations.c.document_id == doc["id"],
                    db.vaccinations.c.status != "a_conferir",
                )
            )
            retained_validated_vaccinations += validated_count or 0
            remaining_vaccinations = con.scalar(
                select(func.count())
                .select_from(db.vaccinations)
                .where(db.vaccinations.c.document_id == doc["id"])
            )
            doc_votes = con.scalar(
                select(func.count())
                .select_from(db.review_votes)
                .where(
                    db.review_votes.c.target_type == "document",
                    db.review_votes.c.target_id == doc["id"],
                )
            )
            if not remaining_vaccinations and not doc_votes and doc["status"] == "pendente":
                con.execute(
                    delete(db.review_assignments).where(db.review_assignments.c.document_id == doc["id"])
                )
                con.execute(delete(db.jobs).where(db.jobs.c.document_id == doc["id"]))
                con.execute(delete(db.documents).where(db.documents.c.id == doc["id"]))
                path = (root / doc["stored_name"]).resolve()
                if path.parent == root:
                    files_to_remove.append(path)
            else:
                retained_documents += 1

    summary_payload = {
        "administrativeRef": administrative_ref.strip(),
        "scrubbedOcrTexts": scrubbed_jobs,
        "deletedUnconfirmedVaccinations": deleted_unconfirmed_vaccinations,
        "deletedFiles": len(files_to_remove),
        "retainedDocuments": retained_documents,
        "retainedValidatedVaccinations": retained_validated_vaccinations,
        "retentionLegalBasis": "Art. 16, I e II da LGPD (cumprimento de obrigação legal/regulatória e trilha de auditoria clínica imutável).",
    }
    response_text = (
        f"{note.strip()} | Ref: {administrative_ref.strip()} | "
        f"Expurgados: {scrubbed_jobs} texto(s) OCR, {deleted_unconfirmed_vaccinations} candidato(s) não votados, "
        f"{len(files_to_remove)} arquivo(s) sem vínculo de revisão. "
        f"Conservados sob bloqueio (art. 16 LGPD): {retained_documents} documento(s) e {retained_validated_vaccinations} registro(s) decidido(s)."
    )
    con.execute(
        update(db.privacy_requests)
        .where(db.privacy_requests.c.id == request_id)
        .values(status="executada", response=response_text[:2000], answered_at=now())
    )
    event(
        con,
        user_id,
        "privacy_request",
        request_id,
        "eliminacao_avaliada_e_executada",
        json.dumps(summary_payload, ensure_ascii=False),
    )
    for path in files_to_remove:
        path.unlink(missing_ok=True)
    return summary_payload


def record_security_incident(con, severity, administrative_ref, summary, scope, mitigation):
    if severity not in ("baixa", "media", "alta", "critica"):
        raise ValueError("Severidade deve ser baixa, media, alta ou critica.")
    if (
        len(administrative_ref.strip()) < 3
        or len(summary.strip()) < 5
        or len(scope.strip()) < 3
        or len(mitigation.strip()) < 5
    ):
        raise ValueError("Preencha referência, resumo, escopo afetado e medidas de mitigação.")
    incident_id = uid()
    payload = {
        "id": incident_id,
        "severity": severity,
        "administrativeRef": administrative_ref.strip(),
        "summary": summary.strip(),
        "affectedScope": scope.strip(),
        "mitigation": mitigation.strip(),
        "recordedAt": now(),
    }
    event(
        con,
        None,
        "privacy_incident",
        incident_id,
        "incidente_seguranca_registrado",
        json.dumps(payload, ensure_ascii=False),
    )
    return payload
