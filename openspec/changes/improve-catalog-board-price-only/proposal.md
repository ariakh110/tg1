# Change: Compare all product families clearly and isolate amount-only bulk edits

## Why
Factory-mixed generic product grids are hard to compare, and bulk pricing currently
routes through a product importer with unrelated side effects.

## What Changes
- Factory/form/grade sections with family-aware numeric ordering and responsive
  semantic display on /products for every family and custom fallbacks.
- Admin-only existing pricing-row list and atomic amount-only update by tier_id.
- **BREAKING:** blank prices no longer clear tiers/availability in bulk-price panel;
  ambiguous product_id requires exact tier; no implicit new Offer/day tier.
- Retain generic product file import, VAT contract and other product pages.

## Impact
products/views.py, dedicated price service/tests; frontend ProductsPageClient and
new display model/table, BulkPricePanel/contentApi and real tests/screenshots.
Approved by explicit user reply «بله، همین طرح را اجرا کن» to the concrete proposal;
no production database change or deployment authorized.
