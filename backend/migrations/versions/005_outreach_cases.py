"""Keep one longitudinal ACS case per dependent, preserving previous contact records."""

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    cases = op.create_table(
        "outreach_cases",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("dependent_id", sa.Text, sa.ForeignKey("dependents.id"), unique=True, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("updated_at", sa.Text, nullable=False),
        sa.CheckConstraint("status IN ('aberta','resolvida')"),
    )
    con = op.get_bind()
    rows = (
        con.execute(
            sa.text(
                "SELECT dependent_id, MIN(updated_at) first_at, MAX(updated_at) last_at, SUM(CASE WHEN status='aberta' THEN 1 ELSE 0 END) active_count FROM pendings GROUP BY dependent_id"
            )
        )
        .mappings()
        .all()
    )
    for row in rows:
        con.execute(
            sa.insert(cases).values(
                id=row["dependent_id"],
                dependent_id=row["dependent_id"],
                status="aberta" if row["active_count"] else "resolvida",
                created_at=row["first_at"],
                updated_at=row["last_at"],
            )
        )
    op.add_column("outreach_actions", sa.Column("case_id", sa.Text, nullable=True))
    con.execute(
        sa.text(
            "UPDATE outreach_actions SET case_id=(SELECT dependent_id FROM pendings WHERE pendings.id=outreach_actions.pending_id)"
        )
    )
    with op.batch_alter_table("outreach_actions") as batch:
        batch.alter_column("case_id", existing_type=sa.Text, nullable=False)
        batch.alter_column("pending_id", existing_type=sa.Text, nullable=True)
        batch.create_foreign_key("fk_actions_case", "outreach_cases", ["case_id"], ["id"])


def downgrade():
    raise RuntimeError("Use a verified backup instead of destructive rollback.")
