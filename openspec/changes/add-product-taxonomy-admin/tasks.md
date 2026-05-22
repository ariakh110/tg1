# Tasks

## 1. Documentation

- [x] Read existing OpenSpec and steel marketplace docs.
- [x] Update root project/rules/architecture context with current product taxonomy behavior.
- [x] Add PRD for product taxonomy and price admin.
- [x] Add OpenSpec proposal, design, tasks, and delta spec.

## 2. Backend

- [x] Confirm product category and attribute option endpoints expose enough data for taxonomy admin UI.
- [x] Confirm validation enforces sheet type -> grade and sheet/coil -> factory dependencies.
- [x] Confirm admin product list includes inactive products and public list hides inactive products.
- [x] Add audit logging and tests for taxonomy create actions.

## 3. Frontend

- [x] Add a dedicated "طبقه‌بندی" panel to `/admin/dashboard`.
- [x] Move taxonomy creation controls from the product panel into the taxonomy panel.
- [x] Show existing categories and option groups with dependency labels.
- [x] Keep product creation form wired to backend categories/options only.
- [x] Keep pagination and admin product filters working.

## 4. Verification

- [x] `cmd /c openspec validate add-product-taxonomy-admin --strict`
- [x] `python manage.py makemigrations --check --dry-run --settings=tg1.settings_test`
- [x] `python manage.py check`
- [x] `python manage.py test --settings=tg1.settings_test`
- [x] `npm run lint`
- [x] Stop any running Next dev process for this repo, then `npm run build`
- [x] Smoke-test `/admin/dashboard`, `/products`, and one product detail page.
