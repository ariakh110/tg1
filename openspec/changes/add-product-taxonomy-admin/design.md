# Design: Product Taxonomy Admin

## Current Shape

- `ProductCategory` is a hierarchical MPTT model with codes, product kind, spec defaults, required fields, sort order, and active state.
- `ProductAttributeOption` is a controlled option table with group, value, label, product kind, optional category, optional parent, sort order, and active state.
- `ProductSpecification` stores selected structured values on each product.
- `ProductViewSet` already exposes public and admin product list behavior.
- `AdminDashboardPage` already has product create/import/list surfaces and can load categories/options/sellers.

## Modeling Decision

Keep visible catalog hierarchy and controlled specification values separate:

- Use `ProductCategory` for the visible category tree: ورق، میلگرد، شمش، لوله، پروفیل, and high-level visible type tabs when needed.
- Use `ProductAttributeOption` for controlled values and dependency graph:
  - `manufacturing_process`: sheet, coil
  - `surface_finish`: black, oiled, alloy, galvanized, color, acid_washed, stainless
  - `steel_grade`: ST37, ST52, CK45, etc.
  - `factory`: Mobarakeh, Oxin, Kavian, Khoramabad, Atieh, etc.
  - `cut_type`: factory, cut
  - `delivery_place`: warehouse, factory
  - `province`, `city`

This avoids overloading category levels with every grade/factory combination and keeps future non-sheet products (rebar, billet, beam) accurate.

## Dependency Rules

- Sheet category selected -> show manufacturing process and surface finish.
- Surface finish selected -> show only grades whose parent is that surface finish.
- Manufacturing process selected -> show only factories whose parent is that process.
- Province selected -> show only cities whose parent is that province.
- Coil selected -> clear/ignore length and cut type.
- Sheet selected -> require length and cut type.

## UI Structure

`/admin/dashboard` should use separate navigation panels:

- Products: create/update product, import template/upload, product inventory table.
- Taxonomy: create category, create controlled option, inspect existing option groups and dependencies.
- Orders, KYC, users, activity: existing admin areas.

Taxonomy UI should show compact management cards and searchable dropdowns. It should not require product images.

## API Contract

The existing endpoints are sufficient for the first implementation:

- `GET/POST /api/categories/`
- `GET /api/categories/active-with-products/`
- `GET/POST /api/attribute-options/`
- `GET /api/products/admin-products/`
- `POST /api/products/admin-upsert/`
- `POST /api/products/admin-bulk-upsert/`
- `GET /api/products/admin-import-template/`
- `POST /api/products/{id}/activate/`
- `POST /api/products/{id}/deactivate/`

If taxonomy edits/deactivation become necessary beyond create-only UI, add additive admin-safe `PATCH` actions later.

## Migration Strategy

No schema migration is required unless new fields are needed. Seed migrations can add missing default options or categories.

## Risks

- Option duplication: mitigate with unique `(group, value, parent)` and existing option list visibility.
- Operator confusion between category and option: taxonomy UI must explain category vs controlled option.
- Legacy free-text records: continue display support while validating new writes.
