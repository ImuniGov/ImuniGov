"""Consent withdrawal is explicit; do not manufacture authorizations for old accounts."""

import sqlalchemy as sa
from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "consent_controls",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Text, sa.ForeignKey("users.id"), unique=True, nullable=False),
        sa.Column("withdrawn", sa.Boolean, nullable=False),
        sa.Column("updated_at", sa.Text, nullable=False),
    )


def downgrade():
    raise RuntimeError("Use a verified backup instead of destructive rollback.")
