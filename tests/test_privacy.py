from conftest import acceptance
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend import db


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
