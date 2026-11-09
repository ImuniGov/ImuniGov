import importlib
import os
import uuid
from datetime import date

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import insert, select
from sqlalchemy.schema import CreateSchema, DropSchema

from backend import clock, db
from backend.domain import now, seed_rules, uid
from backend.main import create_app
from backend.security import hasher


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 11, 8)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(clock, "today", lambda: date(2026, 11, 8))
    external_url = os.environ.get("TEST_DATABASE_URL")
    base_engine = db.make_engine(external_url or "sqlite:///" + str(tmp_path / "test.sqlite3"))
    schema = "qa_" + uuid.uuid4().hex if external_url else None
    if schema:
        with base_engine.begin() as con:
            con.execute(CreateSchema(schema))
        engine = base_engine.execution_options(schema_translate_map={None: schema})
    else:
        engine = base_engine
    db.metadata.create_all(engine)
    with engine.begin() as con:
        if schema:
            con.exec_driver_sql(f'SET LOCAL search_path TO "{schema}"')
        with Operations.context(MigrationContext.configure(con)):
            importlib.import_module("backend.migrations.versions.002_audit_immutable").upgrade()
            importlib.import_module("backend.migrations.versions.008_immutable_votes").upgrade()
            if con.dialect.name == "postgresql":
                con.exec_driver_sql(
                    "CREATE TRIGGER acceptance_append_only BEFORE UPDATE OR DELETE ON privacy_acceptances FOR EACH ROW EXECUTE FUNCTION deny_audit_mutation()"
                )
            else:
                for action in ("UPDATE", "DELETE"):
                    con.exec_driver_sql(
                        f"CREATE TRIGGER acceptance_no_{action.lower()} BEFORE {action} ON privacy_acceptances BEGIN SELECT RAISE(ABORT,'acceptance is append-only'); END"
                    )
        seed_rules(con)
    app = create_app(engine, tmp_path)
    clients = []
    # Three distinct verified professionals; cities/UFs and all cross-comparisons are independent.
    with engine.begin() as con:
        for index, city in enumerate(("3550308", "3304557", "5103403")):
            identifier = uid()
            con.execute(
                insert(db.users).values(
                    id=identifier,
                    name=f"UBS {index}",
                    email=f"ubs{index}@example.test",
                    password_hash=hasher.hash("Teste-sintetico-longo!"),
                    role="ubs",
                    created_at=now(),
                    privacy_version="2026-11-08",
                )
            )
            con.execute(
                insert(db.reviewer_profiles).values(
                    id=uid(),
                    user_id=identifier,
                    professional_id=f"QA-SINTETICO-{index}",
                    birth_city_code=city,
                    work_city_code=city,
                    verified_at=now(),
                    verification_ref="Evidência sintética de teste",
                )
            )

    def client(role="familia", index=0):
        c = TestClient(app)
        clients.append(c)
        email = f"{role}{index}@example.test"
        password = "Teste-sintetico-longo!"
        if role == "familia":
            r = c.post(
                "/api/v1/auth/register",
                json=dict(name="Pessoa Sintética", email=email, password=password, **acceptance()),
            )
        else:
            if role != "ubs":
                with engine.begin() as con:
                    if not con.execute(select(db.users.c.id).where(db.users.c.email == email)).first():
                        con.execute(
                            insert(db.users).values(
                                id=uid(),
                                name=role.upper(),
                                email=email,
                                password_hash=hasher.hash(password),
                                role=role,
                                created_at=now(),
                                privacy_version="2026-11-08",
                            )
                        )
            r = c.post("/api/v1/auth/login", json=dict(email=email, password=password))
        assert r.status_code in (200, 201), r.text
        c.headers["X-CSRF-Token"] = r.json()["csrf"]
        return c

    yield engine, tmp_path, app, client
    for c in clients:
        c.close()
    if schema:
        with base_engine.begin() as con:
            con.execute(DropSchema(schema, cascade=True))
    base_engine.dispose()


def acceptance():
    from backend.privacy import policy

    p = policy()
    return dict(
        consent=True,
        healthConsent=True,
        adultDeclaration=True,
        termsVersion=p["version"],
        privacyHash=p["hash"],
    )
