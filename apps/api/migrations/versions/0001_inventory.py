"""Immutable initial tenant-scoped inventory schema."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("low_max", sa.Integer(), nullable=False),
        sa.Column("high_min", sa.Integer(), nullable=False),
        sa.UniqueConstraint("workspace_id", "id", name="uq_category_workspace_id"),
        sa.UniqueConstraint("workspace_id", "name", name="uq_category_workspace_name"),
        sa.CheckConstraint("low_max >= 0 AND high_min > low_max", name="ck_category_thresholds"),
    )
    op.create_table(
        "variants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(128), nullable=False),
        sa.Column("name", sa.String(250), nullable=False),
        sa.Column("color", sa.String(80), nullable=False),
        sa.Column("size", sa.String(80), nullable=False),
        sa.Column("available", sa.Integer(), nullable=False),
        sa.Column("inventory_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "id", name="uq_variant_workspace_id"),
        sa.UniqueConstraint("workspace_id", "sku", name="uq_variant_workspace_sku"),
        sa.ForeignKeyConstraint(
            ["workspace_id", "category_id"],
            ["categories.workspace_id", "categories.id"],
            ondelete="CASCADE",
            name="fk_variant_category_workspace",
        ),
        sa.CheckConstraint("available >= 0", name="ck_variant_available"),
    )
    op.create_table(
        "sale_lines",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("external_order_id", sa.String(128), nullable=False),
        sa.Column("external_line_id", sa.String(128), nullable=False),
        sa.Column("sold_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("returned_quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.UniqueConstraint(
            "workspace_id",
            "source",
            "external_order_id",
            "external_line_id",
            name="uq_sale_external_line",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "variant_id"],
            ["variants.workspace_id", "variants.id"],
            ondelete="CASCADE",
            name="fk_sale_variant_workspace",
        ),
        sa.CheckConstraint(
            "quantity >= 0 AND returned_quantity >= 0 AND returned_quantity <= quantity",
            name="ck_sale_quantities",
        ),
        sa.CheckConstraint(
            "status IN ('preparing','shipping','completed','pending','cancelled','refunded')",
            name="ck_sale_status",
        ),
    )
    op.create_index("ix_sale_workspace_date", "sale_lines", ["workspace_id", "sold_at"])


def downgrade() -> None:
    op.drop_table("sale_lines")
    op.drop_table("variants")
    op.drop_table("categories")
    op.drop_table("workspaces")
