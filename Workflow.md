# دستیار انبار: implementation and release workflow

## Definition of done for this architecture task

- Four canonical documents exist and AGENTS.md points to them.
- React/TypeScript builds; FastAPI health and business-rule tests pass.
- A reviewed initial Alembic migration represents PostgreSQL tenant constraints.
- /privacy and /terms have accessible plain-text foundation notices.
- Local runtime configuration, database startup and CI commands are documented.
- Repository is public on GitHub and source is pushed after staged-file review.
- Current capabilities and launch blockers are reported honestly.

## Small implementation order

| Order | Deliverable | Acceptance evidence |
| --- | --- | --- |
| Foundation | docs, React shell, health, domain library, migration | build, pytest, migration review |
| Accounts | register/login/logout, one owner workspace, session/CSRF | expiry, revocation, bad origin, two-tenant negative tests |
| Import | CSV/XLSX inventory and detail sales, preview/apply | real synthetic templates, rollback, duplicate/status/replay cases |
| Dashboard | summaries, filters, rank, category settings | inclusive boundaries, no-sales state, RTL/keyboard checks |
| Sources | manual private Sheets sync and CSV export | authorization, range bounds, reconnect/replay, formula-safe export |
| Assistant | prepared questions explaining computed rows | same values/order as API, no external AI |
| Pilot release | operator notice, deletion/export, deploy controls | all launch gates below |

Two days is a scope target for an experienced developer using prepared auth and
deployment tooling, not a guaranteed deadline for a legally reviewed, connected,
production SaaS. Reuse infrastructure; cut decorative work before integrity or
tenant isolation. Keep implementation status in README.md.

## Per-change workflow

1. Read the four documents and inspect git status.
2. Identify one user-visible outcome and affected invariants.
3. Implement the smallest complete change; keep routes, calculations and UI apart.
4. Run checks for the touched surface; inspect relevant diff and configuration.
5. Update docs/contracts/status when behavior changes.
6. Review staged paths for secrets and real data, then commit/push.

Do not write tests that merely repeat styling declarations. Test business and
security boundaries. If a check cannot run, state the missing prerequisite.
Avoid repeated test runs after a passing unchanged result.

## Local commands

From apps/api:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.lock
.\.venv\Scripts\python -m pip install -e . --no-deps
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

From apps/web:

```powershell
npm ci
npm run build
npm run dev -- --host 127.0.0.1
```

From repository root, configure local-only secrets using .env.example:

```powershell
docker compose --env-file .env -f infra/compose.yaml up -d
```

Set DATABASE_URL in the shell before running Alembic from apps/api. Apply:
`python -m alembic upgrade head`; check: `python -m alembic check`.
Migration tests use a dedicated empty test database. Never downgrade a production
database as a routine check. CI creates a disposable PostgreSQL database.

## Verification requirements

Domain: low=3/high=5 yields low for 0 and 3, normal for 4, high for 5; invalid
thresholds/counts fail; ties sort deterministically; no-sales low SKUs need review.
Sales ingestion: preparing -> shipping -> completed counts once; cancellation,
partial return and repeated import update rather than inflate totals. Aggregate
mode must not combine with detailed mode for overlapping periods.
Persistence: migration upgrades an empty PostgreSQL database; cross-workspace
category and variant references fail; SKU is unique only within a workspace.
Security: every new tenant endpoint gets two-workspace tests before release.
UI: build, visible labels, keyboard-only use, Escape/focus for any panels, RTL,
375/768/1440px, dark/light contrast, 200% zoom and reduced-motion.
Audits: npm audit and pip-audit for locked dependencies; repeat only after changes.
Do not equate a vulnerability scan with proof of zero vulnerabilities.

## Launch gate (required before customer data)

- Implement and verify auth, membership, CSRF, tenant filtering and session limits.
- Implement import preview/apply validation, idempotency and bounded file handling.
- Verify frontend and backend operate with TLS under the same origin.
- Configure production host allowlist, secrets, private database, least-privilege
  runtime DB user, trusted proxy hops, upload/rate limits and static security headers.
- Set actual operator identity, support/privacy contact, operating jurisdiction,
  hosting region, subprocessors and retention; review appropriate local requirements.
- Publish accurate privacy/terms/cookie notices. Implement export, deletion,
  integration disconnect, log redaction and backup retention before claiming them.
- Test backup restore and deletion lifecycle, including backup expiry.
- Review dependency advisories, cross-tenant tests, logging and staged secrets.
- Show source and freshness of every summary; test with one willing pilot shop.
- Confirm release evidence and residual limitations; no 'secure forever' claim.

## CI and deployment

CI runs Python tests/lint, real PostgreSQL migration/tenant-constraint checks,
TypeScript production build and dependency audits. Keep permissions read-only.
No repository secrets are necessary to test synthetic data.

Deployment is a separate authorized task. Do not silently provision paid services,
purchase a domain, activate telemetry, or collect actual customer data from this
architecture task. Public GitHub publishing was explicitly authorized.
