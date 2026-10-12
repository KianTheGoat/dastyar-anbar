"""Accounts, isolated sessions, imports and private integrations."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspaces", sa.Column("data_revision", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "workspaces",
        sa.Column("sales_mode", sa.String(16), nullable=False, server_default="detail"),
    )
    op.add_column("workspaces", sa.Column("aggregate_start", sa.Date()))
    op.add_column("workspaces", sa.Column("aggregate_end", sa.Date()))
    op.create_check_constraint(
        "ck_workspace_sales_mode", "workspaces", "sales_mode IN ('detail','aggregate')"
    )
    op.add_column(
        "variants", sa.Column("replenishment", sa.String(16), nullable=False, server_default="none")
    )
    op.create_check_constraint(
        "ck_variant_replenishment", "variants", "replenishment IN ('none','planned','producing')"
    )
    statements = """
    CREATE TABLE accounts (
      id UUID PRIMARY KEY,
      workspace_id UUID NOT NULL UNIQUE REFERENCES workspaces(id) ON DELETE CASCADE,
      email VARCHAR(254) NOT NULL UNIQUE, password_hash VARCHAR(512) NOT NULL,
      verified BOOLEAN NOT NULL, policy_version VARCHAR(32) NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE browser_sessions (
      token_hash VARCHAR(64) PRIMARY KEY, account_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
      csrf_token VARCHAR(64) NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
      last_seen TIMESTAMPTZ NOT NULL
    );
    CREATE INDEX ix_browser_sessions_expires_at ON browser_sessions(expires_at);
    CREATE TABLE action_tokens (
      token_hash VARCHAR(64) PRIMARY KEY,
      account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
      purpose VARCHAR(16) NOT NULL, expires_at TIMESTAMPTZ NOT NULL
    );
    CREATE INDEX ix_action_tokens_expires_at ON action_tokens(expires_at);
    CREATE TABLE rate_buckets (
      key VARCHAR(64) PRIMARY KEY, count INTEGER NOT NULL, expires_at TIMESTAMPTZ NOT NULL
    );
    CREATE INDEX ix_rate_buckets_expires_at ON rate_buckets(expires_at);
    CREATE TABLE import_batches (
      id UUID PRIMARY KEY, workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
      kind VARCHAR(16) NOT NULL, revision INTEGER NOT NULL, payload TEXT,
      row_count INTEGER NOT NULL, applied BOOLEAN NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(), expires_at TIMESTAMPTZ NOT NULL
    );
    CREATE INDEX ix_import_batches_expires_at ON import_batches(expires_at);
    CREATE TABLE import_mappings (
      workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
      kind VARCHAR(16), mapping JSONB NOT NULL, PRIMARY KEY(workspace_id,kind)
    );
    CREATE TABLE aggregate_sales (
      workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE, variant_id UUID,
      net_units INTEGER NOT NULL, PRIMARY KEY(workspace_id,variant_id),
      CONSTRAINT fk_aggregate_variant_workspace FOREIGN KEY(workspace_id,variant_id)
        REFERENCES variants(workspace_id,id) ON DELETE CASCADE,
      CONSTRAINT ck_aggregate_units CHECK(net_units >= 0)
    );
    CREATE TABLE sheet_connections (
      workspace_id UUID PRIMARY KEY REFERENCES workspaces(id) ON DELETE CASCADE,
      payload TEXT NOT NULL, last_synced_at TIMESTAMPTZ
    );
    CREATE TABLE audit_events (
      id UUID PRIMARY KEY, workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
      action VARCHAR(64) NOT NULL, row_count INTEGER, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE INDEX ix_audit_events_created_at ON audit_events(created_at)
    """
    for statement in statements.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    for name in [
        "audit_events",
        "sheet_connections",
        "aggregate_sales",
        "import_mappings",
        "import_batches",
        "rate_buckets",
        "action_tokens",
        "browser_sessions",
        "accounts",
    ]:
        op.drop_table(name)
    op.drop_constraint("ck_variant_replenishment", "variants")
    op.drop_column("variants", "replenishment")
    op.drop_constraint("ck_workspace_sales_mode", "workspaces")
    for name in ["aggregate_end", "aggregate_start", "sales_mode", "data_revision"]:
        op.drop_column("workspaces", name)
