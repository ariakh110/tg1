# Design: Taxonomy CRUD and Product Listing Finalization

## Existing Foundation

- `ProductCategory` stores visible catalog hierarchy, product kind, defaults, required fields, active flag, and sort order.
- `ProductAttributeOption` stores controlled option values and dependencies.
- `ProductSpecification` stores selected option values for each product.
- `ProductAuditLog` already records product and taxonomy create/update events.
- `/admin/dashboard` has separate products and taxonomy panels.
- `/products` already consumes backend data and can group active products.

## API Design

Prefer additive reuse:

- `PATCH /api/categories/{id}/` for category edits.
- `PATCH /api/attribute-options/{id}/` for option edits.
- `PATCH /api/categories/{id}/` with `is_active=false|true` for category lifecycle.
- `PATCH /api/attribute-options/{id}/` with `is_active=false|true` for option lifecycle.

If the UI needs clearer semantics or audit payloads, add custom actions:

- `POST /api/categories/{id}/activate/`
- `POST /api/categories/{id}/deactivate/`
- `POST /api/attribute-options/{id}/activate/`
- `POST /api/attribute-options/{id}/deactivate/`

The custom actions are optional for the first pass if PATCH already logs the update.

## Usage Counts

Category count:

- Count products whose category is the category itself or a descendant.
- Public count should consider only active products.
- Admin impact count should consider all products.

Option count:

- Map option groups to product specification fields:
  - `manufacturing_process` -> `specifications.manufacturing_process`
  - `surface_finish` -> `specifications.surface_finish`
  - `steel_grade` -> `specifications.steel_grade`
  - `factory` -> `specifications.factory`
  - `cut_type` -> `specifications.cut_type`
  - `province`, `city`, `delivery_place` -> delivery location fields or address conventions where available.
- First iteration can expose counts in serializer fields or a dedicated admin stats endpoint.

## Validation Rules

Product writes must:

- only accept active controlled options,
- enforce parent dependency when scoped options exist,
- clear `length_mm` and `cut_type` for coil,
- require `length_mm` and `cut_type` for sheet,
- reject inactive categories for public product creation/update flows.

Taxonomy edits must:

- preserve unique `(group, value, parent)`,
- require parent for factory/city/sheet-grade,
- warn before changing `value` when products use it.

## Frontend Design

Taxonomy panel:

- Add row actions: edit, deactivate/reactivate.
- Use a compact edit drawer or inline edit block.
- Keep create forms visible.
- Show product usage count and dependency parent.
- Filter/search existing options by group, label, value, product kind, and parent.

Product list:

- Main category tabs from active categories with active products.
- Sheet type tabs from backend category/default or active option/product combinations.
- Grade/form section cards/tables:
  - header: steel grade, product form, product count, update hint if available.
  - rows: title, dimensions, origin, group-local market comparison, price/action.
- Request bounded backend pages and aggregate every page before grouping the public list.
- Keep category/type/form/search/ordering filters in query string state; do not expose page navigation.
- Calculate each row's market comparison from priced products in its own grade/form group.

## Backward Compatibility

- Existing product APIs remain stable.
- Existing product rows with legacy option values remain displayable.
- New writes become stricter to prevent future inconsistent data.

## Open Questions

- Should changing an option `value` be blocked when products use it, or allowed with a migration/update operation?
- Should taxonomy deletion be permanently disabled in the custom dashboard?
- Should usage counts include inactive products in public stats or only admin impact stats?
