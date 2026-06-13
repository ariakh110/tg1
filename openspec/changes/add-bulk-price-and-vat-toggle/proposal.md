# Change: Bulk price update + VAT (ارزش افزوده) display toggle

## Why
The store updates the «قیمت روز» of every product frequently (often daily). Today that means editing offers one-by-one, or downloading a blank 2-row Excel sample and rebuilding it from scratch. Operators also need to show list prices either with or without the 10% value-added tax, defaulting to the pre-tax figure that customers expect to compare.

## What Changes
- **Bulk price — Excel (prefilled):** `admin_import_template` now exports every active product with its current price (min «قیمت روز» tier) instead of two static sample rows. Headers are unchanged, so the existing `admin-bulk-upsert` upload parser still maps. Operator downloads → edits the price column → re-uploads.
- **Bulk price — inline table:** new `admin-bulk-prices` action on `ProductViewSet` (POST `{prices:[{product_id, price}]}`) reuses `bulk_upsert_products` with `resolve_store_seller_id` as the default seller (direct-sales safe) and `create_missing=False`. New admin `BulkPricePanel` lists all products with current price + an editable «قیمت جدید» field and a «ذخیرهٔ همه» button.
- **Products-summary pagination:** `ProductSummaryViewSet` gains `SummaryPagination` (`page_size` query param, max 1000) so the bulk table can fetch the full catalog.
- **VAT toggle (list only):** the `/products` page gets a default-OFF «ارزش افزوده» checkbox. When OFF, displayed list prices (rows, group «شروع از», hero/market average) are shown ×0.9 (10% lower); when ON, full price. State persists in `localStorage`. Market-delta percentages are ratios and stay invariant.

## Impact
- Affected specs: `product-pricing`
- Backend (tg1): `products/views.py` (`admin_import_template` prefill + `admin-bulk-prices` action), `products/api_views.py` (`SummaryPagination`). No migration.
- Frontend (kavehmetal): new `app/components/admin/BulkPricePanel.js`; edits to `app/lib/contentApi.js` (`fetchProductsForPricing`, `bulkUpdatePrices`), `app/components/admin/AdminDashboardPage.js` (nav + render), `app/products/page.js` (VAT checkbox + factor).
