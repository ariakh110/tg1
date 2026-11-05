# Catalog Board and Price-only Editing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use executing-plans inline; one final independent reviewer. Do not dispatch implementers.

**Goal:** clearer all-family listing and no non-price side effects from bulk pricing.
**Architecture:** dedicated existing-tier transaction service and paginated admin
rows replace generic upsert in price panel. Pure family display model feeds shared
responsive board; old filters/fetching/VAT stay intact.
**Tech Stack:** existing Django/DRF, Next/React, Tailwind, Node tests and browser QA.
**Spec:** docs/engineering/bmad-output/specs/spec-catalog-board-price-only/SPEC.md + companions and OpenSpec improve-catalog-board-price-only.

## Global Constraints
- Owner approved concrete design and execution; local only, no deploy/live edits.
- No migrations/new dependencies or fabricated facts. Keep VAT ×0.9/×1 unchanged.
- Only unit_price/price_verified_at and native audit/history may change; batch atomic.
- Preserve unrelated frontend handoff files and work on existing non-main branches.

## Review Focus
- Multiple sellers/tiers: min_price must never identify a write target (Task1 tests).
- Stale expected amount/duplicate ID/invalid later row must prevent partial writes (Task1).
- Blank value must not delete any tier or change product availability (Task1).
- All families/custom kinds, mixed price bases, missing nominal/weight/date must remain honest (Task2).
- Narrow RTL layout and out-of-stock products must preserve usable actions (Task2 browser).

## Task 1: Strict price-only API and admin editor

**Files:** create products/price_updates.py and products/test_price_updates.py;
modify products/views.py, products/tests.py legacy expectations; frontend
app/components/admin/BulkPricePanel.js, app/lib/contentApi.js; create
app/lib/bulkPriceEditor.mjs and tests/bulkPriceEditor.test.mjs.
**Consumes:** existing PricingTier/Offer/Product, admin permissions and snapshots.
**Produces:** GET /products/admin-price-rows/ paginated results keyed tier_id with
product/seller/tier/basis/unit_price/price_verified_at; POST admin-bulk-prices prices
[{tier_id,price,expected_price?}] (legacy product_id only unambiguous). Max500 rows;
unknown fields, invalid decimals, duplicate/unknown/stale IDs rejected atomically.
Service update_prices(items,actor) returns total_rows/updated_prices/results, no
create/delete or generic upsert. Price editor drafts keyed tier_id, no blank save.

- [ ] Write real DB tests: complete field snapshots unchanged except amount/time;
  other sellers untouched, admin gate, blank/extra/bad/stale/duplicate/missing IDs,
  ambiguous product fallback, rollback and audit; Node literal payload tests.
- [ ] Run focused Django/Node tests: expected RED before implementation.
- [ ] Implement exact locked tier updates and paginated rows; adapt panel/API, preserve generic importer.
- [ ] Re-run focused tests: expected PASS; update old bulk blank expectation to error+no change (approved behavior). Commit scoped backend/frontend changes separately.

## Task 2: Responsive all-family board and final gates

**Files:** create frontend app/lib/productBoard.mjs,
app/products/_components/ProductPriceGroups.js, tests/productBoard.test.mjs,
tests/productBoard.browser.cjs; modify ProductsPageClient.js. Add backend
docs/engineering/reports/catalog-board-implementation.md and task handoff.
**Consumes:** current ProductListSerializer specification/dynamic_specs/active offers;
Task1 admin rows remain a separate contract.
**Produces:** buildPriceGroups(products), getBoardColumns(family,form), dimension/
price/date helpers; ProductPriceGroups({groups,vatFactor}) responsive semantic UI.

- [ ] Write literal tests: rebar8/10/12 numeric factory groups; angle two legs;
  channel nominal6.5 not height; sheet/coil distinct; pipe/profile/billet/custom;
  correct units, missing/stale date/weight, out-of-stock intent; expected RED.
- [ ] Implement pure model and board with existing font/brand; preserve fetching,
  filters and VAT state, remove misleading mixed-basis market-average badges.
- [ ] Run Node tests, ESLint, native frontend build and browser fixtures at390/1440
  with all families/admin panel (no real API writes). Check screenshots/overflow/actions.
- [ ] Run full backend suite in isolated settings_test/temp media, all Node unit
  tests, Django check/migration consistency/OpenSpec strict. Record actual failures.
- [ ] Commit both repos scoped; task-done verification, one independent whole-change
  review, one TDD fix pass for Important/Critical; defer minor notes, record rulings,
  submit workflow receipts/handoff. No merge/push/deploy.

Self-review: CAP1 is Task2, CAP2 is Task1; exact-tier contract is shared only by
editor/API; public board continues existing public API. Approved UI/price semantics
are preserved; no competitor chart/data copying or new pricing policy.
