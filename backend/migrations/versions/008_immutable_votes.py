"""Votes are append-only; corrections require a new evidence/review, never editing history."""

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE TRIGGER votes_append_only BEFORE UPDATE OR DELETE ON review_votes FOR EACH ROW EXECUTE FUNCTION deny_audit_mutation()"
        )
    else:
        op.execute(
            "CREATE TRIGGER votes_no_update BEFORE UPDATE ON review_votes BEGIN SELECT RAISE(ABORT,'votes are append-only'); END"
        )
        op.execute(
            "CREATE TRIGGER votes_no_delete BEFORE DELETE ON review_votes BEGIN SELECT RAISE(ABORT,'votes are append-only'); END"
        )


def downgrade():
    raise RuntimeError("Use a verified backup instead of destructive rollback.")
