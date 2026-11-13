"""Individual dose dates entered by an authenticated UBS professional."""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dose_plans",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("dependent_id", sa.Text, sa.ForeignKey("dependents.id"), nullable=False),
        sa.Column("vaccine", sa.Text, nullable=False),
        sa.Column("dose", sa.Integer, nullable=False),
        sa.Column("due_date", sa.Text, nullable=False),
        sa.Column("author_id", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("updated_at", sa.Text, nullable=False),
        sa.Column("record_id", sa.Text, sa.ForeignKey("vaccinations.id")),
        sa.CheckConstraint("status IN ('ativa','concluida','cancelada')"),
    )


def downgrade():
    raise RuntimeError("Use a verified backup instead of destructive rollback.")
