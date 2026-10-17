## 1. Iran Commodity Exchange backend
- [x] 1.1 Add the IME physical-trade model, constraints, indexes, migration and read-only admin.
- [x] 1.2 Add a bounded official IME client, steel-chain filtering, Jalali conversion and idempotent upsert service.
- [x] 1.3 Add manual and scheduled sync entry points with last-good-data retention and health metadata.
- [x] 1.4 Add public IME summary, searchable/filterable trade rows and bounded symbol-history endpoints.
- [x] 1.5 Test upstream validation, idempotency, currency/unit preservation, filters, history and failure behavior.

## 2. Global metals backend
- [x] 2.1 Add instrument/observation models, constraints, indexes, migration and admin controls.
- [x] 2.2 Add provider abstraction and Metals.Dev connector with server-only credentials, timeouts, quota-aware refresh and freshness metadata.
- [x] 2.3 Add validated staff CSV import for licensed observations not covered by the connector.
- [x] 2.4 Add global summary, exchange/instrument list and bounded-history endpoints.
- [x] 2.5 Test secret isolation, provider parsing, idempotency, change calculation, stale/error states and CSV validation.

## 3. Storefront
- [x] 3.1 Preserve `/market` as the catalog market and add shared navigation for the three distinct market contexts.
- [x] 3.2 Add `/commodity-exchange` with IME summary cards, product-group map, filters, trade table and price/supply-demand history.
- [x] 3.3 Add `/global-metals` with exchange filters, source-aware price table, daily movement, toman conversion input and history chart.
- [x] 3.4 Add responsive RTL loading, empty, stale, partial-provider and API-error states without fabricated prices.
- [x] 3.5 Add SEO metadata, source explanations, calls to action, menu/footer links and sitemap entries.

## 4. Validation and deployment
- [x] 4.1 Run backend migrations/checks/tests and focused frontend lint/tests.
- [x] 4.2 Run the production frontend build and review desktop/mobile RTL layouts.
- [x] 4.3 Add deployment sync/health checks and document IME/global provider configuration.
- [ ] 4.4 Commit, push and prepare reviewed deployment archives.

