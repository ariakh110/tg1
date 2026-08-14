## 1. Product Page

- [x] 1.1 Render product FAQs open by default with a visible chevron.
- [x] 1.2 Correct automatic Persian family/surface word order without duplicate labels.
- [x] 1.3 Add frontend regression tests for generated product labels.

## 2. Product Images

- [x] 2.1 Enforce deterministic featured-image creation, selection, ordering, and deletion behavior in the API.
- [x] 2.2 Add an edit-only product image manager with upload, primary-image selection, and deletion controls.
- [x] 2.3 Add backend tests for featured image lifecycle and response ordering.

## 3. Verification and Delivery

- [x] 3.1 Run backend tests and migration checks.
- [x] 3.2 Run frontend tests, lint, and production build.
- [x] 3.3 Validate this OpenSpec change in strict mode.
- [x] 3.4 Commit and push both repositories and rebuild deployment archives.

## Verification

- `py -3.10 manage.py test products.tests --settings=kavex_smoke_settings`: 45 passed.
- `py -3.10 manage.py makemigrations --check --dry-run --settings=kavex_smoke_settings`: no changes detected.
- `npm run test:seo`: 19 passed.
- Targeted ESLint: passed.
- `npm run build`: passed; only existing unrelated warnings remain.
- Local production SSR smoke: product route returned 200 with four initially open FAQ disclosures and rendered chevrons.
- `openspec validate refine-product-page-faq-images --strict`: passed.
- GitHub: frontend `aee5796` and backend `84468f1` were pulled/rebased and pushed to `dev-ariakhayer`.
- Deployment archives were rebuilt with the product-image migration, image manager, and FAQ changes present.
