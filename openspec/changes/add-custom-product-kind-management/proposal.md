# Change: Add custom product-kind management

## Why

The taxonomy panel can create categories and controlled options, but its product-kind selectors are hard-coded to six frontend values. An operator therefore cannot introduce a genuinely new catalog family such as angle or channel and reuse it in option and product forms without a code change.

## What Changes

- Allow an admin to create a new root product kind from the category form using a stable technical code.
- Derive saved custom product-kind choices from backend category data instead of a frontend-only list.
- Keep generic specification and dimension inputs available for custom kinds and expose configured grade/process/surface/factory/cut options.
- Populate header, mobile, and homepage category navigation from active backend categories with products while retaining dedicated landing routes for built-in families.
- Add regression coverage for category, option, product, and public-category behavior of a custom kind.

## Impact

- Affected specs: `product-taxonomy`.
- Backend: existing `ProductCategory.product_kind`, `ProductAttributeOption.product_kind`, product upsert validation, and focused tests; no schema migration.
- Frontend: taxonomy management, admin product form, category navigation, and homepage category tiles.
- Product requirements: `openspec/prd/product-taxonomy-admin-prd.md`.
