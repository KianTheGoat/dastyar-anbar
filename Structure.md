# دستیار انبار: architecture

## Decision

React + TypeScript + Vite for the frontend; Python + FastAPI for the backend;
PostgreSQL for persistence; SQLAlchemy 2 and Alembic for schema management.
The foundation uses native CSS semantic tokens and native accessible controls.

FastAPI fits a small typed HTTP API and Python file-processing tools. This is a
maintainability/scope decision, not a benchmark proving that Python always uses
less memory or scales better than Nest. Nest with Fastify is also viable.
Use one modular application, synchronous SQLAlchemy sessions, one bounded import
at a time per workspace initially, and SQL aggregation. Add workers only after
measuring a real bottleneck. Avoid pandas for small bounded imports.

Runtime: Python 3.12-3.14, Node 24 LTS, PostgreSQL 17. Lock package versions through
package-lock.json and requirements.lock (runtime), requirements-dev.lock (checks).
Production uses a single origin with
`/api` proxied to FastAPI and other routes served from the frontend build.

## Files

```text
AGENTS.md                     automatic agent discovery
Agent.md                      scope and agent behavior
Structure.md                  architecture and contracts
Rules.md                      business/design/security/privacy invariants
Workflow.md                   development and release gates
README.md                     current capabilities and local commands
.env.example                  safe configuration examples
.github/workflows/checks.yml   required build/test checks
apps/
  api/
    pyproject.toml
    requirements.lock
    alembic.ini
    migrations/               reviewed schema changes
    app/
      main.py                 health API and security middleware
      config.py               environment validation
      domain/inventory.py     pure classification and ranking
      db/models.py            tenant-scoped persistent schema
    tests/
  web/
    package.json
    package-lock.json
    index.html                fa-IR, RTL, viewport
    vite.config.ts            local /api proxy
    src/
      main.tsx
      App.tsx                 initial shell, privacy and terms routes
      styles.css              semantic design tokens
infra/compose.yaml            local PostgreSQL, optional API profile
```

Future modules belong beside existing code when implemented: auth, imports,
sheets, dashboard, categories. Keep routers thin; validation uses Pydantic;
business services own transactions and calculations. Do not introduce a repository
wrapper per table. Frontend feature code consumes `/api/v1` and shared UI tokens.
Use local React state first. Server state can use a small query cache once needed.

## Database model

Implemented initial schema:

| Entity | Fields / constraints |
| --- | --- |
| workspace | UUID id, name, timestamps |
| category | workspace_id, id, name, low_max, high_min; low_max >= 0 and high_min > low_max |
| variant | workspace_id, id, category_id, SKU, name, color, size, available >= 0, inventory_updated_at |
| sale_line | workspace_id, id, variant_id, source, external_order_id, external_line_id, sold_at, quantity, returned_quantity, status |

SKU uniqueness is `(workspace_id, sku)`. External order-line uniqueness is
`(workspace_id, source, external_order_id, external_line_id)`. Category and variant
references use composite workspace foreign keys, preventing cross-shop links.
Every tenant-owned table includes workspace_id. Deleting a workspace cascades
through its data; only the future confirmed account-deletion service may invoke it.

Before persistent customer endpoints ship, add account, membership (one owner role
initially), hashed opaque session, import_batch, and sheet_connection migrations.
Do not activate routes against real data before auth and tenant tests pass.
Secrets for Sheets are encrypted with a key outside the database and source tree.

## Business rules

- Category thresholds apply separately to every variant, not summed product stock.
- Low: available <= low_max. High: available >= high_min. Normal: values between.
- Example shoes: low_max=3, high_min=5. Trousers 2/4 is an editable example.
- One inventory category per variant, regardless of website merchandising tags.
- Ranking includes only low-stock variants with positive net sales: descending
  net units, ascending available units, then SKU for a deterministic tie-break.
- Low stock with zero sales stays visible as `needs_review`, outside the ranked list.
- Default window: last 30 calendar days in Asia/Tehran, including today. Convert
  boundaries to UTC and query `[start, end)`; never guess the source date format.
- Eligible statuses: preparing, shipping, completed. Source labels map explicitly
  to these canonical values. Pending, cancelled, and fully refunded are excluded.
- Net sold per eligible line = quantity - returned_quantity, bounded at zero;
  returns cannot exceed quantity. Reconcile partial returns using the original line.
- Updating one order line changes its row; a status transition never inserts a
  second sale. A sale already deducted in the supplied available inventory must
  not be deducted again.

## Import contract (MVP implementation task)

Inventory: `sku,name,category,color,size,available`. Sales detail:
`source,order_id,line_id,sku,sold_at,quantity,status,returned_quantity`.
Aggregated sales alternative: `sku,net_units,period_start,period_end`; store as a
separate replaceable reporting snapshot and NEVER add it to detailed orders for
the same reporting scope. UI must show which mode and period are active.

Keep identifiers as strings. Accept UTF-8/UTF-8-BOM CSV and `.xlsx`, not `.xls`,
macros, or arbitrary archives. Initial bounds: 5 MiB uploaded, 10,000 rows per
import, bounded expanded XLSX size of 25 MiB. Reject formulas and encrypted files.
Headers can be mapped through a saved small per-workspace field mapping.
Reject duplicate SKU rows in inventory snapshots and duplicate order-line keys in
one import; return row numbers and field names, not full rows.

Flow: parse -> normalize -> validate -> preview -> explicit apply. Use database
transactions and a unique batch token for retry protection. Inventory snapshots
replace the provided SKU quantities, not increment them. Omitted SKUs remain
unchanged and the preview says so. Unknown sale SKUs block apply. Stale inventory
snapshots cannot overwrite a newer snapshot silently. Partial imports never commit.
Raw files are temporary and discarded after processing; durable import batches
contain counts, mode, period, timestamps, and minimal error metadata.

Google Sheets uses the same two tables and validation path. Manual sync only.
For the pilot, an operator-managed service account reads only spreadsheets
explicitly shared with it; the user supplies spreadsheet ID and tab ranges.
Prefer one pilot account per shop where practical. No public-sheet requirement.
No arbitrary URL fetch: call the official Sheets API using a validated ID.
Credential provisioning is a documented operator prerequisite, not a claim of
zero-setup OAuth. Self-service OAuth with minimal file access is a later option.
Google sync must show requested scopes/access, preview data, and allow disconnect.

## Planned API, not current implemented endpoints

```text
POST   /api/v1/auth/register, /login, /logout
GET    /api/v1/auth/session
GET    /api/v1/dashboard?from=...&to=...&category_id=...
GET    /api/v1/variants?cursor=...&limit=50
GET    /api/v1/categories
PATCH  /api/v1/categories/{id}
POST   /api/v1/imports/preview
POST   /api/v1/imports/{id}/apply
GET    /api/v1/export.csv
POST   /api/v1/sheets/connect, /sync
DELETE /api/v1/sheets/connection
DELETE /api/v1/account                 confirmed deletion
```

`GET /api/health` is currently implemented. No tenant endpoint is publicly exposed
by the foundation. Workspace comes from authenticated membership, never trusted
from a request body or query string. Foreign or missing IDs both return 404.
Errors use stable codes and field paths. API responses carry generated_at and
data_updated_at separately; a calculation time is not a synchronization time.

## Deployment boundary

One API process and one database suffice for a pilot; static frontend served by a
TLS reverse proxy. Database is private. Local compose publishes PostgreSQL only on
127.0.0.1. The API validates production host settings and disables public API docs.
The reverse proxy supplies TLS, request-size limits, security headers for static
assets, and correct SPA fallback for /privacy and /terms. Do not use Vite's dev
server as a public deployment. Backups, retention, restore rehearsal and monitoring
are release tasks, not inferred from the presence of compose.yaml.

`apps/api/Dockerfile` provides a non-root Python runtime for machines where native
Python extensions are unavailable or blocked. Local compose's optional `api`
profile exposes only the data-free foundation API. It does not provision accounts
or connect the database automatically.

## Decision sources

- https://fastapi.tiangolo.com/features/
- https://docs.nestjs.com/techniques/performance
- https://docs.sqlalchemy.org/en/20/
- https://alembic.sqlalchemy.org/en/latest/
- https://developers.google.com/workspace/sheets/api/guides/values
