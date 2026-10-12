"""Retain pseudonymous deletion markers across backup restore."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "deletion_markers",
        sa.Column("workspace_hash", sa.String(64), primary_key=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_deletion_markers_expires_at", "deletion_markers", ["expires_at"])


def downgrade():
    op.drop_table("deletion_markers")
