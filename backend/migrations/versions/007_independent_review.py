"""Require three independent, geographically compatible approvals; preserve prior decisions in audit."""

import json
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reviewer_profiles",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Text, sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("professional_id", sa.Text, unique=True, nullable=False),
        sa.Column("birth_city_code", sa.String(7), nullable=False),
        sa.Column("work_city_code", sa.String(7), nullable=False),
        sa.Column("verified_at", sa.Text, nullable=False),
        sa.Column("verification_ref", sa.Text, nullable=False),
    )
    op.create_table(
        "review_votes",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("assignment_id", sa.Text, sa.ForeignKey("review_assignments.id"), nullable=False),
        sa.Column("target_type", sa.Text, nullable=False),
        sa.Column("target_id", sa.Text, nullable=False),
        sa.Column("decision", sa.Text, nullable=False),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("guidance", sa.Text, nullable=False),
        sa.Column("independence_confirmed", sa.Boolean, nullable=False),
        sa.Column("evidence_hash", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.UniqueConstraint("assignment_id", "target_type", "target_id"),
    )
    con = op.get_bind()
    audit = sa.table(
        "audit_events",
        sa.column("id"),
        sa.column("actor_id"),
        sa.column("target_type"),
        sa.column("target_id"),
        sa.column("event"),
        sa.column("details"),
        sa.column("created_at"),
    )
    timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    for table, kind, state_column, pending in [
        ("documents", "document", "status", "pendente"),
        ("vaccinations", "vaccination", "status", "a_conferir"),
    ]:
        rows = (
            con.execute(sa.text(f"SELECT * FROM {table} WHERE status != :pending"), {"pending": pending})
            .mappings()
            .all()
        )
        for row in rows:
            snapshot = {
                key: row.get(key)
                for key in (
                    "status",
                    "reviewer",
                    "reviewer_id",
                    "review_note",
                    "review_guidance",
                    "reviewed_at",
                )
            }
            con.execute(
                sa.insert(audit).values(
                    id=str(uuid.uuid4()),
                    actor_id=None,
                    target_type=kind,
                    target_id=row["id"],
                    event="reaberto_para_revisao_tripla",
                    details=json.dumps(snapshot, ensure_ascii=False),
                    created_at=timestamp,
                )
            )
        reviewer = "reviewer=''" if table == "documents" else "reviewer_id=NULL"
        con.execute(
            sa.text(
                f"UPDATE {table} SET status=:pending, {reviewer}, review_note='',review_guidance='',reviewed_at=NULL WHERE status != :pending"
            ),
            {"pending": pending},
        )
    # Completed reminders are re-evaluated after their single-review records were reopened.
    con.execute(sa.text("UPDATE dose_plans SET status='ativa',record_id=NULL WHERE status='concluida'"))


def downgrade():
    raise RuntimeError("Use a verified backup instead of destructive rollback.")
