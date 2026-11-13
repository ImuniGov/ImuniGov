"""A reported conflict after voting pauses the case for documented administrative handling."""

import sqlalchemy as sa
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def install_guards():
    for table in ("review_incidents", "review_resolutions"):
        if op.get_bind().dialect.name == "postgresql":
            op.execute(
                f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION deny_audit_mutation()"
            )
        else:
            for action in ("UPDATE", "DELETE"):
                op.execute(
                    f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'incident history is append-only'); END"
                )


def upgrade():
    op.add_column(
        "documents", sa.Column("review_hold", sa.Boolean, nullable=False, server_default=sa.false())
    )
    op.create_table(
        "review_incidents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("document_id", sa.Text, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column(
            "assignment_id", sa.Text, sa.ForeignKey("review_assignments.id"), unique=True, nullable=False
        ),
        sa.Column("reporter_id", sa.Text, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_round", sa.Integer, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("origin", sa.Text, nullable=False),
        sa.Column("administrative_ref", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
    )
    op.create_table(
        "review_resolutions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("incident_id", sa.Text, sa.ForeignKey("review_incidents.id"), unique=True, nullable=False),
        sa.Column("administrative_ref", sa.Text, nullable=False),
        sa.Column("note", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
    )
    install_guards()


def downgrade():
    raise RuntimeError("Use a verified backup instead of destructive rollback.")
