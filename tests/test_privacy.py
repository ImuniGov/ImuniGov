import io

from conftest import acceptance
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select, update

from backend import db
from backend.privacy import execute_privacy_deletion, record_security_incident, verify_representation


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (120, 80), "white").save(buf, format="PNG")
    return buf.getvalue()


def test_versioned_specific_acceptance_and_rights_isolation(env):
    engine, root, app, client = env
    c = TestClient(app)
    notice = c.get("/api/v1/privacy/notice").json()
    assert notice["controller"] == "ImuniGuia" and len(notice["hash"]) == 64
    body = dict(
        name="Pessoa Sintética",
        email="privacy@example.test",
        password="Privacidade-Teste-2026",
        **acceptance(),
    )
    assert c.post("/api/v1/auth/register", json={**body, "healthConsent": False}).status_code == 422
    assert c.post("/api/v1/auth/register", json={**body, "termsVersion": "antiga"}).status_code == 409
    with engine.connect() as con:
        assert not con.execute(select(db.users).where(db.users.c.email == body["email"])).first()
    family, other = client(), client(index=1)
    with engine.connect() as con:
        rows = list(con.execute(select(db.acceptances)).mappings())
        assert len(rows) == 2 and all(r["policy_hash"] == notice["hash"] for r in rows)
    result = family.post(
        "/api/v1/privacy/requests", json={"kind": "revogacao", "message": "Quero revogar a autorização."}
    )
    assert result.status_code == 201 and result.json()["item"]["status"] == "recebida"
    assert len(family.get("/api/v1/privacy/requests").json()["items"]) == 1
    assert other.get("/api/v1/privacy/requests").json()["items"] == []


def test_representation_verification_deletion_execution_and_incident_response(env):
    engine, root, app, client = env
    family = client("familia", 0)
    ubs0, ubs1, ubs2 = client("ubs", 0), client("ubs", 1), client("ubs", 2)

    dep_res = family.post(
        "/api/dependents",
        json={"name": "Dependente Sintético", "birthDate": "2026-02-01", "representationConfirmed": True},
    )
    assert dep_res.status_code == 201
    dep_id = dep_res.json()["item"]["id"]
    assert dep_res.json()["item"]["representationVerified"] is False

    with engine.begin() as con:
        ver = verify_representation(
            con,
            dep_id,
            "CERTIDAO-SINTETICA-2026-01",
            "Certidão de nascimento conferida presencialmente na recepção.",
        )
        assert ver["verified"] is True

    deps = family.get("/api/dependents").json()["items"]
    assert deps[0]["representationVerified"] is True

    # Document 1: reviewed by UBS panel + 1 validated dose + 1 unvoted candidate + OCR raw text
    doc1 = family.post(
        "/api/documents",
        data={"dependentId": dep_id, "vaccine": "BCG", "doseDate": "2026-02-02"},
        files={"file": ("doc1.png", _png(), "image/png")},
    ).json()["item"]["id"]
    with engine.begin() as con:
        con.execute(
            update(db.jobs).where(db.jobs.c.document_id == doc1).values(raw_text="BCG 2026-02-02 Lote 123")
        )
    for reviewer in (ubs0, ubs1, ubs2):
        assert (
            reviewer.post(
                f"/api/documents/{doc1}/decision",
                json={
                    "decision": "aprovado",
                    "note": "Arquivo legível.",
                    "guidance": "",
                    "independenceConfirmed": True,
                    "reviewRound": 1,
                },
            ).status_code
            == 200
        )
    cand_valid = ubs0.post(
        f"/api/v1/documents/{doc1}/candidates",
        json={"vaccine": "BCG", "dose": 1, "doseDate": "2026-02-02"},
    ).json()["item"]["id"]
    for reviewer in (ubs0, ubs1, ubs2):
        assert (
            reviewer.post(
                f"/api/v1/vaccinations/{cand_valid}/decision",
                json={
                    "decision": "validado",
                    "note": "Conferido.",
                    "independenceConfirmed": True,
                    "reviewRound": 1,
                },
            ).status_code
            == 200
        )
    cand_unvoted = ubs0.post(
        f"/api/v1/documents/{doc1}/candidates",
        json={"vaccine": "Hepatite B", "dose": 1, "doseDate": "2026-02-02"},
    ).json()["item"]["id"]

    # Document 2: unreviewed pending document without any votes -> should be purged completely
    doc2 = family.post(
        "/api/documents",
        data={"dependentId": dep_id, "vaccine": "Pentavalente", "doseDate": "2026-04-02"},
        files={"file": ("doc2.png", _png(), "image/png")},
    ).json()["item"]["id"]

    del_req = family.post(
        "/api/v1/privacy/requests",
        json={"kind": "eliminacao", "message": "Solicito eliminação dos dados possíveis e texto OCR."},
    )
    assert del_req.status_code == 201
    req_id = del_req.json()["item"]["id"]

    with engine.begin() as con:
        summary = execute_privacy_deletion(
            con,
            root,
            req_id,
            "PROC-LGPD-2026-09",
            "Expurgo de dados acessórios executado; registros clínicos auditados retidos conforme art. 16 da LGPD.",
        )
    assert summary["scrubbedOcrTexts"] == 1
    assert summary["deletedUnconfirmedVaccinations"] == 1
    assert summary["deletedFiles"] == 1
    assert summary["retainedDocuments"] == 1
    assert summary["retainedValidatedVaccinations"] == 1

    with engine.connect() as con:
        assert not con.execute(select(db.documents).where(db.documents.c.id == doc2)).first()
        assert con.execute(select(db.documents).where(db.documents.c.id == doc1)).first()
        assert not con.execute(select(db.vaccinations).where(db.vaccinations.c.id == cand_unvoted)).first()
        assert con.execute(select(db.vaccinations).where(db.vaccinations.c.id == cand_valid)).first()
        job1 = con.execute(select(db.jobs).where(db.jobs.c.document_id == doc1)).mappings().one()
        assert job1["raw_text"] == ""
        req_row = (
            con.execute(select(db.privacy_requests).where(db.privacy_requests.c.id == req_id))
            .mappings()
            .one()
        )
        assert req_row["status"] == "executada"

    with engine.begin() as con:
        incident = record_security_incident(
            con,
            "media",
            "INC-SEC-2026-01",
            "Tentativa bloqueada de acesso automatizado repetido.",
            "Endpoint de autenticação sem comprometimento de sessão.",
            "Rate limiting confirmado e chaves rotacionadas preventivamente.",
        )
    assert incident["severity"] == "media"
    with engine.connect() as con:
        ev = (
            con.execute(
                select(db.audit).where(
                    db.audit.c.target_type == "privacy_incident",
                    db.audit.c.target_id == incident["id"],
                )
            )
            .mappings()
            .one()
        )
        assert ev["event"] == "incidente_seguranca_registrado"
