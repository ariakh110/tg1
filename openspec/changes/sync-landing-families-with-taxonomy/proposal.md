# Change: Sync landing families with product taxonomy

## Why
The landing editor reads product families from a hard-coded six-item frontend list. Newly created product taxonomy roots therefore cannot be selected, and the public category routes reject their codes with a static allowlist even if a landing is saved.

## What Changes
- Load landing family options from active root `ProductCategory` records that have a stable code.
- Keep the current family available while editing an older landing, even if that taxonomy record is no longer active.
- Resolve public family names and validity from the product taxonomy instead of a fixed frontend allowlist.
- Include dynamically discovered landing families in the sitemap family entries.
- Keep the existing static family metadata only as a visual/title fallback for legacy families.

## Impact
- Affected specs: `product-seo`
- Backend schema/API: no change; the existing `/api/categories/` endpoint remains the source of truth.
- Frontend: landing admin data loading, category route validation/title resolution, landing route validation/title resolution, and sitemap family discovery.

