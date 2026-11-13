"""Randomly assigned review responsibility and an explicit next step for the family."""

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("documents", sa.Column("review_guidance", sa.Text, nullable=False, server_default=""))
    op.add_column("vaccinations", sa.Column("review_guidance", sa.Text, nullable=False, server_default=""))
    op.create_table(
        "review_assignments",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("document_id", sa.Text, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("reviewer_id", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="ativa"),
        sa.Column("profile_snapshot", sa.JSON, nullable=False),
        sa.UniqueConstraint("document_id", "reviewer_id"),
    )


def downgrade():
    raise RuntimeError("Use a verified backup instead of destructive rollback.")
