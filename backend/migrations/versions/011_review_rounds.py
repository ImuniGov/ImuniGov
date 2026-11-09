"""Preserve earlier votes while a new independent panel reviews unfinished work."""

import sqlalchemy as sa
from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("documents", sa.Column("review_round", sa.Integer, nullable=False, server_default="1"))
    op.add_column(
        "reviewer_profiles", sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true())
    )
    constraints = sa.inspect(op.get_bind()).get_unique_constraints("review_assignments")
    old = next(c for c in constraints if set(c["column_names"]) == {"document_id", "reviewer_id"})
    naming = {"uq": "uq_%(table_name)s_%(column_0_name)s_%(column_1_name)s"}
    with op.batch_alter_table("review_assignments", naming_convention=naming) as batch:
        batch.add_column(sa.Column("review_round", sa.Integer, nullable=False, server_default="1"))
        batch.drop_constraint(old["name"] or "uq_review_assignments_document_id_reviewer_id", type_="unique")
        batch.create_unique_constraint("uq_assignment_round", ["document_id", "reviewer_id", "review_round"])
    op.create_table(
        "review_gate",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("revision", sa.Integer, nullable=False, server_default="1"),
    )
    op.execute("INSERT INTO review_gate (id,revision) VALUES ('roster',1)")

    op.create_table(
        "reviewer_changes",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("profile_id", sa.Text, sa.ForeignKey("reviewer_profiles.id"), nullable=False),
        sa.Column("before", sa.JSON, nullable=False),
        sa.Column("after", sa.JSON, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("verification_ref", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
    )
    install_history_guard()


def install_history_guard():
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE TRIGGER reviewer_changes_append_only BEFORE UPDATE OR DELETE ON reviewer_changes FOR EACH ROW EXECUTE FUNCTION deny_audit_mutation()"
        )
    else:
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER reviewer_changes_no_{action.lower()} BEFORE {action} ON reviewer_changes BEGIN SELECT RAISE(ABORT,'profile history is append-only'); END"
            )


def downgrade():
    raise RuntimeError("Use a verified backup instead of destructive rollback.")
