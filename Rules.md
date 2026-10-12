# دستیار انبار: mandatory rules

## Product simplicity

Use Persian labels and short task-specific explanations. Three product views:
inventory/priorities, data sources/import/export, category settings. Legal notices
are simple text routes linked from every footer, not a marketing-site project.
Every visible button performs an implemented action or is explicitly unavailable.
Do not claim a connector, automatic forecast, or generative chatbot exists before
it works. The initial assistant uses computed data and prepared questions only.

## Code conventions

TypeScript strict mode, explicit boundary types, functional React components,
and local state first. Python uses typed domain functions and Ruff formatting.
UTF-8 and LF in source, 2-space web/config indentation and 4-space Python.
Keep each component responsible for one interaction; extract only when reuse or
readability warrants it. Do not duplicate backend business calculations in React.
Environment-specific credentials never belong in source or dependency locks.

## Design system

Design read: a calm Persian RTL operational dashboard for small online shops.
DESIGN_VARIANCE=3, MOTION_INTENSITY=2, VISUAL_DENSITY=7. Low visual complexity,
compact readable data, restrained feedback. The skill search matched Minimalism
& Swiss Style; its marketing hero and GSAP suggestions do not fit this product.

Use native CSS variables and HTML controls initially. Add Radix primitives only
for a real dialog/popover need; use their real package, never imitate semantics.
One component foundation and one icon family (Phosphor, if icons are needed).
No decorative icon package, chart library, Tailwind, or animation library is
required by the foundation. No emoji controls, generic glass panels, gradients,
oversized marketing headings, scroll reveals, confetti, or decorative charts.

| Token | Light | Dark |
| --- | --- | --- |
| canvas | #FAF8F5 | #181411 |
| surface | #FFFCF8 | #231D18 |
| text | #30251F | #F7EEE4 |
| muted text | #736157 | #C5B4A6 |
| border | #E6DDD4 | #493B31 |
| control border | #9A8171 | #947F6E |
| primary/action | #9A431C | #EFB98F |
| on primary | #FFFFFF | #301F15 |
| low text / background | #9D3626 / #FFF0EB | #F0A58E / #40261F |
| normal text / background | #496143 / #EDF3E8 | #BBCCAA / #26301F |
| excess text / background | #86610C / #FAF0D9 | #E8C177 / #3C3019 |

Action accent is warm terracotta; semantic inventory colors have distinct roles.
The human requested warm colors and Apple-inspired whitespace on 2026-10-12.
Center a single login card without a promotional side column or field-helper clutter.
Start in light mode unless the user selected dark mode for this tab.
Light-mode summary cards have a visible warm border and a restrained two-layer
shadow (2px/4px at 3.5%, 8px/24px at 6.5%) for separation from the canvas.
Keep dark-mode summary surfaces unchanged when refining light-only elevation.
Never convey a state by color alone: use text such as «کمبود» or «موجودی زیاد».
All token pairs must meet 4.5:1 for ordinary text and 3:1 for meaningful controls.

Spacing scale: 4/8/12/16/24/32/48px expressed as rem. Radius: 12px controls,
20px surfaces. Content max-width 1280px, gutters 16px mobile and 32px desktop.
Body 16px / line-height 1.7, metadata >=14px, headings 24-32px. Persian joined
letters use letter-spacing:0; do not apply negative Latin tracking to Persian.
Use system fonts initially; production may self-host licensed Vazirmatn with its
license included, font-display:swap. Never fetch fonts from a third-party CDN.
Numbers use tabular-nums. SKU/code uses bdi or an isolated LTR region.

RTL uses logical CSS properties; navigation order and reading order match.
Breakpoints 375/768/1024/1440px. Main page must fit at 375px and at 200% zoom;
large tables may scroll inside a labeled region, never the entire page.
On mobile retain name, variant, available, sales, and priority; move secondary
details into an accessible disclosure. Assistant anchors at bottom-left with
safe-area clearance, has a close button, and never covers the focused control.

## Interaction craft

Apply Emil's immediate feedback and Apple's predictability, agency, restraint,
and spatial consistency. Never block input while an animation finishes.
Regular buttons give pointer-down feedback, but actions commit on click/release.
Frequent keyboard navigation, sorting, and filtering change immediately.
CSS transitions only for feedback: press 100ms, occasional panel enter 180ms,
exit 120ms; easing cubic-bezier(0.23,1,0.32,1). Enumerate properties; never
transition:all. Only transform/opacity for movement. No scale(0) entrances.
Springs/gestures are not required; add only if a real interaction earns them.
The chat trigger is a 56px circle with a chat icon and accessible name, no visible
caption. Its panel opens above the trigger with 200ms opacity/transform feedback;
keyboard interaction is immediate. Initial login entry is 240ms and chart bar entry
260ms; reduced motion disables both. No delayed input or artificial loading timers.
Use source-backed daily line/area, inventory donut and top-seller bars. All charts
share table filters and have readable numbers and accessible data alternatives.
No imported sales means unknown; aggregate sales never invent a daily trend.
Honor reduced motion, reduced transparency and more contrast; solid surfaces
remain readable without blur. Hover effects only on devices supporting hover.

Use native buttons/links/inputs with visible labels. Target 44x44 CSS px for
touchable controls and 8px spacing. Maintain visible focus, skip link, semantic
landmarks, meaningful headings and table headers. A modal traps focus, closes with
Escape, and restores focus. Connect errors to fields and focus an error summary.
Every data view implements loading, empty, error, stale, and success states.
Display real last-sync times. A successful preview is not a successful import.

## Business invariants

Thresholds are category-level; low_max >=0; high_min > low_max. Inclusive boundaries.
One SKU equals one product/color/size combination. Each shop owns its SKU namespace.
Counts are finite nonnegative integers, never booleans, NaN, fractional values or
silently truncated numbers. Returned units cannot exceed original quantity.
Missing data is unknown, not zero. Persian/Arabic digits can be normalized with an
explicit parser; preserve identifiers and leading zeros. Dates require explicit
calendar/timezone selection; ambiguous date strings are validation errors.
Preparing/shipping/completed sales count once per order line. Replay never adds
duplicate sales. Inventory is the supplied available snapshot, not recalculated
by subtracting the same orders again. Aggregates never mix with detailed sales.
Recommendations are priorities, not promised future sales or exact production
quantities. A low-stock variant with no sales has an explicit review state.

## Security rules and launch gates

Public source is not public shop data. Keep secrets in runtime environment or
managed secret storage. `.env`, uploads, database dumps, exports and logs stay out
of Git. Validate configuration and fail closed for unsafe production settings.
No defaults for production passwords or encryption keys.

Keep these implemented boundaries intact:

- Hash passwords with Argon2id using a maintained library. Allow password managers
  and paste. Add rate limits to login/reset/register; responses avoid enumeration.
- Use high-entropy opaque server-side sessions, hash session tokens at rest,
  expire and revoke them on logout, and rotate after login. No auth token in
  localStorage. Production cookie: __Host-session, Secure, HttpOnly, SameSite=Lax,
  Path=/, no Domain. Document a separate localhost development cookie.
- Protect every unsafe request (including login/logout and imports) using an
  Origin allowlist and a session-bound CSRF token. SameSite alone is insufficient.
- Derive workspace from authenticated membership. Apply tenant filter to every
  query, export, preview, apply, and Google connection; no caller-chosen tenant.
- Composite foreign keys and unique constraints enforce cross-tenant consistency.
  Database constraints do not replace route authorization. Test with two shops.
- Parameterized SQL/SQLAlchemy only. React text escaping; no unsanitized HTML.
- Same-origin production; explicit development CORS origins with credentials.
  No wildcard credentialed CORS. TLS at the proxy; HSTS after TLS is verified.
- Static frontend and API both get CSP, frame-ancestors 'none', nosniff,
  Referrer-Policy:no-referrer, and restricted Permissions-Policy. Adapt CSP for
  Vite HMR only locally. Never disable certificate validation.
- Bound uploads, rows, expanded zip size, sheets range, query page size and import
  concurrency. Reject path traversal, formulas, external XLSX links and macros.
  CSV export neutralizes formula prefixes =,+,-,@,tab,CR after whitespace handling.
- No arbitrary remote URLs for Sheets: official Google API and validated IDs only.
- Errors contain codes/row numbers and request IDs, not secrets, customer rows,
  SQL, filesystem paths, or stack traces. Production docs/debugging are disabled.
- Audit import/apply, settings changes and deletion using minimal metadata. Avoid
  session tokens and row values in access, application and exception logs.
- Run dependency audits and a staged-secret review before public publication.
  No known exploitable high/critical finding may be waived silently.

The MVP exposes tenant APIs only after authentication. Production additionally
requires verified email. Verification establishes a fresh owner password and
records policy acceptance, preventing takeover of an unverified precreated account.
Rate counters commit even on rejected authentication. Password reset/change revokes
all prior sessions. Single-use hashed email tokens expire after 30 minutes.

## Privacy and cookies

Import only product/SKU, variant attributes, quantities, dates and order-line
identifiers. Customer names, addresses, emails, phone numbers and payment details
are unnecessary and must be rejected/discarded rather than stored.
No third-party analytics, advertising pixels, session replay, remote fonts, or
AI transfer by default. Deterministic assistant consumes the same tenant-scoped
summary as the dashboard and sends no data to an external model.

Routes /privacy and /terms are simple readable notices linked in the footer.
Privacy text must describe actual data, purpose, storage location, subprocessors,
retention, deletion/export process, contact, cookies and policy changes.
Do not fabricate operator details or claim GDPR/other legal certification.
The product is «دستیار انبار» within «دستیار»; copyright belongs to its owner.
Original notices describe this implementation; other sites are references only.
Production startup requires contact, country, hosting region and provider disclosure.

Public legal routes do not bootstrap sessions. Private pages create an anonymous
30-minute session; authenticated sessions last at most seven days with a 12-hour
idle expiry. Appearance selected by the user persists only in tab sessionStorage.
The session cookie is strictly necessary. Explain it in a cookie notice; do not
show a misleading 'accept all' banner when only necessary cookies exist.
Optional cookies, if ever introduced, remain off until valid granular consent;
reject is as easy as accept, withdrawal is available, and consent is versioned.
Assess actual applicable law; an essential-cookie exemption is jurisdiction-specific.

Implemented retention: raw imports discarded after
processing; temporary previews expire within 24h; operational rows remain until
owner deletion; audit metadata 90 days; backups rotate out within 30 days.
Expired previews and minimal audit metadata are cleaned hourly. Daily encrypted
backups are retained for the configured 1-365 days (default 30). A pseudonymous
deletion marker survives for backup retention plus one day; restore reapplies
deletions and revokes all sessions/tokens. Keep the encryption key privately backed
up; losing it makes previews/connections/backups unreadable. Run grants again after
restore. Backup deletion is not falsely described as instantaneous.
Users must be able to export and request/delete their workspace. Google disconnect
removes stored access and stops sync; revocation does not imply historical deletion.

## Sources and scope

- Emil Kowalski: https://animations.dev/ (restrained meaningful motion).
- Apple: https://developer.apple.com/design/human-interface-guidelines/
- WCAG: https://www.w3.org/TR/WCAG22/
- OWASP: https://cheatsheetseries.owasp.org/
- Cookie reference (UK, not universal law):
  https://ico.org.uk/for-organisations/advice-for-small-organisations/privacy-notices-and-cookies/cookies-and-privacy-notices-in-detail/
- design-taste-frontend applies to visual consistency here, not its landing hero,
  image generation, carousel, marketing density or mandatory cinematic patterns.
- ui-ux-pro-max matches guide choices; database recommendations are not authority
  for inaccessible colors, Persian typography or unnecessary packages.
