# Change: Add Product Taxonomy Admin

## Why

Admins need to publish steel products and update prices without typing inconsistent category, grade, factory, city, or delivery values. The public product list must be derived from active backend data, while the admin dashboard must keep full control over taxonomy, products, prices, activation state, imports, and auditability.

## What Changes

- Add a documented product taxonomy workflow for category/type/grade/factory dependencies.
- Make taxonomy management a first-class admin dashboard panel.
- Keep categories backend-driven and show only categories/types with active products on public pages.
- Keep product form values backend-driven through searchable dropdowns.
- Preserve inactive products in admin inventory while hiding them from public product lists.
- Audit product and taxonomy management operations.

## Impact

- Backend: product category and attribute option APIs remain the source of truth.
- Frontend: `/admin/dashboard` gains a dedicated taxonomy management area and product forms continue to consume backend options.
- Data: no immediate schema change is required if existing `ProductCategory` and `ProductAttributeOption` support the dependencies.
- Tests: backend validation/listing tests and frontend lint/build are required.
