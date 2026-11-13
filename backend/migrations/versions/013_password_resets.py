"""Store expiring, single-use password recovery codes."""

import sqlalchemy as sa
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "password_resets",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "user_id", sa.Text, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
        ),
        sa.Column("expires", sa.Integer, nullable=False),
    )


def downgrade():
    op.drop_table("password_resets")
