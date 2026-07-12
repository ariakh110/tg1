# Tasks

## 1. Documentation

- [x] Add PRD for taxonomy CRUD and public product-list finalization.
- [x] Add OpenSpec proposal/design/tasks/spec delta.
- [x] Review with product owner before implementation.

## 2. Backend

- [x] Add or confirm category edit/deactivate/reactivate API behavior.
- [x] Add or confirm option edit/deactivate/reactivate API behavior.
- [x] Add audit events for category/option deactivate/reactivate.
- [x] Add usage counts or impact hints for categories/options.
- [x] Tighten product validation so inactive options are rejected for new writes.
- [x] Add tests for taxonomy CRUD, inactive option rejection, usage counts, and admin/public visibility.

## 3. Frontend Admin

- [x] Add edit controls for category rows in taxonomy panel.
- [x] Add deactivate/reactivate controls for category rows.
- [x] Add edit controls for controlled option rows.
- [x] Add deactivate/reactivate controls for controlled option rows.
- [x] Show product usage count and warning before soft-deactivation.
- [x] Keep inactive options visible in admin but hidden from product create/update dropdowns.

## 4. Frontend Public Product List

- [x] Finalize active category/type tabs from backend data.
- [x] Group sheet/coil products by steel grade and product form while retaining factory per row.
- [x] Render row title from structured specs.
- [x] Render origin as city/province plus delivery place.
- [x] Render price, inquiry, or order/request action based on price and availability.
- [x] Preserve filter query parameters and aggregate every backend response page into one public list.

## 5. Verification

- [x] `cmd /c openspec validate add-taxonomy-crud-and-product-listing --strict`
- [x] `python manage.py makemigrations --check --dry-run --settings=tg1.settings_test`
- [x] `python manage.py check`
- [x] `python manage.py test --settings=tg1.settings_test`
- [x] `npm run lint`
- [x] Stop any running Next dev process for this repo, then `npm run build`
- [x] Smoke-test `/admin/dashboard`, `/products`, and one product detail page.
