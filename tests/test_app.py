import io
from datetime import date

from conftest import acceptance
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from backend import db
from backend.domain import evaluate
from backend.worker import parse_candidates, process_one


def dependent(c):
    r = c.post(
        "/api/dependents",
        json={"name": "Criança Sintética", "birthDate": "2026-01-01", "representationConfirmed": True},
    )
    assert r.status_code == 201, r.text
    return r.json()["item"]["id"]


def image():
    output = io.BytesIO()
    Image.new("RGB", (200, 100), "white").save(output, format="PNG")
    return output.getvalue()


def upload(c, person):
    r = c.post(
        "/api/documents",
        data={"dependentId": person, "vaccine": "BCG", "doseDate": "2026-01-02"},
        files={"file": ("sintetico.png", image(), "image/png")},
    )
    assert r.status_code == 201, r.text
    return r.json()["item"]["id"]


def test_auth_permissions_and_csrf(env):
    engine, root, app, client = env
    anonymous = TestClient(app)
    assert anonymous.get("/api/dependents").status_code == 401
    a, b, acs = client(), client(index=1), client("acs")
    person = dependent(a)
    doc = upload(a, person)
    assert b.get(f"/api/documents/{doc}/file").status_code == 404
    assert b.get(f"/api/v1/dependents/{person}/vaccinations").status_code == 404
    assert acs.get("/api/documents").status_code == 403
    assert acs.get(f"/api/documents/{doc}/file").status_code == 403
    assert (
        a.post(
            f"/api/documents/{doc}/decision", json={"decision": "aprovado", "independenceConfirmed": True}
        ).status_code
        == 403
    )
    old_csrf = a.headers.pop("X-CSRF-Token")
    assert (
        a.post("/api/dependents", json={"name": "Outra pessoa", "birthDate": "2026-02-01"}).status_code == 403
    )
    a.headers["X-CSRF-Token"] = old_csrf
    assert a.post("/api/v1/auth/logout").status_code == 204
    assert a.get("/api/v1/me").status_code == 401
    assert (
        anonymous.post(
            "/api/v1/auth/register",
            json={
                "name": "Teste",
                "email": "x@example.test",
                "password": "long-password-test",
                "consent": True,
            },
            headers={"Origin": "https://evil.example"},
        ).status_code
        == 403
    )


def test_registration_validates_and_never_grants_staff(env):
    engine, root, app, client = env
    c = TestClient(app)
    data = dict(
        name="Pessoa Sintética", email="x@example.test", password="Uma-senha-longa-2026", **acceptance()
    )
    assert c.post("/api/v1/auth/register", json={**data, "role": "ubs"}).status_code == 422
    assert c.post("/api/v1/auth/register", json={**data, "consent": False}).status_code == 422
    assert c.post("/api/v1/auth/register", json={**data, "password": "123"}).status_code == 422
    assert c.post("/api/v1/auth/register", json=data).status_code == 201
    assert c.post("/api/v1/auth/register", json=data).status_code == 409
    with engine.connect() as con:
        user = con.execute(select(db.users).where(db.users.c.email == "x@example.test")).mappings().one()
        assert user["password_hash"].startswith("$argon2")
        assert user["role"] == "familia"


def test_upload_validation_and_decision_identity(env):
    engine, root, app, client = env
    family, ubs = client(), client("ubs")
    person = dependent(family)
    assert (
        family.post(
            "/api/documents",
            data={"dependentId": person, "vaccine": "BCG"},
            files={"file": ("bad.png", b"<script>bad</script>", "image/png")},
        ).status_code
        == 415
    )
    assert (
        family.post(
            "/api/documents",
            data={"dependentId": person, "vaccine": "BCG"},
            files={"file": ("large.png", b"x" * (10 * 1024 * 1024 + 1), "image/png")},
        ).status_code
        == 413
    )
    doc = upload(family, person)
    assert family.get(f"/api/documents/{doc}/file").content == image()
    assert family.delete(f"/api/dependents/{person}").status_code == 409
    assert (
        ubs.post(
            f"/api/documents/{doc}/decision", json={"decision": "rejeitado", "independenceConfirmed": True}
        ).status_code
        == 400
    )
    r = ubs.post(
        f"/api/documents/{doc}/decision",
        json={"decision": "aprovado", "reviewer": "Impostor", "independenceConfirmed": True},
    )
    assert r.status_code == 200 and r.json()["item"]["status"] == "pendente"
    assert "Impostor" not in r.json()["item"]["reviewer"]
    for index in (1, 2):
        assert (
            client("ubs", index)
            .post(
                f"/api/documents/{doc}/decision", json={"decision": "aprovado", "independenceConfirmed": True}
            )
            .status_code
            == 200
        )
    final = family.get(f"/api/documents/{doc}").json()["item"]
    assert final["status"] == "aprovado" and final["review"]["approvals"] == 3
    assert (
        ubs.post(
            f"/api/documents/{doc}/decision", json={"decision": "aprovado", "independenceConfirmed": True}
        ).status_code
        == 409
    )
    assert family.get(f"/api/v1/dependents/{person}/vaccinations").json()["items"] == []
    audit = family.get("/api/audit", params={"documentId": doc}).json()["items"]
    assert any(a["event"] == "revisao_tripla_aprovado" and a["actor_id"] for a in audit)


def test_full_review_pending_guidance_outreach_notification(env):
    engine, root, app, client = env
    family, ubs, acs, other = client(), client("ubs"), client("acs"), client(index=1)
    with engine.begin() as con:
        active = con.execute(select(db.rules)).mappings().one()
        con.execute(db.rules.update().values(rules=[r for r in active["rules"] if r["vaccine"] == "BCG"]))
    person = dependent(family)
    doc = upload(family, person)
    pending = next(
        p
        for p in family.get(f"/api/v1/dependents/{person}/pendings").json()["items"]
        if p["vaccine"] == "BCG"
    )
    cases = acs.get("/api/v1/acs/cases").json()["items"]
    assert any(c["id"] == person for c in cases)
    assert all("vaccine" not in c and "fileUrl" not in c and "birth_date" not in c for c in cases)
    path = f"/api/v1/acs/cases/{person}/actions"
    assert (
        acs.post(
            path,
            json={
                "kind": "telefone",
                "note": "Contato sintético realizado.",
                "contactDate": "2026-11-08",
            },
        ).status_code
        == 201
    )
    for released in (False, True):
        assert (
            ubs.post(
                f"/api/v1/pendings/{pending['id']}/guidance",
                json={"text": "Orientação sintética da equipe.", "released": released},
            ).status_code
            == 201
        )
    assert len(family.get(f"/api/v1/dependents/{person}/guidance").json()["items"]) == 1
    record = ubs.post(
        f"/api/v1/documents/{doc}/candidates", json={"vaccine": "BCG", "dose": 1, "doseDate": "2026-01-02"}
    ).json()["item"]
    decision = f"/api/v1/vaccinations/{record['id']}/decision"
    assert (
        ubs.post(
            decision,
            json={"decision": "validado", "note": "Conferido na evidência.", "independenceConfirmed": True},
        ).status_code
        == 409
    )
    approve_document(client, doc)
    approve_record(client, record["id"])
    assert all(c["id"] != person for c in acs.get("/api/v1/acs/cases").json()["items"])
    assert len(acs.get(path).json()["items"]) == 1  # History survives resolution.
    notes = family.get("/api/v1/notifications").json()["items"]
    assert notes
    assert other.patch("/api/v1/notifications/" + notes[0]["id"], json={"read": True}).status_code == 404
    assert family.patch("/api/v1/notifications/" + notes[0]["id"], json={"read": True}).status_code == 200
    count = len(notes)
    for _ in range(2):
        assert ubs.post(f"/api/v1/dependents/{person}/recalculate").status_code == 200
    assert len(family.get("/api/v1/notifications").json()["items"]) == count


def test_ocr_candidates_idempotency_and_failure(env):
    engine, root, app, client = env
    family = client()
    person = dependent(family)
    doc = upload(family, person)
    assert process_one(engine, root, extractor=lambda p: ("BCG dose 1 02/01/2026", 82))
    assert not process_one(engine, root)
    records = family.get(f"/api/v1/dependents/{person}/vaccinations").json()["items"]
    assert len(records) == 1 and records[0]["status"] == "a_conferir"
    ubs = client("ubs")
    # Re-queue as a recovery scenario: source keys prevent duplication.
    from sqlalchemy import update

    with engine.begin() as con:
        con.execute(update(db.jobs).where(db.jobs.c.document_id == doc).values(status="queued"))
    assert process_one(engine, root, extractor=lambda p: ("BCG dose 1 02/01/2026", 82))
    assert len(family.get(f"/api/v1/dependents/{person}/vaccinations").json()["items"]) == 1
    doc2 = upload(family, person)
    assert process_one(engine, root, extractor=lambda p: ("ilegível", 2))
    assert family.get(f"/api/v1/documents/{doc2}/processing").json()["item"]["status"] == "unreadable"
    assert ubs.post(f"/api/v1/documents/{doc2}/retry").status_code == 200

    def broken(path):
        raise RuntimeError("sensitive internal detail")

    assert process_one(engine, root, extractor=broken)
    state = family.get(f"/api/v1/documents/{doc2}/processing").json()["item"]
    assert state["status"] == "failed" and "sensitive" not in state["error"]


def test_parser_does_not_invent_dates_or_doses():
    assert parse_candidates("Penta 12/01/2026") == []
    assert parse_candidates("Penta dose 1 31/02/2026") == []
    assert parse_candidates("VIP dose 2 01/06/2026")[0]["vaccine"] == "Poliomielite VIP"


def test_rule_boundaries_and_candidates():
    rule = dict(id="r1", vaccine="V", dose=1, due_months=2, max_months=60)
    ruleset = dict(valid_from="2026-01-01", valid_until="2026-12-31", rules=[rule])
    assert not evaluate("2026-01-31", [], ruleset, date(2026, 3, 30))
    assert evaluate("2026-01-31", [], ruleset, date(2026, 3, 31))
    candidate = dict(vaccine="V", dose=1, dose_date="2026-03-31", status="a_conferir")
    assert evaluate("2026-01-31", [candidate], ruleset, date(2026, 4, 1))
    assert not evaluate("2026-01-31", [{**candidate, "status": "validado"}], ruleset, date(2026, 4, 1))
    assert not evaluate("2026-01-31", [], ruleset, date(2027, 1, 1))


def test_rule_intervals():
    ruleset = dict(
        valid_from="2026-01-01",
        valid_until="2026-12-31",
        rules=[
            dict(id="a", vaccine="V", dose=1, due_months=2, max_months=84),
            dict(
                id="b", vaccine="V", dose=2, due_months=4, min_months=0, max_months=84, min_interval_days=30
            ),
        ],
    )
    records = [
        dict(vaccine="V", dose=1, dose_date="2026-03-01", status="validado"),
        dict(vaccine="V", dose=2, dose_date="2026-03-15", status="validado"),
    ]
    assert [x["id"] for x in evaluate("2026-01-01", records, ruleset, date(2026, 8, 1))] == ["b"]
    records[1]["dose_date"] = "2026-04-01"
    assert not evaluate("2026-01-01", records, ruleset, date(2026, 8, 1))


def approve_document(client, doc):
    for index in range(3):
        response = client("ubs", index).post(
            f"/api/documents/{doc}/decision",
            json={"decision": "aprovado", "note": "Conferido no original.", "independenceConfirmed": True},
        )
        assert response.status_code == 200, response.text
        assert response.json()["item"]["status"] == ("aprovado" if index == 2 else "pendente")


def approve_record(client, identifier):
    for index in range(3):
        response = client("ubs", index).post(
            f"/api/v1/vaccinations/{identifier}/decision",
            json={"decision": "validado", "note": "Conferido no original.", "independenceConfirmed": True},
        )
        assert response.status_code == 200, response.text
        assert response.json()["item"]["status"] == ("validado" if index == 2 else "a_conferir")
