from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_category_workspace_id"),
        UniqueConstraint("workspace_id", "name", name="uq_category_workspace_name"),
        CheckConstraint("low_max >= 0 AND high_min > low_max", name="ck_category_thresholds"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    low_max: Mapped[int] = mapped_column(Integer)
    high_min: Mapped[int] = mapped_column(Integer)


class Variant(Base):
    __tablename__ = "variants"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_variant_workspace_id"),
        UniqueConstraint("workspace_id", "sku", name="uq_variant_workspace_sku"),
        ForeignKeyConstraint(
            ["workspace_id", "category_id"],
            ["categories.workspace_id", "categories.id"],
            ondelete="CASCADE",
            name="fk_variant_category_workspace",
        ),
        CheckConstraint("available >= 0", name="ck_variant_available"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    category_id: Mapped[UUID]
    sku: Mapped[str] = mapped_column(String(128))
    name: Mapped[str] = mapped_column(String(250))
    color: Mapped[str] = mapped_column(String(80))
    size: Mapped[str] = mapped_column(String(80))
    available: Mapped[int] = mapped_column(Integer)
    inventory_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SaleLine(Base):
    __tablename__ = "sale_lines"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "source",
            "external_order_id",
            "external_line_id",
            name="uq_sale_external_line",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "variant_id"],
            ["variants.workspace_id", "variants.id"],
            ondelete="CASCADE",
            name="fk_sale_variant_workspace",
        ),
        CheckConstraint(
            "quantity >= 0 AND returned_quantity >= 0 AND returned_quantity <= quantity",
            name="ck_sale_quantities",
        ),
        CheckConstraint(
            "status IN ('preparing','shipping','completed','pending','cancelled','refunded')",
            name="ck_sale_status",
        ),
        Index("ix_sale_workspace_date", "workspace_id", "sold_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    variant_id: Mapped[UUID]
    source: Mapped[str] = mapped_column(String(80))
    external_order_id: Mapped[str] = mapped_column(String(128))
    external_line_id: Mapped[str] = mapped_column(String(128))
    sold_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    quantity: Mapped[int] = mapped_column(Integer)
    returned_quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32))
