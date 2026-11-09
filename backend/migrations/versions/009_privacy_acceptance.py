"""Specific consent evidence; do not fabricate consent for legacy accounts."""

import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "privacy_acceptances",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("version", sa.Text, nullable=False),
        sa.Column("policy_hash", sa.Text, nullable=False),
        sa.Column("terms_accepted", sa.Boolean, nullable=False),
        sa.Column("health_consent", sa.Boolean, nullable=False),
        sa.Column("adult_declaration", sa.Boolean, nullable=False),
        sa.Column("accepted_at", sa.Text, nullable=False),
    )
    op.create_table(
        "privacy_requests",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("response", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("answered_at", sa.Text),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE TRIGGER acceptance_append_only BEFORE UPDATE OR DELETE ON privacy_acceptances FOR EACH ROW EXECUTE FUNCTION deny_audit_mutation()"
        )
    else:
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER acceptance_no_{action.lower()} BEFORE {action} ON privacy_acceptances BEGIN SELECT RAISE(ABORT,'acceptance is append-only'); END"
            )


def downgrade():
    raise RuntimeError("Use a verified backup instead of destructive rollback.")
