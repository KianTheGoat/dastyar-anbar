# دستیار انبار: agent contract

Status: implemented MVP; production activation requires operator configuration.
Updated: 2026-10-12. Product language: Persian (fa-IR), direction: RTL.

## Read order and authority

1. Current human instructions.
2. This document: scope, responsibilities, truthful reporting.
3. `Rules.md`: mandatory business, design, security, privacy rules.
4. `Structure.md`: architecture, schemas, API contracts.
5. `Workflow.md`: implementation sequence and release evidence.

Resolve conflicts using this order. Record architectural changes in Structure.md
and update affected tests and Workflow.md in the same change. Ask only when a
missing decision affects authorization, data loss, or a materially different product.
Routine reversible implementation decisions belong to the agent.

## Product promise

A small SaaS for online shops with a warehouse. Import inventory and sales from
Excel, CSV, or an authorized Google Sheet. Show low, normal, and excess inventory
for each SKU (one product/color/size combination). Prioritize low-stock SKUs by
net units sold. Category settings control thresholds, not per-product overrides.

The core question is: «کدام رنگ و سایز پرفروش را زودتر دوباره تأمین کنیم؟»

## Current requested delivery

Implement the complete agreed MVP with React/FastAPI/PostgreSQL, public GitHub
source, the four governing documents, authentication, import/export, dashboard,
private Sheets adapter, category settings, assistant, account lifecycle and honest
legal notices. The source implements these modules. Hosted production, real email
delivery and live Google access require domain/provider credentials supplied by
the operator; synthetic integration tests are not evidence of live connections.

## MVP boundary

Include account/session isolation, category thresholds, inventory/sales import,
preview and validation, dashboard filters, CSV export, manual Google Sheet sync,
last-update indicators, and a deterministic assistant in the bottom-left corner.
The assistant explains computed results and offers prepared questions.

Later: WooCommerce plugin, CMS integration API, website-builder connectors,
production quantity forecasting, lead-time planning, billing automation, and LLM
chat. Accounting integration is outside the agreed scope.

Do not add microservices, Redis, Celery, Kubernetes, event buses, vector databases,
complex RBAC, an enterprise design system, or a generic import framework without
a demonstrated need and a human-approved scope change.

## Working behavior

- Inspect the existing checkout and preserve unrelated changes.
- Prefer one small coherent change over scaffolding speculative abstractions.
- Keep business calculations in Python; React displays the API results.
- Use feature folders only when a feature actually exists.
- Never create empty modules, dead buttons, fabricated testimonials, fake sync
  times, or hidden sample data. Label demonstrations explicitly.
- Do not spawn agents unless the human or an applicable instruction authorizes it.
- Use synthetic fixtures. Never commit real shop data, tokens, credential files,
  customer names, phone numbers, or addresses to this public repository.
- Never log imported rows or include them in exception messages.
- Do not send shop data to third-party AI services.
- Keep dependencies small, explicitly declared, and locked.
- Report what was implemented, which checks passed, which could not run, and
  which launch requirements remain. Never guarantee zero security defects.

## Meaningful checks

Run the relevant commands in Workflow.md. For domain changes, test inclusive
thresholds, ties, zero sales, and invalid quantities. For persistent APIs, test
cross-workspace access and import replay. For frontend changes, build, check
keyboard navigation, RTL, small screens, and reduced motion. Test claims must
refer to checks actually executed; CI configuration alone is not passing CI.

## Design provenance

The requested skills are emil-design-eng, apple-design, design-taste-frontend,
and ui-ux-pro-max. Their applicable guidance is synthesized in Rules.md so another
LLM does not need the original local files. design-taste-frontend explicitly
excludes dashboards; its marketing patterns are not dashboard requirements.
Accessibility, Persian legibility, and task completion take precedence over style.

## Publishing

The user authorized a new public GitHub repository. Publish generated project
source and documentation directly through GitHub/git, not Composio. Use an
allowlist of staged files, inspect the staged diff, and exclude local environment
files and screenshots. No automatic production deployment or service purchase is
included. Do not attach a PR unless one is actually created.
