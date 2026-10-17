## 1. Market data backend
- [x] 1.1 Add `ProductPriceSnapshot` model, constraints, migration, and admin visibility.
- [x] 1.2 Add a single price-capture service and invoke it from individual, bulk, and import price-write paths.
- [x] 1.3 Add an idempotent command to seed the current baseline without backfilling invented history.
- [x] 1.4 Add public summary, product-table, and bounded-history endpoints with unit normalization and freshness metadata.
- [x] 1.5 Test snapshots, same-day closing updates, inactive/unpriced exclusions, basis normalization, history ranges, and query bounds.

## 2. Market storefront
- [x] 2.1 Add `/market` metadata and a responsive RTL page using the existing Kaveh Metal visual system.
- [x] 2.2 Add status cards, proportional market tiles, searchable/filterable price rows, top movers, and an accessible price-history SVG.
- [x] 2.3 Add loading, empty, sparse-history, API-error, and stale-data states without sample prices.
- [x] 2.4 Connect rows and calls to action to product, inquiry, and contact routes.

## 3. Steel weight calculator
- [x] 3.1 Add pure formula utilities and versioned standard-weight tables for supported sections.
- [x] 3.2 Add `/tools/steel-weight-calculator` with shape-specific inputs, validation, reset, and Persian-formatted results.
- [x] 3.3 Show per-metre/per-unit weight, total kg/tonnes, optional estimated value, formula/standard note, and tolerance disclosure.
- [x] 3.4 Add deterministic tests for representative inputs, boundaries, invalid geometry, and unit conversions.

## 4. Discovery and validation
- [x] 4.1 Add desktop/mobile menu and footer links plus sitemap entries.
- [x] 4.2 Run backend checks/migrations/tests and focused frontend lint/tests.
- [x] 4.3 Run the production frontend build and manually verify desktop/mobile RTL layouts.
- [x] 4.4 Prepare deployment archives and document the post-deploy snapshot seed and smoke checks.
