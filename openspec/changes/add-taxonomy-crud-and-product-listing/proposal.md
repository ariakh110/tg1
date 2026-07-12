# Change: Add Taxonomy CRUD and Product Listing Finalization

## Why

The product taxonomy admin panel now exists, but admins need full lifecycle control over categories and controlled options. Public product lists also need to behave like steel price lists: backend-driven tabs, comparable grade/form grouping, clear dimensions/origin, and correct price/inquiry/order actions.

Without this change, operators must use Django admin for corrections and the storefront can drift away from the controlled taxonomy.

## What Changes

- Add edit, deactivate, and reactivate workflows for product categories.
- Add edit, deactivate, and reactivate workflows for controlled product options.
- Show taxonomy usage counts/impact hints before deactivation.
- Ensure product write validation rejects inactive or invalid dependent option combinations.
- Finalize `/products` public list behavior around active category/type tabs, grade/form sections, complete filtered results, row titles, origin display, price/inquiry/order actions, and group-local market comparison.
- Expand tests for taxonomy lifecycle, usage visibility, and public list filtering.

## Impact

- Backend: may add admin-safe actions or rely on PATCH/partial update where existing viewsets and permissions are sufficient.
- Frontend: `/admin/dashboard` taxonomy panel gains edit and lifecycle controls; `/products` gains a complete grade/form-grouped price-list view.
- Data: no schema migration is expected unless product usage counts need cached fields; first iteration should compute counts dynamically.
- Docs: this change is backed by `openspec/prd/product-taxonomy-crud-and-listing-prd.md`.
