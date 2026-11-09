from datetime import date

import pytest
from sqlalchemy import insert, select

from backend import db
from backend.domain import notify, now, recalculate, schedule, uid
from backend.push import deliver


def ruleset():
    return {
        "version": "test-v1",
        "source": "https://example.test/calendar",
        "valid_from": "2026-01-01",
        "valid_until": "2027-12-31",
        "rules": [
            {"id": "one", "vaccine": "BCG", "dose": 1, "due_months": 2, "min_months": 0, "max_months": 60}
        ],
    }


@pytest.mark.parametrize(
    "today,status,days",
    [
        (date(2026, 1, 29), "prevista", 31),
        (date(2026, 1, 30), "proxima", 30),
        (date(2026, 3, 1), "proxima", 0),
        (date(2026, 3, 2), "atrasada", -1),
    ],
)
def test_schedule_alert_window(today, status, days):
    item = schedule("2026-01-01", [], ruleset(), today)[0]
    assert item["status"] == status and item["daysUntil"] == days and item["dueDate"] == "2026-03-01"


def test_confirmed_dose_removes_reminder_but_candidate_does_not():
    record = {"vaccine": "BCG", "dose": 1, "dose_date": "2026-02-01", "status": "a_conferir"}
    assert schedule("2026-01-01", [record], ruleset(), date(2026, 2, 10))[0]["hasCandidate"]
    assert schedule("2026-01-01", [{**record, "status": "validado"}], ruleset(), date(2026, 2, 10)) == []
    assert schedule(None, [], ruleset(), date(2026, 2, 10)) == []


def test_family_schedule_isolation_and_notification_once(env):
    engine, root, app, client = env
    a, b = client(), client(index=1)
    a_id = a.get("/api/v1/me").json()["user"]["id"]
    with engine.begin() as con:
        con.execute(
            insert(db.dependents).values(
                id="forecast-test",
                name="Pessoa Sintética",
                owner_id=a_id,
                birth_date="2026-01-01",
                created_at=now(),
            )
        )
        con.execute(db.rules.update().values(active=False))
        con.execute(insert(db.rules).values(id=uid(), active=True, created_at=now(), **ruleset()))
        recalculate(con, "forecast-test", today=date(2026, 1, 30))
        recalculate(con, "forecast-test", today=date(2026, 1, 30))
        notes = (
            con.execute(select(db.notifications).where(db.notifications.c.user_id == a_id)).mappings().all()
        )
        assert len(notes) == 1 and "se aproxima" in notes[0]["message"]
    assert b.get("/api/v1/family/schedule").json()["items"] == []
    assert a.get("/api/v1/family/schedule").json()["items"][0]["dependentId"] == "forecast-test"


def test_push_opt_in_payload_privacy_and_logout_revocation(env):
    engine, root, app, client = env
    family, other = client(), client(index=1)
    subscription = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test-only",
        "keys": {"p256dh": "A" * 87, "auth": "B" * 22},
        "expirationTime": None,
    }
    assert (
        family.post(
            "/api/v1/push/subscriptions", json={**subscription, "endpoint": "https://127.0.0.1/internal"}
        ).status_code
        == 422
    )
    assert family.post("/api/v1/push/subscriptions", json=subscription).status_code == 201
    assert other.post("/api/v1/push/subscriptions", json=subscription).status_code == 409
    owner = family.get("/api/v1/me").json()["user"]["id"]
    with engine.begin() as con:
        notify(con, owner, "event-test", "Informação pessoal que não pode ir à tela bloqueada.")
    calls = []
    deliver(engine, root, sender=lambda **kw: calls.append(kw))
    deliver(engine, root, sender=lambda **kw: calls.append(kw))
    assert len(calls) == 1 and calls[0]["data"] == '{"type":"care-update"}'
    assert family.post("/api/v1/auth/logout").status_code == 204
    with engine.connect() as con:
        assert con.execute(select(db.push_subscriptions.c.enabled)).scalar() is False


def test_push_backoff_does_not_lose_notification(env):
    engine, root, app, client = env
    family = client()
    subscription = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test-retry",
        "keys": {"p256dh": "A" * 87, "auth": "B" * 22},
    }
    assert family.post("/api/v1/push/subscriptions", json=subscription).status_code == 201
    owner = family.get("/api/v1/me").json()["user"]["id"]
    with engine.begin() as con:
        notify(con, owner, "event-retry", "Aviso interno.")

    def fail(**kw):
        raise RuntimeError("provider unavailable")

    deliver(engine, root, sender=fail)
    with engine.connect() as con:
        device = con.execute(select(db.push_subscriptions)).mappings().one()
        assert device["failures"] == 1 and device["enabled"]
        assert device["next_attempt"] > 0
    calls = []
    deliver(engine, root, sender=lambda **kw: calls.append(kw))
    assert not calls


def test_pwa_public_assets_and_private_cache_headers(env):
    _, _, app, client = env
    family = client()
    manifest = family.get("/manifest.webmanifest")
    assert manifest.status_code == 200 and manifest.json()["display"] == "standalone"
    for icon in manifest.json()["icons"]:
        assert family.get(icon["src"]).status_code == 200
    worker = family.get("/sw.js")
    assert worker.status_code == 200 and worker.headers["service-worker-allowed"] == "/"
    assert family.get("/offline.html").status_code == 200
    assert family.get("/api/dependents").headers["cache-control"] == "no-store"
