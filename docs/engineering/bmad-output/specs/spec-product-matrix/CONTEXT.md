# CURRENT — product matrix context

Existing `products/admin_import.py` builds products/specs/offers/tiers and distinguishes supplied length type. `find_product` relies on name plus supplied specs; the new create-only matrix must compare normalized full physical specs without requiring equal display names. `ProductSpecificationSerializer` validates required category fields and backend options. Existing `availability_status` represents stock state, not quantitative inventory. Prices use 12 total digits and two decimals. `resolve_store_seller_id` can create a seller and therefore must not be called by preview.

Frontend product admin already fetches active categories, sellers and attribute options; the new component can receive these rather than add taxonomy APIs. Existing non-main checkouts and unrelated frontend handoff/review edits are preserved. No matrix endpoint/component currently exists. Relevant existing tests: `products.test_product_identity`.
