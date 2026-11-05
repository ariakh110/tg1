# Catalog board / price-only context — 2026-11-05

User supplied six screenshots: current /products?family=rebar mixes factories in
grade groups, long repeated titles/badges, generic columns and bulky actions;
reference screenshots show compact factory sections with size/grade/weight/date.
User requests all product families, not competitor content or a new chart feature.
Owner approved the concrete proposal: «بله، همین طرح را اجرا کن» in reply to
factory-centric family-aware mobile tables and exact-tier price-only editing;
blank/invalid prices error rather than delete. No live changes authorized.

CURRENT: ProductsPageClient groupProducts keys grade/form, sorts thickness/width/
length but omits rebar diameter; fixed five-column grid uses170px action column
for three buttons. getDimensions concatenates all fields; dynamic nominal channel
size absent; mixed-basis average gets described as market. BulkPricePanel displays
product-wide min_price but submits product_id only. admin_bulk_prices calls generic
bulk_upsert_products, which can create a store Offer/tier, reset basis to kg,
overwrite condition metadata in file mode, and blank price deletes all product
tiers and changes availability to inquiry. Isolated SQLite diagnostic confirmed
blank removes tiers/changes availability; numeric update reported success without
changing the original differently-named tier (generic command can create another).
No live database inspected. Generic CSV/XLSX import is a distinct product-editing
workflow and remains explicitly outside price-only panel behavior.

Backend clean at55aecdf; frontend has unrelated dirty handoff/current-state docs.
Keep non-main checkouts, scoped commits; no worktree switch/merge/push/deploy.
Previous bulk-price spec allowed store/day-price creation; this approved change
supersedes that behavior only for inline bulk-price editing. VAT list-toggle
contract (off ×0.9, on ×1) remains unchanged. Schemas/SEO/matrix/import not expanded.
