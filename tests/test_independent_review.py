import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError
from test_app import dependent, upload

from backend import db
from backend.geography import compatible, location
from backend.reviews import choose_panel


def test_cross_birth_work_and_interstate_ride():
    def snapshot(birth, work):
        return {"birth": location(birth), "work": location(work)}

    assert not compatible(snapshot("3550308", "3304557"), snapshot("5103403", "3550308"))
    # Brasília and Luziânia are in distinct UFs, but share the official RIDE.
    assert not compatible(snapshot("5300108", "5300108"), snapshot("5212501", "5212501"))
    assert compatible(snapshot("3550308", "3550308"), snapshot("5103403", "5103403"))
    profiles = [
        {"user_id": str(i), "snapshot": snapshot(city, city)}
        for i, city in enumerate(("3550308", "3304557", "5103403"))
    ]
    assert len(choose_panel(profiles)) == 3
    assert choose_panel(profiles[:2]) == []
    with pytest.raises(ValueError):
        location("0000000")


def test_waits_for_complete_team_and_restricts_unassigned(env):
    engine, root, app, client = env
    with engine.begin() as con:
        con.execute(delete(db.reviewer_profiles))
    family, ubs = client(), client("ubs")
    doc = upload(family, dependent(family))
    item = family.get(f"/api/documents/{doc}").json()["item"]
    assert item["review"]["waitingForTeam"] and item["review"]["assigned"] == 0
    assert ubs.get(f"/api/documents/{doc}/file").status_code == 403
    assert ubs.get("/api/documents").json()["items"] == []


def test_refusal_is_visible_with_reason_next_step_and_author(env):
    engine, root, app, client = env
    family, other, ubs = client(), client(index=1), client("ubs")
    doc = upload(family, dependent(family))
    path = f"/api/documents/{doc}/decision"
    body = dict(
        decision="rejeitado", note="Data ilegível na foto.", guidance="Envie outra foto com a data visível."
    )
    assert ubs.post(path, json=body).status_code == 422
    assert ubs.post(path, json={**body, "independenceConfirmed": False}).status_code == 422
    assert (
        ubs.post(
            path, json={**body, "guidance": "", "reviewRound": 1, "independenceConfirmed": True}
        ).status_code
        == 400
    )
    response = ubs.post(path, json={**body, "reviewRound": 1, "independenceConfirmed": True})
    assert response.status_code == 200
    item = family.get("/api/v1/family/feedback").json()["items"][0]
    assert item["reason"] == body["note"] and item["nextStep"] == body["guidance"]
    assert item["at"] and item["reviewers"][0]["name"] == "UBS 0"
    assert other.get("/api/v1/family/feedback").json()["items"] == []
    assert ubs.post(path, json={**body, "reviewRound": 1, "independenceConfirmed": True}).status_code == 409


def test_votes_are_blind_and_impediment_stops_access(env):
    engine, root, app, client = env
    family, ubs, second = client(), client("ubs"), client("ubs", 1)
    doc = upload(family, dependent(family))
    assert (
        ubs.post(
            f"/api/documents/{doc}/decision",
            json=dict(
                decision="aprovado",
                note="Minha avaliação independente.",
                reviewRound=1,
                independenceConfirmed=True,
            ),
        ).status_code
        == 200
    )
    pending = second.get(f"/api/documents/{doc}").json()["item"]
    assert pending["status"] == "pendente" and pending["review"]["myVote"] is None
    assert pending["review"]["votesReceived"] is None and pending["review"]["reviewers"] == []
    audit = second.get("/api/audit", params={"documentId": doc}).json()["items"]
    assert not any(i["details"] == "Minha avaliação independente." for i in audit)
    assert (
        second.post(f"/api/v1/documents/{doc}/impediment", json={"reason": "Conheço a família."}).status_code
        == 200
    )
    assert second.get(f"/api/documents/{doc}/file").status_code == 403
    assert family.get(f"/api/documents/{doc}").json()["item"]["review"]["waitingForTeam"]
    late = ubs.post(f"/api/v1/documents/{doc}/impediment", json={"reason": "Conflito percebido após votar."})
    assert late.status_code == 200 and late.json()["hold"] is True and late.json()["incidentId"]
    assert ubs.get(f"/api/documents/{doc}/file").status_code == 403
    held = family.get(f"/api/documents/{doc}").json()["item"]
    assert held["reviewHold"] is True and held["review"]["onHold"] is True
    with engine.connect() as con:
        assert len(con.execute(select(db.review_votes)).all()) == 1
        assert len(con.execute(select(db.review_incidents)).all()) == 1


def test_votes_and_acceptances_cannot_be_rewritten(env):
    engine, root, app, client = env
    family, ubs = client(), client("ubs")
    doc = upload(family, dependent(family))
    assert (
        ubs.post(
            f"/api/documents/{doc}/decision",
            json=dict(decision="aprovado", reviewRound=1, independenceConfirmed=True),
        ).status_code
        == 200
    )
    for table, values in (
        (db.review_votes, {"decision": "recusar"}),
        (db.acceptances, {"version": "fabricada"}),
    ):
        for statement in (update(table).values(**values), delete(table)):
            with pytest.raises(DBAPIError), engine.begin() as con:
                con.execute(statement)
