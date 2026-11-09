# Frozen schema for revision 001. Do not modify after release.

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
sessions = table(
    "sessions",
    text("user_id", ForeignKey("users.id"), nullable=False),
    text("csrf", nullable=False),
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
    text("created_at", nullable=False),
    text("reviewed_at"),
    text("reviewer", nullable=False),
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
actions = table(
    "outreach_actions",
    text("pending_id", ForeignKey("pendings.id"), nullable=False),
    text("author_id", ForeignKey("users.id"), nullable=False),
    text("kind", nullable=False),
    text("note", nullable=False),
    text("contact_date", nullable=False),
    text("created_at", nullable=False),
)
