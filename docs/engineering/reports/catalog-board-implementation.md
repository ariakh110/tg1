# Catalog board / amount-only editor — implementation evidence

Date: 2026-11-06. Workflow: `catalog-board-price-only`. OpenSpec:
`improve-catalog-board-price-only`. Owner explicitly approved the concrete design
and execution. Local changes only; no deployment, production writes or sends.

## Implemented

- `/products` groups every family by factory, family, form, grade and price basis;
  numeric dimensions sort numerically. Family-specific columns distinguish two
  angle legs, channel nominal size, sheet/coil, pipe/profile/billet/beam and custom
  families. A price-per-ton is never compared to price-per-kg for selecting a row.
- Desktop semantic tables and compact mobile rows retain RTL/IRANYekan, filters,
  links, out-of-stock reservation intent, actual seller/condition/unit/date, and
  existing VAT behavior (off ×0.9, on ×1). Unknown facts are dashes, not inventions.
  Misleading cross-unit average badges were removed, not replaced with fake history.
- Read-only `dynamic_specs` now accompanies public product-list rows, with attribute
  prefetch. This exposes the already-public native field needed for channel nominal
  size; inactive-product access policy is unchanged.
- Admin price rows identify each existing tier and its seller/basis/condition.
  Amount-only service locks exact tiers, validates the whole batch, checks optional
  expected amounts, and writes only amount/verification time plus native audit and
  history. No product, specification, offer, seller, stock or conditions are saved.
  Blank/invalid/extra fields/stale/unknown/duplicate/ambiguous IDs reject atomically.
  Legacy product ID succeeds only with exactly one existing tier; no implicit create.
- Admin input supports Persian digits and two decimal places. Errors preserve the
  draft. Untouched legacy zero-price rows do not block editing other rows; a new
  zero or empty amount still rejects. Generic product-file import remains separate.

## Verification before independent review

- Real Django API tests watched RED then GREEN, including exact-tier field snapshots,
  permission/atomicity/rollback/audit and channel nominal payload regression.
- Isolated full Django suite: **510 passed**, `tg1.settings_test`, temporary media.
- All frontend Node unit tests: **87 passed**; editor-zero regression watched RED
  then GREEN. Touched runtime-file ESLint clean.
- Local Playwright/installed Chrome: **14 scenarios passed**, all nine family
  desktop routes, four narrow-mobile routes, paginated admin exact-tier save,
  blank guard and stale error. No JS page errors or unexpected API writes. Real
  actionable links tested with Playwright trial clicks, reservation URL verified.
- Browser fixture API is loopback-only and contains artificial data, never live data.
  A deliberate stale-price HTTP400 and an aborted background GET are expected.
- Django system check clean; migration consistency and OpenSpec strict checked.
- Production frontend build: see final verification/review report for exit status.
- Independent review/fix outcome is recorded separately, not inferred from tests.

Screenshots in `catalog-board-visual/` are local fixture evidence, not deployed UI.
No new dependency or schema migration. Both backend and frontend must be released
together: the editor requires the new exact-tier API. Deploy is a separate choice.
