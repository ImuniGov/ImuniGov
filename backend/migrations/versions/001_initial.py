"""Initial schema. Future revisions alter this schema, never edit this revision."""

from alembic import op

from backend.migrations.schema_v1 import metadata

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    metadata.create_all(op.get_bind())


def downgrade():
    raise RuntimeError("Destructive rollback is disabled. Restore a verified backup instead.")
