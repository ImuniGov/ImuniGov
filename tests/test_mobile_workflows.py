import time

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from test_app import dependent, upload

from backend import db
from backend.password_reset import issue_reset_code


def test_reviewer_must_start_with_oldest_available_document(env):
    _, _, _, client = env
    family = client()
    reviewer = client("ubs")
    person = dependent(family)
    first, later = upload(family, person), upload(family, person)
    queue = "/api/v1/review/next"
    vote = {"decision": "aprovado", "reviewRound": 1, "independenceConfirmed": True}
    assert family.get(queue).status_code == 403
    assert reviewer.get(queue).json()["item"] == {"id": first, "step": "arquivo"}
    assert reviewer.post(f"/api/documents/{later}/decision", json=vote).status_code == 409
    record = reviewer.post(
        f"/api/v1/documents/{first}/candidates",
        json={"vaccine": "BCG", "dose": 1, "doseDate": "2026-01-02"},
    ).json()["item"]
    assert reviewer.post(f"/api/documents/{first}/decision", json=vote).status_code == 200
    assert reviewer.get(queue).json()["item"]["id"] == later
    for index in (1, 2):
        other = client("ubs", index)
        assert other.post(f"/api/documents/{first}/decision", json=vote).status_code == 200
    assert reviewer.get(queue).json()["item"] == {"id": first, "step": "doses"}
    assert reviewer.post(f"/api/documents/{later}/decision", json=vote).status_code == 409
    assert (
        reviewer.post(
            f"/api/v1/vaccinations/{record['id']}/decision",
            json={**vote, "decision": "validado", "note": "Registro legível."},
        ).status_code
        == 200
    )
    assert reviewer.get(queue).json()["item"] == {"id": later, "step": "arquivo"}


def test_password_recovery_and_opt_in_session_cookie(env):
    engine, _, app, client = env
    family = client()
    email = "familia0@example.test"
    login = "/api/v1/auth/login"
    reset = "/api/v1/auth/reset-password"
    password = "Teste-sintetico-longo!"
    new_password = "Nova-senha-sintetica!"
    with TestClient(app) as browser:
        normal = browser.post(login, json={"email": email, "password": password})
        assert normal.status_code == 200 and "Max-Age" not in normal.headers["Set-Cookie"]
        remembered = browser.post(login, json={"email": email, "password": password, "remember": True})
        assert remembered.status_code == 200 and "Max-Age=604800" in remembered.headers["Set-Cookie"]

        expired = issue_reset_code(engine, email)
        with engine.begin() as con:
            con.execute(update(db.password_resets).values(expires=int(time.time()) - 1))
        assert browser.post(reset, json={"code": expired, "password": new_password}).status_code == 400

        replaced = issue_reset_code(engine, email)
        code = issue_reset_code(engine, email)
        with engine.connect() as con:
            assert con.scalar(select(db.password_resets.c.id)) != code
        assert browser.post(reset, json={"code": replaced, "password": new_password}).status_code == 400
        assert browser.post(reset, json={"code": code, "password": new_password}).status_code == 204
        assert browser.post(reset, json={"code": code, "password": new_password}).status_code == 400
        assert browser.get("/api/v1/me").status_code == 401
        assert family.get("/api/v1/me").status_code == 401
        assert browser.post(login, json={"email": email, "password": password}).status_code == 401
        assert browser.post(login, json={"email": email, "password": new_password}).status_code == 200
