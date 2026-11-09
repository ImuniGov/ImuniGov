import hashlib
import sqlite3

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, insert, select, text

from backend import db
from backend.backup import backup, restore
from backend.domain import now
from backend.manage import import_legacy


def test_migrate_legacy_backup_restore(tmp_path, monkeypatch):
    target = tmp_path / "target"
    target.mkdir()
    url = "sqlite:///" + str(target / "app.sqlite3")
    monkeypatch.setenv("DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "head")
    command.upgrade(Config("alembic.ini"), "head")
    engine = db.make_engine(url)
    legacy = tmp_path / "legacy"
    (legacy / "uploads").mkdir(parents=True)
    original = b"synthetic original bytes"
    (legacy / "uploads" / "legacy.png").write_bytes(original)
    con = sqlite3.connect(legacy / "imuniguia.sqlite3")
    con.executescript("""
      CREATE TABLE dependents(id TEXT PRIMARY KEY, name TEXT, created_at TEXT);
      CREATE TABLE documents(id TEXT PRIMARY KEY, dependent_id TEXT, original_name TEXT, stored_name TEXT, content_type TEXT, size INTEGER, sha256 TEXT, vaccine TEXT, dose_date TEXT, family_note TEXT, status TEXT, review_note TEXT, created_at TEXT, reviewed_at TEXT, reviewer TEXT);
      CREATE TABLE audit_events(id INTEGER PRIMARY KEY, document_id TEXT, event TEXT, details TEXT, created_at TEXT);
      INSERT INTO dependents VALUES('person','Sintético','2026-01-01');
      INSERT INTO audit_events VALUES(1,'doc','arquivo_enviado','Entrega antiga','2026-01-01');
    """)
    con.execute(
        "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "doc",
            "person",
            "original.png",
            "legacy.png",
            "image/png",
            len(original),
            hashlib.sha256(original).hexdigest(),
            "BCG",
            "2026-01-01",
            "",
            "pendente",
            "",
            "2026-01-01",
            None,
            "",
        ),
    )
    con.commit()
    con.close()
    first = import_legacy(legacy, engine, target)
    assert first["verified_hashes"] == 1
    assert import_legacy(legacy, engine, target) == first
    with engine.connect() as con:
        person = con.execute(select(db.dependents)).mappings().one()
        assert person["owner_id"] is None
        assert con.scalar(select(func.count()).select_from(db.documents)) == 1
        assert con.scalar(select(func.count()).select_from(db.audit)) == 1
    archive = tmp_path / "backup.tgz"
    before = backup(engine, target, archive)
    restored_dir = tmp_path / "restored"
    restored_dir.mkdir()
    restored_engine = db.make_engine("sqlite:///" + str(restored_dir / "app.sqlite3"))
    db.metadata.create_all(restored_engine)
    assert restore(restored_engine, restored_dir, archive) == before
    assert (restored_dir / "uploads" / "legacy.png").read_bytes() == original
    with pytest.raises(ValueError, match="novo e vazio"):
        restore(restored_engine, restored_dir, archive)
    (legacy / "uploads" / "legacy.png").write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash divergente"):
        import_legacy(legacy, engine, target)
    engine.dispose()
    restored_engine.dispose()


def test_outreach_upgrade_preserves_prior_contacts(tmp_path, monkeypatch):
    url = "sqlite:///" + str(tmp_path / "upgrade.sqlite3")
    monkeypatch.setenv("DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "004")
    engine = db.make_engine(url)
    with engine.begin() as con:
        con.execute(
            insert(db.users).values(
                id="acs",
                name="ACS sintético",
                email="acs@example.test",
                password_hash="not-a-login-hash",
                role="acs",
                created_at=now(),
                privacy_version="test",
            )
        )
        con.execute(
            insert(db.dependents).values(
                id="dep", name="Sintético", owner_id=None, birth_date="2026-01-01", created_at=now()
            )
        )
        con.execute(
            insert(db.rules).values(
                id="rules",
                version="test",
                source="https://example.test",
                valid_from="2026-01-01",
                valid_until="2026-12-31",
                rules=[],
                active=True,
                created_at=now(),
            )
        )
        con.execute(
            insert(db.pendings).values(
                id="pending",
                dependent_id="dep",
                rule_set_id="rules",
                rule_id="one",
                vaccine="BCG",
                dose=1,
                reason="Sintético",
                status="aberta",
                updated_at=now(),
            )
        )
        con.execute(
            text(
                "INSERT INTO outreach_actions(id,pending_id,author_id,kind,note,contact_date,created_at) VALUES(:id,:p,:a,:k,:n,:d,:t)"
            ),
            {
                "id": "old-contact",
                "p": "pending",
                "a": "acs",
                "k": "visita",
                "n": "Contato antigo preservado.",
                "d": "2026-11-08",
                "t": now(),
            },
        )
    command.upgrade(Config("alembic.ini"), "head")
    with engine.connect() as con:
        contact = con.execute(select(db.actions)).mappings().one()
        assert (
            contact["case_id"] == "dep"
            and contact["pending_id"] == "pending"
            and contact["note"] == "Contato antigo preservado."
        )
        assert con.execute(select(db.outreach_cases.c.status)).scalar_one() == "aberta"
    engine.dispose()


def test_round_upgrade_preserves_populated_assignments_and_votes(tmp_path, monkeypatch):
    url = "sqlite:///" + str(tmp_path / "round-upgrade.sqlite3")
    monkeypatch.setenv("DATABASE_URL", url)
    command.upgrade(Config("alembic.ini"), "010")
    engine = db.make_engine(url)
    with engine.begin() as con:
        for identifier, role in (("owner", "familia"), ("reviewer", "ubs")):
            con.execute(
                insert(db.users).values(
                    id=identifier,
                    role=role,
                    name="Sintético",
                    email=identifier + "@example.test",
                    password_hash="not-a-login",
                    privacy_version="test",
                    created_at=now(),
                )
            )
        con.execute(
            insert(db.dependents).values(
                id="person", owner_id="owner", name="Sintético", birth_date="2026-01-01", created_at=now()
            )
        )
        con.execute(
            insert(db.documents).values(
                id="doc",
                dependent_id="person",
                original_name="synthetic.png",
                stored_name="synthetic.png",
                content_type="image/png",
                size=1,
                sha256="a" * 64,
                vaccine="BCG",
                dose_date="2026-01-02",
                family_note="",
                status="pendente",
                review_note="",
                reviewer="",
                created_at=now(),
            )
        )
        con.execute(
            insert(db.review_assignments).values(
                id="assignment",
                document_id="doc",
                reviewer_id="reviewer",
                profile_snapshot={"old": "preserved"},
                status="ativa",
                created_at=now(),
            )
        )
        con.execute(
            insert(db.review_votes).values(
                id="vote",
                assignment_id="assignment",
                target_type="document",
                target_id="doc",
                decision="aprovar",
                note="Nota original",
                guidance="Orientação original",
                independence_confirmed=True,
                evidence_hash="b" * 64,
                created_at=now(),
            )
        )
    command.upgrade(Config("alembic.ini"), "head")
    with engine.begin() as con:
        assert not con.exec_driver_sql("PRAGMA foreign_key_check").all()
        assert con.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
        assert con.execute(select(db.review_votes.c.guidance)).scalar() == "Orientação original"
        assert con.execute(select(db.review_assignments.c.review_round)).scalar() == 1
        con.execute(
            insert(db.review_assignments).values(
                id="new-assignment",
                document_id="doc",
                reviewer_id="reviewer",
                review_round=2,
                profile_snapshot={"new": "snapshot"},
                status="ativa",
                created_at=now(),
            )
        )
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError), engine.begin() as con:
        con.execute(db.review_votes.update().values(note="alterada"))
    engine.dispose()
