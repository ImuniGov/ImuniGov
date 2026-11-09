from conftest import acceptance
from sqlalchemy import select, update
from test_app import dependent, upload

from backend import db
from backend.worker import process_one


def test_withdrawal_blocks_workflows_but_preserves_own_access_and_resume(env):
    engine, root, app, client = env
    family, ubs, acs = client(), client("ubs"), client("acs")
    person = dependent(family)
    doc = upload(family, person)
    assert ubs.get(f"/api/documents/{doc}/file").status_code == 200
    assert (
        family.post(
            "/api/v1/privacy/requests", json={"kind": "revogacao", "message": "Quero pausar."}
        ).status_code
        == 201
    )
    assert family.get("/api/v1/me").json()["user"]["privacy"]["withdrawn"]
    assert family.get(f"/api/documents/{doc}/file").status_code == 200
    assert family.get("/api/v1/privacy/export").status_code == 200
    assert (
        family.post(
            "/api/dependents",
            json={"name": "Outra pessoa", "birthDate": "2026-01-01", "representationConfirmed": True},
        ).status_code
        == 403
    )
    assert ubs.get(f"/api/documents/{doc}/file").status_code == 403
    assert not ubs.get("/api/documents").json()["items"]
    assert not ubs.get("/api/dependents").json()["items"]
    assert not acs.get("/api/v1/acs/cases").json()["items"]
    assert acs.get(f"/api/v1/acs/cases/{person}/actions").status_code == 403
    assert not process_one(
        engine, root, extractor=lambda path: (_ for _ in ()).throw(AssertionError("Must not read"))
    )
    assert (
        family.post("/api/v1/privacy/accept", json={**acceptance(), "healthConsent": False}).status_code
        == 422
    )
    assert (
        family.post("/api/v1/privacy/accept", json={**acceptance(), "privacyHash": "0" * 64}).status_code
        == 409
    )
    assert family.post("/api/v1/privacy/accept", json=acceptance()).json()["user"]["privacy"]["current"]
    assert ubs.get(f"/api/documents/{doc}/file").status_code == 200
    assert process_one(engine, root, extractor=lambda path: ("BCG dose 1 02/01/2026", 85))


def test_revocation_during_ocr_discards_result(env):
    engine, root, app, client = env
    family = client()
    person = dependent(family)
    doc = upload(family, person)

    def extractor(path):
        response = family.post(
            "/api/v1/privacy/requests", json={"kind": "revogacao", "message": "Interromper agora."}
        )
        assert response.status_code == 201
        return "BCG dose 1 02/01/2026", 95

    assert process_one(engine, root, extractor=extractor)
    with engine.connect() as con:
        assert not con.execute(select(db.vaccinations)).first()
        job = con.execute(select(db.jobs).where(db.jobs.c.document_id == doc)).mappings().one()
        assert job["status"] == "failed" and job["raw_text"] == ""


def test_old_policy_hash_needs_explicit_new_acceptance_and_representation(env):
    engine, root, app, client = env
    family = client()
    assert (
        family.post("/api/dependents", json={"name": "Pessoa", "birthDate": "2026-01-01"}).status_code == 422
    )
    person = dependent(family)
    # An older account has no acceptance of the currently served document.
    with engine.begin() as con:
        con.execute(update(db.consent_controls).values(withdrawn=True))
        # Keep immutable acceptance evidence; change the active policy in the test instead.
    from backend import consents

    original = consents.policy
    import unittest.mock

    with unittest.mock.patch.object(consents, "policy", return_value={**original(), "hash": "1" * 64}):
        assert not family.get("/api/v1/me").json()["user"]["privacy"]["current"]
        assert (
            family.post(
                "/api/dependents",
                json={"name": "Pessoa", "birthDate": "2026-01-01", "representationConfirmed": True},
            ).status_code
            == 403
        )
    assert family.get(f"/api/v1/dependents/{person}/vaccinations").status_code == 200


def test_reaccept_during_old_ocr_does_not_reuse_earlier_authorization(env):
    engine, root, app, client = env
    family = client()
    doc = upload(family, dependent(family))

    def extractor(path):
        assert (
            family.post(
                "/api/v1/privacy/requests", json={"kind": "revogacao", "message": "Pausar."}
            ).status_code
            == 201
        )
        assert family.post("/api/v1/privacy/accept", json=acceptance()).status_code == 200
        return "BCG dose 1 02/01/2026", 90

    assert process_one(engine, root, extractor=extractor)
    with engine.connect() as con:
        assert not con.execute(select(db.vaccinations)).first()
        assert con.execute(select(db.jobs.c.status).where(db.jobs.c.document_id == doc)).scalar() == "failed"
