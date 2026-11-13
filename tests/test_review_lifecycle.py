from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError
from test_app import approve_document, approve_record, dependent, upload

from backend import db
from backend.domain import now, uid
from backend.reviews import (
    assign_document,
    change_reviewer,
    list_incidents,
    report_incident,
    resolve_incident,
)
from backend.security import hasher


def change(engine, active=True, birth=None, work=None, apply=True):
    with engine.begin() as con:
        preview = change_reviewer(
            con,
            "ubs0@example.test",
            active,
            birth,
            work,
            "Conferência documental sintética 2",
            "Alteração sintética para teste",
            apply=False,
        )
        if not apply:
            return preview
        return change_reviewer(
            con,
            "ubs0@example.test",
            active,
            birth,
            work,
            "Conferência documental sintética 2",
            "Alteração sintética para teste",
            apply=True,
            expected_version=preview["expectedVersion"],
        )


def test_profile_preview_and_new_round_preserve_votes(env):
    engine, root, app, client = env
    family, reviewer = client(), client("ubs")
    doc = upload(family, dependent(family))
    assert (
        reviewer.post(
            f"/api/documents/{doc}/decision",
            json={"decision": "aprovado", "reviewRound": 1, "independenceConfirmed": True},
        ).status_code
        == 200
    )
    assert change(engine, apply=False)["unfinishedRoundsToRestart"] == 1
    assert family.get(f"/api/documents/{doc}").json()["item"]["review"]["approvals"] == 1
    change(engine)
    item = family.get(f"/api/documents/{doc}").json()["item"]
    assert item["status"] == "pendente" and item["review"]["round"] == 2
    assert item["review"]["approvals"] == 0 and item["review"]["assigned"] == 3
    history = family.get(f"/api/v1/documents/{doc}/review-history").json()["items"]
    assert len(history) == 1 and history[0]["review_round"] == 1
    assert history[0]["professional"] == "UBS 0"
    exported = family.get("/api/v1/privacy/export").json()
    assert len(exported["dependents"][0]["documents"][0]["reviewHistory"]) == 1
    assert reviewer.get(f"/api/documents/{doc}/file").status_code == 401
    approve_document(client, doc)
    assert family.get(f"/api/documents/{doc}").json()["item"]["review"]["approvals"] == 3
    with engine.connect() as con:
        assert con.scalar(select(func.count()).select_from(db.review_votes)) == 4
        history = con.execute(select(db.reviewer_changes)).mappings().one()
        assert history["before"]["verified_at"] != history["after"]["verified_at"]
    with pytest.raises(DBAPIError), engine.begin() as con:
        con.execute(update(db.reviewer_changes).values(reason="Troca indevida"))


def test_suspension_waits_without_relaxing_and_requires_verified_reactivation(env):
    engine, root, app, client = env
    family = client()
    doc = upload(family, dependent(family))
    change(engine, active=False)
    item = family.get(f"/api/documents/{doc}").json()["item"]
    assert item["review"]["waitingForTeam"] and item["review"]["assigned"] == 0
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        assert (
            c.post(
                "/api/v1/auth/login",
                json={"email": "ubs0@example.test", "password": "Teste-sintetico-longo!"},
            ).status_code
            == 403
        )
    # Crossing birth/work into SP makes the third person incompatible with another reviewer.
    with engine.begin() as con:
        from backend.reviews import lock_roster

        lock_roster(con)
        profile = (
            con.execute(
                select(db.reviewer_profiles)
                .join(db.users, db.users.c.id == db.reviewer_profiles.c.user_id)
                .where(db.users.c.email == "ubs1@example.test")
            )
            .mappings()
            .one()
        )
        con.execute(
            update(db.reviewer_profiles)
            .where(db.reviewer_profiles.c.id == profile["id"])
            .values(work_city_code="3550308")
        )
    change(engine, active=True)
    assert family.get(f"/api/documents/{doc}").json()["item"]["review"]["waitingForTeam"]


def test_completed_record_retains_original_three_authors_after_round_restart(env):
    engine, root, app, client = env
    family, reviewer = client(), client("ubs")
    person = dependent(family)
    doc = upload(family, person)
    record = reviewer.post(
        f"/api/v1/documents/{doc}/candidates", json={"vaccine": "BCG", "dose": 1, "doseDate": "2026-01-02"}
    ).json()["item"]
    approve_document(client, doc)
    approve_record(client, record["id"])
    # OCR remains queued, so unfinished work may produce further candidates.
    change(engine)
    records = family.get(f"/api/v1/dependents/{person}/vaccinations").json()["items"]
    assert records[0]["status"] == "validado"
    assert records[0]["review"]["round"] == 1 and records[0]["review"]["approvals"] == 3
    assert len(records[0]["review"]["reviewers"]) == 3
    assert family.get(f"/api/documents/{doc}").json()["item"]["review"]["round"] == 2


def test_concurrent_votes_finalize_once_and_duplicate_vote_is_rejected(env):
    engine, root, app, client = env
    family = client()
    doc = upload(family, dependent(family))
    reviewers = [client("ubs", i) for i in range(3)]
    barrier = Barrier(3)

    def vote(c):
        barrier.wait(timeout=15)
        return c.post(
            f"/api/documents/{doc}/decision",
            json={"decision": "aprovado", "reviewRound": 1, "independenceConfirmed": True},
        )

    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(vote, reviewers))
    assert [r.status_code for r in responses] == [200, 200, 200]
    assert family.get(f"/api/documents/{doc}").json()["item"]["review"]["approvals"] == 3
    with engine.connect() as con:
        assert (
            con.scalar(
                select(func.count())
                .select_from(db.audit)
                .where(db.audit.c.target_id == doc, db.audit.c.event == "revisao_tripla_aprovado")
            )
            == 1
        )
    # A separate pending document exercises duplicate submissions before terminal status.
    another = upload(family, dependent(family))
    duplicate_barrier = Barrier(2)

    def duplicate(_):
        duplicate_barrier.wait(timeout=15)
        return (
            reviewers[0]
            .post(
                f"/api/documents/{another}/decision",
                json={"decision": "aprovado", "reviewRound": 1, "independenceConfirmed": True},
            )
            .status_code
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(duplicate, range(2))) == [200, 409]


def test_concurrent_allocation_does_not_add_extra_reviewers(env):
    engine, root, app, client = env
    family = client()
    doc = upload(family, dependent(family))
    with engine.begin() as con:
        con.execute(delete(db.review_assignments).where(db.review_assignments.c.document_id == doc))
    barrier = Barrier(3)

    def allocate(_):
        barrier.wait(timeout=15)
        with engine.begin() as con:
            return [a["id"] for a in assign_document(con, doc)]

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(allocate, range(3)))
    assert all(len(ids) == 3 and set(ids) == set(results[0]) for ids in results)


def test_stale_vote_cannot_be_applied_to_new_round(env):
    engine, root, app, client = env
    family = client()
    doc = upload(family, dependent(family))
    change(engine)
    reviewer = client("ubs")
    response = reviewer.post(
        f"/api/documents/{doc}/decision",
        json={"decision": "aprovado", "independenceConfirmed": True, "reviewRound": 1},
    )
    assert response.status_code == 409
    assert family.get(f"/api/documents/{doc}").json()["item"]["review"]["approvals"] == 0


def test_profile_change_racing_vote_never_counts_old_vote_in_new_round(env):
    engine, root, app, client = env
    family, reviewer = client(), client("ubs")
    doc = upload(family, dependent(family))
    barrier = Barrier(2)

    def vote():
        barrier.wait(timeout=15)
        return reviewer.post(
            f"/api/documents/{doc}/decision",
            json={"decision": "aprovado", "independenceConfirmed": True, "reviewRound": 1},
        ).status_code

    def change_profile():
        barrier.wait(timeout=15)
        return change(engine)

    with ThreadPoolExecutor(max_workers=2) as pool:
        vote_result = pool.submit(vote)
        profile_result = pool.submit(change_profile)
        assert vote_result.result(timeout=30) in (200, 401, 403, 409)
        assert profile_result.result(timeout=30)["unfinishedRoundsToRestart"] == 1
    item = family.get(f"/api/documents/{doc}").json()["item"]
    assert item["review"]["round"] == 2 and item["review"]["approvals"] == 0


def test_completed_document_is_preserved_until_new_work_arrives(env):
    engine, root, app, client = env
    family = client()
    doc = upload(family, dependent(family))
    approve_document(client, doc)
    with engine.begin() as con:
        con.execute(update(db.jobs).where(db.jobs.c.document_id == doc).values(status="completed"))
    assert change(engine)["completedDecisionsPreserved"] == 1
    previous = family.get(f"/api/documents/{doc}").json()["item"]
    assert previous["status"] == "aprovado" and previous["review"]["approvals"] == 3
    assert previous["review"]["assigned"] == 3
    second = client("ubs", 1)
    assert (
        second.post(
            f"/api/v1/documents/{doc}/candidates",
            json={"vaccine": "BCG", "dose": 1, "doseDate": "2026-01-02"},
        ).status_code
        == 201
    )
    with engine.begin() as con:
        assign_document(con, doc)
    current = family.get(f"/api/documents/{doc}").json()["item"]
    assert current["status"] == "pendente" and current["review"]["round"] == 2


def test_changed_profile_preview_cannot_be_reused(env):
    engine, root, app, client = env
    preview = change(engine, apply=False)
    change(engine)
    with pytest.raises(ValueError, match="perfil mudou"), engine.begin() as con:
        change_reviewer(
            con,
            "ubs0@example.test",
            False,
            None,
            None,
            "Protocolo sintético",
            "Suspensão sintética",
            apply=True,
            expected_version=preview["expectedVersion"],
        )


def _add_fourth_reviewer(engine):
    with engine.begin() as con:
        identifier = uid()
        con.execute(
            db.users.insert().values(
                id=identifier,
                name="UBS 3",
                email="ubs3@example.test",
                password_hash=hasher.hash("Teste-sintetico-longo!"),
                role="ubs",
                created_at=now(),
                privacy_version="2026-11-08",
            )
        )
        con.execute(
            db.reviewer_profiles.insert().values(
                id=uid(),
                user_id=identifier,
                professional_id="QA-SINTETICO-3",
                birth_city_code="4106902",
                work_city_code="4106902",
                verified_at=now(),
                verification_ref="Evidência sintética 3",
            )
        )


def test_late_impediment_suspends_confirmed_evidence_and_resolves_with_new_panel(env):
    engine, root, app, client = env
    family, ubs0, ubs1, ubs2 = client(), client("ubs", 0), client("ubs", 1), client("ubs", 2)
    person = dependent(family)
    doc = upload(family, person)
    plan = ubs0.post(
        f"/api/v1/dependents/{person}/dose-plans",
        json={"vaccine": "BCG", "dose": 1, "dueDate": "2026-11-20", "note": "Planejamento inicial"},
    ).json()["item"]
    record = ubs0.post(
        f"/api/v1/documents/{doc}/candidates",
        json={"vaccine": "BCG", "dose": 1, "doseDate": "2026-01-02"},
    ).json()["item"]
    approve_document(client, doc)
    approve_record(client, record["id"])

    # Before late impediment: dose is validated, plan is completed, BCG pending is resolved.
    assert family.get(f"/api/v1/dependents/{person}/vaccinations").json()["items"][0]["status"] == "validado"
    assert family.get(f"/api/v1/dependents/{person}/dose-plans").json()["items"][0]["status"] == "concluida"
    assert not any(
        p["vaccine"] == "BCG" for p in family.get(f"/api/v1/dependents/{person}/pendings").json()["open"]
    )

    # Administrative report of late impediment discovered after ubs0 voted.
    with engine.begin() as con:
        inc = report_incident(
            con,
            doc,
            "ubs0@example.test",
            "PROC-ADM-2026-01",
            "Vínculo familiar indireto identificado após conclusão da rodada 1.",
        )
        assert inc["hold"] is True and inc["incidentId"]
        with pytest.raises(ValueError, match="já registrado|não pertence"):
            report_incident(con, doc, "ubs0@example.test", "PROC-ADM-2026-01", "Duplicado")
        open_list = list_incidents(con, only_open=True)
        assert len(open_list) == 1 and open_list[0]["id"] == inc["incidentId"]

    # Effects of hold: document and dose confirmations withdrawn, plan and pending reopened, ubs0 blocked.
    held_doc = family.get(f"/api/documents/{doc}").json()["item"]
    assert held_doc["status"] == "pendente" and held_doc["reviewHold"] is True
    assert (
        family.get(f"/api/v1/dependents/{person}/vaccinations").json()["items"][0]["status"] == "a_conferir"
    )
    assert family.get(f"/api/v1/dependents/{person}/dose-plans").json()["items"][0]["status"] == "ativa"
    assert any(
        p["vaccine"] == "BCG" for p in family.get(f"/api/v1/dependents/{person}/pendings").json()["open"]
    )
    assert ubs0.get(f"/api/documents/{doc}/file").status_code == 403
    assert (
        ubs1.post(
            f"/api/documents/{doc}/decision",
            json={"decision": "aprovado", "reviewRound": 1, "independenceConfirmed": True},
        ).status_code
        == 409
    )
    assert (
        ubs1.post(
            f"/api/v1/documents/{doc}/candidates",
            json={"vaccine": "Pentavalente", "dose": 1, "doseDate": "2026-03-02"},
        ).status_code
        == 409
    )

    # Add 4th compatible reviewer so round 2 can form a full 3-person panel without ubs0.
    _add_fourth_reviewer(engine)
    ubs3 = client("ubs", 3)

    with engine.begin() as con:
        res = resolve_incident(
            con,
            inc["incidentId"],
            "DESPACHO-ADM-2026-02",
            "Confirmado impedimento de ubs0; aberta nova rodada com equipe independente.",
        )
        assert res["resolved"] is True and res["hold"] is False
        assert res["newRound"] == 2 and res["assigned"] == 3 and not res["waitingForTeam"]
        with pytest.raises(ValueError, match="já resolvida"):
            resolve_incident(con, inc["incidentId"], "DESPACHO-ADM-2026-02", "Repetição")
        assert list_incidents(con, only_open=True) == []
        assert len(list_incidents(con, only_open=False)) == 1

    # Immutability of incidents and resolutions tables.
    for table, values in (
        (db.review_incidents, {"reason": "adulterado"}),
        (db.review_resolutions, {"note": "adulterada"}),
    ):
        for stmt in (update(table).values(**values), delete(table)):
            with pytest.raises(DBAPIError), engine.begin() as con:
                con.execute(stmt)

    # Round 2 state: administration did NOT approve document or dose; prior votes preserved; ubs3 is blind to round 1 notes.
    round2_doc = family.get(f"/api/documents/{doc}").json()["item"]
    assert round2_doc["status"] == "pendente" and round2_doc["reviewHold"] is False
    assert round2_doc["review"]["round"] == 2 and round2_doc["review"]["approvals"] == 0
    history = family.get(f"/api/v1/documents/{doc}/review-history").json()["items"]
    assert len(history) == 6 and all(h["review_round"] == 1 for h in history)
    ubs3_audit = ubs3.get("/api/audit", params={"documentId": doc}).json()["items"]
    assert not any(
        a["event"] in ("rodada_anterior_preservada", "decisao_documento_suspensa_impedimento")
        for a in ubs3_audit
    )

    # New independent panel (ubs1, ubs2, ubs3) completes round 2 review.
    for reviewer in (ubs1, ubs2, ubs3):
        r_doc = reviewer.post(
            f"/api/documents/{doc}/decision",
            json={
                "decision": "aprovado",
                "note": "Conferido na rodada 2.",
                "reviewRound": 2,
                "independenceConfirmed": True,
            },
        )
        assert r_doc.status_code == 200, r_doc.text
    for reviewer in (ubs1, ubs2, ubs3):
        r_vac = reviewer.post(
            f"/api/v1/vaccinations/{record['id']}/decision",
            json={
                "decision": "validado",
                "note": "Dose validada na rodada 2.",
                "reviewRound": 2,
                "independenceConfirmed": True,
            },
        )
        assert r_vac.status_code == 200, r_vac.text

    assert family.get(f"/api/documents/{doc}").json()["item"]["status"] == "aprovado"
    final_vac = family.get(f"/api/v1/dependents/{person}/vaccinations").json()["items"][0]
    assert final_vac["status"] == "validado" and final_vac["review"]["round"] == 2
    assert {r["name"] for r in final_vac["review"]["reviewers"]} == {"UBS 1", "UBS 2", "UBS 3"}
    assert family.get(f"/api/v1/dependents/{person}/dose-plans").json()["items"][0]["status"] == "concluida"
    assert plan["id"] == family.get(f"/api/v1/dependents/{person}/dose-plans").json()["items"][0]["id"]


def test_concurrent_vote_and_late_impediment(env):
    engine, root, app, client = env
    family, ubs0, ubs1 = client(), client("ubs", 0), client("ubs", 1)
    doc = upload(family, dependent(family))
    assert (
        ubs0.post(
            f"/api/documents/{doc}/decision",
            json={"decision": "aprovado", "reviewRound": 1, "independenceConfirmed": True},
        ).status_code
        == 200
    )
    barrier = Barrier(2)

    def vote_ubs1():
        barrier.wait(timeout=15)
        return ubs1.post(
            f"/api/documents/{doc}/decision",
            json={"decision": "aprovado", "reviewRound": 1, "independenceConfirmed": True},
        ).status_code

    def impediment_ubs0():
        barrier.wait(timeout=15)
        return ubs0.post(
            f"/api/v1/documents/{doc}/impediment",
            json={"reason": "Impedimento posterior percebido em concorrência."},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_vote = pool.submit(vote_ubs1)
        f_imp = pool.submit(impediment_ubs0)
        assert f_vote.result(timeout=30) in (200, 409)
        assert f_imp.result(timeout=30) == 200

    item = family.get(f"/api/documents/{doc}").json()["item"]
    assert item["reviewHold"] is True and item["status"] == "pendente"
