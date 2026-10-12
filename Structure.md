# دستیار انبار: architecture and contracts

Updated 2026-10-12. Implemented MVP, one modular application.

## Stack decision

React + strict TypeScript + Vite; Python FastAPI; PostgreSQL 17; synchronous
SQLAlchemy 2; explicit Alembic migrations. Python suits bounded Excel/CSV parsing
and typed HTTP routes. This is a simplicity/maintainability decision, not a claim
that Python universally uses less memory or scales better than Nest/Fastify.
No pandas, queue, Redis, microservices, ORM repository wrappers or external AI.

Python 3.12-3.14 (Docker/CI 3.13), Node 24. Runtime and check dependencies are
pinned in requirements.lock/requirements-dev.lock and package-lock.json.
Frontend state is local React state; the API owns calculations and transactions.
Production uses one origin: Caddy serves assets and proxies /api to FastAPI.

## Source map

```text
AGENTS.md                    discovers the four canonical documents
Agent.md                     scope, authority, truthful reporting
Rules.md                     mandatory design/business/security rules
Structure.md                 this architecture and API contract
Workflow.md                  run, test, deploy, restore procedures
README.md                    Persian product/run guide
LICENSE / THIRD_PARTY.md      ownership and third-party license notices
LEGAL_SOURCES.md              references for original legal notices
.env*.example                configuration templates, never real credentials
.github/workflows/checks.yml  migrations, API tests, web build, audits
apps/api/
  app/main.py                lifecycle, health, safe errors, headers
  app/config.py              validated runtime configuration
  app/auth.py                registration, login, verification, password lifecycle
  app/security.py            Argon2id, sessions, CSRF, rate limits, encryption
  app/body_limit.py          bounded request buffering before multipart parsing
  app/importing.py           normalization, encrypted previews, atomic apply
  app/import_routes.py       bounded file routes, mapping, history
  app/dashboard.py           SQL aggregation, ranking, settings, assistant, export/delete
  app/sheets.py              private per-workspace service-account reader
  app/maintenance.py         hourly expiry and audit cleanup
  app/backups.py             encrypted bounded daily backups and explicit restore
  app/grant_runtime.py       migration-owner-only runtime table grants
  app/db/models.py           persistent models and database constraints
  app/db/session.py          request session/rollback dependency
  app/domain/inventory.py    pure threshold/ranking contracts
  migrations/versions/       0001 foundation, 0002 SaaS, 0003 deletion markers
  tests/                    domain, tenant, authentication, import, restore tests
apps/web/
  src/App.tsx               authenticated shell and public legal routes
  src/Auth.tsx              login/register/verify/reset forms
  src/Dashboard.tsx         table, filters, counts, replenishment, assistant
  src/Sources.tsx           file mapping, preview/apply, manual private Sheets
  src/Settings.tsx          category thresholds and account lifecycle
  src/Legal.tsx             privacy, terms, cookies and preparation guide
  src/api.ts / ui.tsx       typed fetch, CSRF memory, accessible common feedback
  src/styles.css            semantic light/dark RTL design tokens
  public/theme-init.js      tab appearance only; no authentication storage
  public/Vazirmatn-OFL.txt   self-hosted font license
  Caddyfile / Dockerfile    static production build, TLS proxy and CSP
infra/compose.yaml          complete localhost-only development stack
infra/compose.production.yaml  private database, migration/runtime separation, TLS, backups
infra/init-runtime.sh       initial least-privilege runtime database role
```

## Persisted data and isolation

| Table | Purpose and constraints |
| --- | --- |
| workspaces | UUID, name, revision, detail/aggregate reporting mode and period |
| accounts | one owner per workspace, unique normalized email, Argon2id hash, verified flag, accepted policy version |
| categories | unique workspace/name; low_max >= 0, high_min > low_max |
| variants | unique workspace/SKU, color/size, available >= 0, actual snapshot time, replenishment state |
| sale_lines | unique workspace/source/order/line; quantity >= returned >= 0, canonical status and dated index |
| aggregate_sales | one net unit value per workspace/variant, separate reporting snapshot |
| browser_sessions | SHA-256 of opaque token, account reference, CSRF value, absolute/idle timestamps |
| action_tokens | hashed single-use verification/reset token, purpose and expiry |
| rate_buckets | HMAC of action/identity/time bucket, atomic counter, short expiry |
| import_batches | workspace/version/kind/count/time/expiry; normalized encrypted payload until apply/expiry |
| import_mappings | only selected field-to-column names, scoped by workspace/kind |
| sheet_connections | encrypted configuration, last successful applied sync |
| audit_events | workspace/action/count/time, no imported rows; 90-day retention |
| deletion_markers | hash of deleted workspace UUID and expiry, retained through backup lifecycle |

Categories and variants use composite workspace foreign keys. All shop data is
queried using the authenticated owner's workspace; client-provided workspace IDs
never select a tenant. Foreign and absent object IDs both return 404. The MVP has
one owner rather than speculative staff/RBAC features. Workspace deletion cascades
its operational data, account, sessions, tokens, mappings and connections.
Deletion markers intentionally have no workspace foreign key.

## Inventory and sales rules

- One SKU is one product/color/size combination; identifiers remain strings.
- Thresholds are per category, applied to each SKU: low <= low_max, high >= high_min,
  normal between. Default 3/5: zero and three low, four normal, five high.
- Rank low-stock, positive net-sales SKUs by units descending, stock ascending,
  then SKU. Producing SKUs stay visible but are excluded from the proposal queue.
  Low-stock zero-sale rows require review. A planned state remains a candidate.
- Count preparing/shipping/completed only; pending/cancelled/refunded excluded.
  Net units = quantity minus partial returned quantity on the original eligible line.
- Changing a line's status updates its unique key. Reimport never adds duplicates.
  Supplied available stock already reflects orders; do not subtract them again.
- Default sales window is 30 calendar days including today in Asia/Tehran; convert
  boundaries to UTC and query an exclusive upper bound. Custom windows <=366 days.
- Aggregate imports replace aggregate rows with their explicit common period;
  reports never sum them with detailed orders. Importing detail switches the active
  mode back to detail. Retained detail history may then be used again.
- Show actual inventory time separately from calculation time. Per-SKU snapshots
  older than 24 hours have a refresh warning; omitted SKUs may have older snapshots.

## Import contract

Inventory: `sku,name,category,color,size,available`.
Sales: `source,order_id,line_id,sku,sold_at,quantity,status,returned_quantity`.
Aggregate: `sku,net_units,period_start,period_end`.

Read -> explicitly map -> normalize -> validate -> encrypted preview -> confirmed
apply. CSV is UTF-8/BOM, comma separated; Excel is XLSX, not XLS. Bounds are 5 MiB,
10,000 rows, 64 columns, 25 MiB expanded XLSX, <=10 workbook tabs. Reject formulas,
macros, external links, encrypted archives, traversal and XML entities. Do not
evaluate formulas. Numeric Excel sizes are accepted; identifiers must be text to
preserve zeros. Persian/Arabic digits in counts/dates are explicitly normalized.

Choose Gregorian ISO or Jalali YYYY-MM-DD/YYYY/MM/DD; timezone is explicit.
Status mapping is explicit; missing status requires the finalized-report checkbox.
Reject duplicate inventory SKU/order-line keys, invalid returns and unknown sale
SKUs. Errors contain row/field/code only. Unselected customer columns are discarded.

Previews expire after 24 hours and capture a workspace revision under a row lock.
Apply checks revision/expiry/tenant, locks the workspace and commits atomically;
replaying an applied batch returns success without further writes. Applied payloads
are erased. Inventory replaces included SKU quantities; missing SKUs are unchanged.
Older snapshots cannot overwrite newer ones. Limits: 10,000 variants/100,000 detail
lines per shop. Changing thresholds or replenishment invalidates pending revisions.

Sheets calls the official read-only API with a validated spreadsheet ID and bounded
ranges. One dedicated service account per shop, private credentials mounted outside
Git, no arbitrary URLs/public sheets. A sync fetch produces a combined preview;
inventory and sales apply in one transaction. Connect/disconnect invalidates pending
Sheets previews. Disconnect stops fetch and removes configuration, while historical
imported data stays until account deletion. Google sharing revocation is separate.

## Implemented routes

| Method | Route | Behavior |
| --- | --- | --- |
| GET | /api/health, /api/ready, /api/meta | data-free health, database readiness, public operator metadata |
| GET | /api/templates/{inventory,sales,aggregate}.csv | empty BOM templates |
| GET | /api/v1/auth/session | anonymous/authenticated session and CSRF bootstrap |
| POST | /api/v1/auth/register, /login, /logout | account/session lifecycle |
| POST | /api/v1/auth/verify | one-use token, fresh password and policy acceptance |
| POST | /api/v1/auth/password/{request,reset,change} | generic recovery request, token reset, reauthenticated change |
| GET | /api/v1/dashboard, /variants | summary or rows; start/end/category, search/state/priority/page filters |
| GET/PATCH | /api/v1/categories, /categories/{id} | list or threshold update |
| PATCH | /api/v1/variants/{id}/replenishment | none/planned/producing |
| POST | /api/v1/imports/headers, /preview | multipart file mapping or validation/preview |
| POST | /api/v1/imports/{id}/apply | transactional idempotent apply |
| GET | /api/v1/imports/history | own recent batch metadata |
| GET | /api/v1/sheets/connection | provisioned account email, own configuration and actual sync time |
| POST/DELETE | /api/v1/sheets/connect, /sync; /connection | connect/manual preview/disconnect |
| GET | /api/v1/export.csv, /assistant, /activity | formula-safe report, computed answers, minimal recent events |
| GET/DELETE | /api/v1/account/export; /account | streamed own JSON export; password+phrase confirmed deletion |

Unsafe routes require exact Origin and X-CSRF-Token bound to the server session.
Private reads require authentication; production also requires verified email.
OpenAPI is available locally and disabled in production. See Workflow.md for
deployment configuration and release evidence. WooCommerce/CMS/billing/forecasting
and generative chat remain explicitly later scope.
