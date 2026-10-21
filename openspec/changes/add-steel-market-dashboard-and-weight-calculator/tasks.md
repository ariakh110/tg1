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

## 5. Admin-managed global market source
- [x] 5.1 Add singleton provider settings with a write-only API key, enable switch, and bounded refresh interval.
- [x] 5.2 Resolve automatic synchronization from admin settings with an environment fallback.
- [x] 5.3 Add admin-only force-sync and licensed CSV import controls to the site settings panel.
- [x] 5.4 Test secret handling, permissions, provider synchronization, frontend lint, and production builds.

## 6. Interactive market chart corrections
- [x] 6.1 Replace custom price SVGs with shared Apache ECharts line/bar charts and correct null/date handling.
- [x] 6.2 Add commodity hierarchy drilldown and independent inline charts with range controls.
- [x] 6.3 Add server sorting, pagination, specification search and full report-derived product descriptions.
- [x] 6.4 Add administrator metal visibility selection applied to public summary and history.
- [x] 6.5 Verify chart options, API regressions, frontend build and deploy archives.

## 7. Scope navigation and daily channel reports
- [x] 7.1 Apply every treemap level to group/producer/symbol/date table scope and support root/breadcrumb reset.
- [x] 7.2 Align market navigation within all three page heroes.
- [x] 7.3 Add branded daily item/group drafts with independent Telegram/Bale configuration and explicit preview/send controls.
- [x] 7.4 Persist per-channel publication status, duplicate prevention and outbound audit logs.
- [x] 7.5 Verify API calculations, authorization, publication mocks, real canvas drilldown and browser/admin flows; prepare deployment.

## Telegram MTProto recovery
- [x] Add optional bot MTProto transport, validated classic/dd proxy imports, write-only application hash and admin connection tests.
- [x] Preserve Bale HTTPS delivery, bound preflight failover, and block automatic resend after uncertain delivery.
- [x] Add explicit audited admin review for completed uncertain publications without sending.
- [x] Verify transport tests, frontend lint/build and browser settings/test flow with mocked delivery.
- [x] Prepare committed deployment archives using the existing PrepareOnly release workflow.
