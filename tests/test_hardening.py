from datetime import date, datetime, timezone

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError
from test_app import approve_document, approve_record, dependent, upload

from backend import clock, db


def test_any_vaccine_can_have_ubs_date_but_not_family_date(env):
    engine, root, app, client = env
    family, other, ubs = client(), client(index=1), client("ubs")
    person = dependent(family)
    doc = upload(family, person)
    path = f"/api/v1/dependents/{person}/dose-plans"
    plan = {
        "vaccine": "Influenza",
        "dose": 1,
        "dueDate": "2026-11-30",
        "note": "Data individual sintética definida pela UBS.",
    }
    assert family.post(path, json=plan).status_code == 403
    result = ubs.post(path, json=plan)
    assert result.status_code == 201, result.text
    assert ubs.post(path, json=plan).status_code == 409
    assert other.get(path).status_code == 404
    item = next(
        i for i in family.get("/api/v1/family/schedule").json()["items"] if i["vaccine"] == "Influenza"
    )
    assert item["daysUntil"] == 22 and item["status"] == "proxima" and item["sourceType"] == "ubs"
    record = ubs.post(
        f"/api/v1/documents/{doc}/candidates",
        json={"vaccine": "Influenza", "dose": 1, "doseDate": "2026-11-01"},
    ).json()["item"]
    assert any(i["vaccine"] == "Influenza" for i in family.get("/api/v1/family/schedule").json()["items"])
    approve_document(client, doc)
    approve_record(client, record["id"])
    assert not any(i["vaccine"] == "Influenza" for i in family.get("/api/v1/family/schedule").json()["items"])
    assert family.get(path).json()["items"][0]["status"] == "concluida"
    another = ubs.post(path, json={**plan, "dose": 2}).json()["item"]
    cancel = f"/api/v1/dose-plans/{another['id']}/cancel"
    assert family.post(cancel, json={"note": "Tentativa indevida."}).status_code == 403
    assert ubs.post(cancel, json={"note": "Substituição da data de teste."}).status_code == 200
    assert any(p["status"] == "cancelada" for p in family.get(path).json()["items"])


def test_audit_cannot_be_updated_or_deleted(env):
    engine, root, app, client = env
    client()
    with engine.connect() as con:
        identifier = con.execute(select(db.audit.c.id).limit(1)).scalar_one()
    for statement in (
        update(db.audit).where(db.audit.c.id == identifier).values(event="alterado"),
        delete(db.audit).where(db.audit.c.id == identifier),
    ):
        with pytest.raises(DBAPIError), engine.begin() as con:
            con.execute(statement)


def test_session_expiration_and_birth_validation(env):
    engine, root, app, client = env
    family = client()
    assert (
        family.post("/api/dependents", json={"name": "Sintético", "birthDate": "2026-11-09"}).status_code
        == 422
    )
    assert (
        family.post("/api/dependents", json={"name": "Sintético", "birthDate": "1899-01-01"}).status_code
        == 422
    )
    with engine.begin() as con:
        con.execute(update(db.sessions).values(expires=0))
    assert family.get("/api/v1/me").status_code == 401


def test_unit_clock_uses_configured_timezone(monkeypatch):
    class Instant(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 9, 2, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(clock, "datetime", Instant)
    monkeypatch.setenv("APP_TIMEZONE", "America/Cuiaba")
    assert clock.today() == date(2026, 11, 8)
    monkeypatch.setenv("APP_TIMEZONE", "Europe/Lisbon")
    assert clock.today() == date(2026, 11, 9)
