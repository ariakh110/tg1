# PRD: Product Taxonomy CRUD & Public Price List Finalization

## Problem / Opportunity

The first product taxonomy admin step created a dedicated admin panel and backend-driven dropdowns. The next gap is operational control: admins can create taxonomy values, but they still need full lifecycle management for mistakes, inactive values, and product-list display rules.

The public product list also needs to behave like a real steel price list:
- category and type tabs must come from active backend data,
- sheet/coil rows must be grouped by factory,
- each row must show a generated title, dimensions, origin, price or inquiry/order action,
- inactive products and inactive taxonomy values must not leak into the public list.

## Users & Use Cases

- Admin/operator:
  - edits category or option labels/codes after typos,
  - deactivates outdated categories/options without deleting history,
  - sees how many products depend on each taxonomy value,
  - reviews products grouped by factory/type and fixes missing specs.
- Storefront visitor:
  - selects a main category, then a valid subtype such as black sheet or acid-washed sheet,
  - sees factory-grouped price sections,
  - understands whether the product has a price, needs inquiry, or is unavailable/register-order.
- Future marketplace/order workflow:
  - uses the same controlled taxonomy for RFQs and seller stock listings.

## Goals & Success Metrics

- Admin can create, edit, deactivate, and reactivate categories/options from `/admin/dashboard`.
- Admin list keeps inactive taxonomy values visible for management and audit.
- Product form hides inactive taxonomy values by default.
- Public category/type tabs only show active taxonomy/category values that have active products.
- Public product rows are grouped by factory for sheet/coil lists.
- Each factory section has a concise header and product count.
- Product row title is generated from structured specs when `name` is missing or needs normalization.
- All taxonomy lifecycle actions are audit logged.
- Backend and frontend checks pass with no new lint/build errors.

## Functional Requirements

### FR-1 Taxonomy Category CRUD

- Admin can edit category `name`, `code`, `parent`, `product_kind`, `sort_order`, `spec_defaults`, `required_spec_fields`, and `is_active`.
- Admin can deactivate/reactivate categories.
- Deactivating a category must not delete products.
- Public endpoints must exclude inactive categories.
- Admin endpoints/lists must show inactive categories.

### FR-2 Controlled Option CRUD

- Admin can edit option `group`, `label`, `value`, `product_kind`, `parent`, `category`, `sort_order`, and `is_active`.
- Admin can deactivate/reactivate options.
- Product create/update dropdowns must use only active options.
- Admin taxonomy table must include inactive options.
- Parent requirements:
  - `factory` requires a `manufacturing_process` parent.
  - `city` requires a `province` parent.
  - `steel_grade` for `sheet` requires a `surface_finish` parent.

### FR-3 Dependency Safety

- Backend must reject product writes that use inactive controlled options.
- Backend must reject invalid dependent combinations, such as a grade that is not allowed for the selected sheet type.
- Admin UI should prevent obvious invalid submissions before hitting the API.
- When a parent option changes, dependent fields in forms must reset.

### FR-4 Product Counts & Impact Preview

- Taxonomy admin table must show product usage counts where practical:
  - category product count by descendant categories,
  - option count based on matching product specification fields.
- Deactivation UI must warn when a category/option is used by products.
- The first iteration can show counts as read-only impact hints; hard blocking is not required.

### FR-5 Public Product List

- `/products` must request active categories/types from backend data.
- If the main category is sheet, the list must support type tabs such as black, oiled, alloy, acid-washed, galvanized, color, stainless, when active products exist.
- Product sections must group by factory.
- Rows must show:
  - title generated from process, type, thickness, width, length, grade/factory,
  - origin as `city - delivery_place` or `province - delivery_place`,
  - price if available,
  - inquiry button when price is empty but product is available for inquiry,
  - order/request button when out of stock.
- Pagination must remain stable when category/type/filter changes.

### FR-6 Admin Product List

- Admin product list keeps showing all products by default.
- Filters support active, inactive, all, category, search, and later type/factory.
- Deactivation of a product must keep it visible in admin all/inactive views.
- Product actions must be logged.

## Non-functional Requirements

- Keep APIs additive and backward-compatible.
- Keep frontend taxonomy display backend-driven.
- Avoid expensive N+1 queries; use `select_related`, `prefetch_related`, annotations, or aggregate endpoints.
- Keep admin UI understandable for non-technical operators.
- Do not require product images for price-list products.

## Out of Scope

- Real-time market scraping.
- Automatic ERP/WMS sync.
- Complex permission workflow for non-admin taxonomy editors.
- Full RFQ/order creation flow from out-of-stock rows.
- Bulk edit UI for taxonomy values beyond single-row edit.

## UX Notes

- The taxonomy panel should have a management-table feel, not a marketing layout.
- Use inline edit drawer/modal or row edit mode for categories/options.
- Keep danger actions visually separated:
  - deactivate/reactivate as soft lifecycle actions,
  - delete should remain unavailable or reserved for Django admin until there is a strong requirement.
- Show dependency labels clearly: `ST37 -> ورق سیاه`, `مبارکه -> ورق`, `اصفهان -> استان اصفهان`.

## Analytics / Audit Events

- `PRODUCT_CATEGORY_CREATED`
- `PRODUCT_CATEGORY_UPDATED`
- `PRODUCT_CATEGORY_DEACTIVATED`
- `PRODUCT_CATEGORY_ACTIVATED`
- `TAXONOMY_OPTION_CREATED`
- `TAXONOMY_OPTION_UPDATED`
- `TAXONOMY_OPTION_DEACTIVATED`
- `TAXONOMY_OPTION_ACTIVATED`
- `PRODUCT_DEACTIVATED`
- `PRODUCT_ACTIVATED`

## Rollout Plan

1. Add backend admin-safe endpoints/actions or allow PATCH with current viewsets where permission rules already fit.
2. Add usage counts for categories/options.
3. Add edit/deactivate/reactivate controls to the taxonomy panel.
4. Finalize public `/products` grouping by active category/type/factory.
5. Add tests for taxonomy CRUD, inactive option visibility, and public list hiding inactive data.
6. Run backend/frontend verification and smoke tests.

## Risks

- Editing a value can break old product specs if value codes change. Mitigation: prefer editing labels; changing `value` should show usage impact.
- Inactive option values may still exist on older products. Mitigation: display legacy values read-only but reject new writes.
- Counts can be expensive if computed naively. Mitigation: use annotated querysets or a dedicated lightweight stats endpoint.
