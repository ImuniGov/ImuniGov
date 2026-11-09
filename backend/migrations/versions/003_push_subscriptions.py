"""Private device subscriptions, independently revocable per session/device."""

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("session_id", sa.Text, nullable=False),
        sa.Column("endpoint", sa.Text, unique=True, nullable=False),
        sa.Column("keys", sa.JSON, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column("last_sent_at", sa.Text, nullable=False),
        sa.Column("failures", sa.Integer, nullable=False),
        sa.Column("next_attempt", sa.Integer, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
    )


def downgrade():
    raise RuntimeError("Use a verified backup instead of destructive rollback.")
