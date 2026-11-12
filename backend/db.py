import os
from pathlib import Path

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    event,
    false,
    true,
)

metadata = MetaData()


def table(name, *columns, **kw):
    return Table(name, metadata, Column("id", String(64), primary_key=True), *columns, **kw)


def text(name, *args, **kw):
    return Column(name, Text, *args, **kw)


users = table(
    "users",
    text("name", nullable=False),
    Column("email", String(254), unique=True, nullable=False),
    text("password_hash", nullable=False),
    Column("role", String(16), nullable=False),
    text("created_at", nullable=False),
    text("privacy_version", nullable=False),
    CheckConstraint("role IN ('familia','ubs','acs')"),
)
consent_controls = table(
    "consent_controls",
    text("user_id", ForeignKey("users.id"), nullable=False, unique=True),
    Column("withdrawn", Boolean, nullable=False),
    text("updated_at", nullable=False),
)
acceptances = table(
    "privacy_acceptances",
    text("user_id", ForeignKey("users.id"), nullable=False),
    text("version", nullable=False),
    text("policy_hash", nullable=False),
    Column("terms_accepted", Boolean, nullable=False),
    Column("health_consent", Boolean, nullable=False),
    Column("adult_declaration", Boolean, nullable=False),
    text("accepted_at", nullable=False),
)
privacy_requests = table(
    "privacy_requests",
    text("user_id", ForeignKey("users.id"), nullable=False),
    text("kind", nullable=False),
    text("message", nullable=False),
    text("status", nullable=False),
    text("response", nullable=False),
    text("created_at", nullable=False),
    text("answered_at"),
)
sessions = table(
    "sessions",
    text("user_id", ForeignKey("users.id"), nullable=False),
    text("csrf", nullable=False),
    Column("expires", Integer, nullable=False),
)
password_resets = table(
    "password_resets",
    text("user_id", ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
    Column("expires", Integer, nullable=False),
)
attempts = table(
    "auth_attempts", Column("expires", Integer, nullable=False), Column("count", Integer, nullable=False)
)
dependents = table(
    "dependents",
    text("owner_id", ForeignKey("users.id")),
    text("name", nullable=False),
    Column("birth_date", String(10)),
    text("created_at", nullable=False),
)
documents = table(
    "documents",
    text("dependent_id", ForeignKey("dependents.id"), nullable=False),
    text("original_name", nullable=False),
    text("stored_name", unique=True, nullable=False),
    text("content_type", nullable=False),
    Column("size", Integer, nullable=False),
    text("sha256", nullable=False),
    text("vaccine", nullable=False),
    Column("dose_date", String(10)),
    text("family_note", nullable=False),
    text("status", nullable=False),
    text("review_note", nullable=False),
    text("review_guidance", nullable=False, server_default=""),
    text("created_at", nullable=False),
    text("reviewed_at"),
    text("reviewer", nullable=False),
    Column("review_round", Integer, nullable=False, server_default="1"),
    Column("review_hold", Boolean, nullable=False, server_default=false()),
    CheckConstraint("status IN ('pendente','aprovado','rejeitado')"),
)
audit = table(
    "audit_events",
    text("actor_id", ForeignKey("users.id")),
    text("target_type", nullable=False),
    text("target_id", nullable=False),
    text("event", nullable=False),
    text("details", nullable=False),
    text("created_at", nullable=False),
)
jobs = table(
    "ocr_jobs",
    text("document_id", ForeignKey("documents.id"), nullable=False, unique=True),
    text("status", nullable=False),
    Column("attempts", Integer, nullable=False),
    text("updated_at", nullable=False),
    text("error", nullable=False),
    text("raw_text", nullable=False),
)
vaccinations = table(
    "vaccinations",
    text("dependent_id", ForeignKey("dependents.id"), nullable=False),
    text("document_id", ForeignKey("documents.id")),
    text("vaccine", nullable=False),
    Column("dose", Integer, nullable=False),
    Column("dose_date", String(10)),
    text("status", nullable=False),
    text("origin", nullable=False),
    Column("confidence", Integer),
    text("source_key", unique=True, nullable=False),
    text("reviewer_id", ForeignKey("users.id")),
    text("review_note", nullable=False),
    text("review_guidance", nullable=False, server_default=""),
    text("created_at", nullable=False),
    text("reviewed_at"),
    CheckConstraint("status IN ('a_conferir','validado','recusado')"),
)
rules = table(
    "rule_sets",
    text("version", unique=True, nullable=False),
    text("source", nullable=False),
    text("valid_from", nullable=False),
    text("valid_until", nullable=False),
    Column("rules", JSON, nullable=False),
    Column("active", Boolean, nullable=False),
    text("created_at", nullable=False),
)
pendings = table(
    "pendings",
    text("dependent_id", ForeignKey("dependents.id"), nullable=False),
    text("rule_set_id", ForeignKey("rule_sets.id"), nullable=False),
    text("rule_id", nullable=False),
    text("vaccine", nullable=False),
    Column("dose", Integer, nullable=False),
    text("reason", nullable=False),
    text("status", nullable=False),
    text("updated_at", nullable=False),
    UniqueConstraint("dependent_id", "rule_set_id", "rule_id"),
)
guidance = table(
    "guidance",
    text("pending_id", ForeignKey("pendings.id"), nullable=False),
    text("author_id", ForeignKey("users.id"), nullable=False),
    text("text", nullable=False),
    Column("released", Boolean, nullable=False),
    text("created_at", nullable=False),
)
notifications = table(
    "notifications",
    text("user_id", ForeignKey("users.id"), nullable=False),
    text("event_key", unique=True, nullable=False),
    text("message", nullable=False),
    Column("read", Boolean, nullable=False),
    text("created_at", nullable=False),
)
outreach_cases = table(
    "outreach_cases",
    text("dependent_id", ForeignKey("dependents.id"), unique=True, nullable=False),
    text("status", nullable=False),
    text("created_at", nullable=False),
    text("updated_at", nullable=False),
    CheckConstraint("status IN ('aberta','resolvida')"),
)
actions = table(
    "outreach_actions",
    text("pending_id", ForeignKey("pendings.id")),
    text("case_id", ForeignKey("outreach_cases.id"), nullable=False),
    text("author_id", ForeignKey("users.id"), nullable=False),
    text("kind", nullable=False),
    text("note", nullable=False),
    text("contact_date", nullable=False),
    text("created_at", nullable=False),
)


dose_plans = table(
    "dose_plans",
    text("dependent_id", ForeignKey("dependents.id"), nullable=False),
    text("vaccine", nullable=False),
    Column("dose", Integer, nullable=False),
    text("due_date", nullable=False),
    text("author_id", ForeignKey("users.id"), nullable=False),
    text("note", nullable=False),
    text("status", nullable=False),
    text("created_at", nullable=False),
    text("updated_at", nullable=False),
    text("record_id", ForeignKey("vaccinations.id")),
    CheckConstraint("status IN ('ativa','concluida','cancelada')"),
)

push_subscriptions = table(
    "push_subscriptions",
    text("user_id", ForeignKey("users.id"), nullable=False),
    text("session_id", nullable=False),
    text("endpoint", unique=True, nullable=False),
    Column("keys", JSON, nullable=False),
    Column("enabled", Boolean, nullable=False),
    text("last_sent_at", nullable=False),
    Column("failures", Integer, nullable=False),
    Column("next_attempt", Integer, nullable=False),
    text("created_at", nullable=False),
)


review_gate = table("review_gate", Column("revision", Integer, nullable=False, server_default="1"))


review_assignments = table(
    "review_assignments",
    text("document_id", ForeignKey("documents.id"), nullable=False),
    text("reviewer_id", ForeignKey("users.id"), nullable=False),
    text("created_at", nullable=False),
    text("status", nullable=False, server_default="ativa"),
    Column("profile_snapshot", JSON, nullable=False),
    Column("review_round", Integer, nullable=False, server_default="1"),
    UniqueConstraint("document_id", "reviewer_id", "review_round", name="uq_assignment_round"),
)

reviewer_profiles = table(
    "reviewer_profiles",
    text("user_id", ForeignKey("users.id"), unique=True, nullable=False),
    text("professional_id", unique=True, nullable=False),
    Column("birth_city_code", String(7), nullable=False),
    Column("work_city_code", String(7), nullable=False),
    text("verified_at", nullable=False),
    text("verification_ref", nullable=False),
    Column("active", Boolean, nullable=False, server_default=true()),
)

reviewer_changes = table(
    "reviewer_changes",
    text("profile_id", ForeignKey("reviewer_profiles.id"), nullable=False),
    Column("before", JSON, nullable=False),
    Column("after", JSON, nullable=False),
    text("reason", nullable=False),
    text("verification_ref", nullable=False),
    text("created_at", nullable=False),
)

review_incidents = table(
    "review_incidents",
    text("document_id", ForeignKey("documents.id"), nullable=False),
    text("assignment_id", ForeignKey("review_assignments.id"), nullable=False, unique=True),
    text("reporter_id", ForeignKey("users.id"), nullable=False),
    Column("source_round", Integer, nullable=False),
    text("reason", nullable=False),
    text("origin", nullable=False),
    text("administrative_ref", nullable=False),
    text("created_at", nullable=False),
)
review_resolutions = table(
    "review_resolutions",
    text("incident_id", ForeignKey("review_incidents.id"), nullable=False, unique=True),
    text("administrative_ref", nullable=False),
    text("note", nullable=False),
    text("created_at", nullable=False),
)

review_votes = table(
    "review_votes",
    text("assignment_id", ForeignKey("review_assignments.id"), nullable=False),
    text("target_type", nullable=False),
    text("target_id", nullable=False),
    text("decision", nullable=False),
    text("note", nullable=False),
    text("guidance", nullable=False),
    Column("independence_confirmed", Boolean, nullable=False),
    text("evidence_hash", nullable=False),
    text("created_at", nullable=False),
    UniqueConstraint("assignment_id", "target_type", "target_id"),
)


def make_engine(url=None):
    data = Path(os.environ.get("IMUNIGUI_DATA_DIR", "data")).resolve()
    data.mkdir(parents=True, exist_ok=True)
    url = url or os.environ.get("DATABASE_URL", f"sqlite:///{data / 'app.sqlite3'}")
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {},
        pool_pre_ping=True,
    )
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def sqlite_pragmas(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")

    return engine
