from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DeletionMarker(Base):
    __tablename__ = "deletion_markers"
    workspace_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint("sales_mode IN ('detail','aggregate')", name="ck_workspace_sales_mode"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    data_revision: Mapped[int] = mapped_column(default=0, server_default="0")
    sales_mode: Mapped[str] = mapped_column(String(16), default="detail", server_default="detail")
    aggregate_start: Mapped[date | None] = mapped_column(Date)
    aggregate_end: Mapped[date | None] = mapped_column(Date)


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
        CheckConstraint(
            "replenishment IN ('none','planned','producing')", name="ck_variant_replenishment"
        ),
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
    replenishment: Mapped[str] = mapped_column(String(16), default="none", server_default="none")


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


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        unique=True,
    )
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    policy_version: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BrowserSession(Base):
    __tablename__ = "browser_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[UUID | None] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    csrf_token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ActionToken(Base):
    __tablename__ = "action_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    purpose: Mapped[str] = mapped_column(String(16))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RateBucket(Base):
    __tablename__ = "rate_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ImportBatch(Base):
    __tablename__ = "import_batches"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(16))
    revision: Mapped[int] = mapped_column(Integer)
    payload: Mapped[str | None] = mapped_column(Text)
    row_count: Mapped[int] = mapped_column(Integer)
    applied: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ImportMapping(Base):
    __tablename__ = "import_mappings"
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    kind: Mapped[str] = mapped_column(String(16), primary_key=True)
    mapping: Mapped[dict] = mapped_column(JSONB)


class AggregateSale(Base):
    __tablename__ = "aggregate_sales"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "variant_id"],
            ["variants.workspace_id", "variants.id"],
            ondelete="CASCADE",
            name="fk_aggregate_variant_workspace",
        ),
        CheckConstraint("net_units >= 0", name="ck_aggregate_units"),
    )
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    variant_id: Mapped[UUID] = mapped_column(primary_key=True)
    net_units: Mapped[int] = mapped_column(Integer)


class SheetConnection(Base):
    __tablename__ = "sheet_connections"
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    payload: Mapped[str] = mapped_column(Text)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(64))
    row_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
