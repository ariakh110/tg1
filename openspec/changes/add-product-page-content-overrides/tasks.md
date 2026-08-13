## 1. Documentation
- [x] 1.1 Record proposal, design, product requirements, and PRD.

## 2. Backend
- [x] 2.1 Add product SEO/content, FAQ, related-product, index-mode, and price-verification fields with migrations.
- [x] 2.2 Add validated and sanitized API serialization plus atomic admin editing support.
- [x] 2.3 Preserve page content during price/Excel updates and timestamp real price writes.
- [x] 2.4 Seed T006 content for the existing 10 mm ST37 cut-sheet URL.
- [x] 2.5 Add backend tests.

## 3. Frontend
- [x] 3.1 Add the edit-only product content and SEO editor, repeatable FAQ, related-product selector, and preview.
- [x] 3.2 Add deterministic automatic content and indexing/freshness helpers.
- [x] 3.3 Render H1, content, FAQ, links, metadata, and schema in initial server HTML.
- [x] 3.4 Make visible prices, buy/cart/checkout tiers, and structured Offer data share the verified-price rule.
- [x] 3.5 Add frontend tests.

## 4. Verification And Release
- [x] 4.1 Run migration checks, backend checks/tests, frontend tests/lint/build, and OpenSpec validation.
- [ ] 4.2 Commit, synchronize, and push both repositories without staging unrelated changes.
- [ ] 4.3 Rebuild deploy archives and document the backend-first deployment and price-refresh sequence.

## Verification Record
- `manage.py check --settings=tg1.settings_test`: passed.
- `manage.py makemigrations --check --dry-run --settings=tg1.settings_test`: passed.
- `manage.py test products --settings=tg1.settings_test`: 44 passed.
- Full backend suite: 259 passed and 2 pre-existing `sales.tests.LoadingVehicleWeighbridgeTests` errored because their fixture still supplies removed `StoreOrderItem.unit_price` and `total_price` arguments.
- `npm run test:seo`: 18 passed.
- Targeted ESLint: passed.
- `npm run build`: passed; existing unrelated image/effect warnings remain.
