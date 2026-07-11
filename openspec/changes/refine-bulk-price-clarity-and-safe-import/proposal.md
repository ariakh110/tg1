# Change: Bulk-price clarity (alloy/city) + safe price-only Excel import

## Why
The bulk price tools shipped, but the store owner can't tell products apart: the price table and the Excel template show neither the steel grade (ST37/ST52) nor the city, so two same-named products with different grades look identical. The owner also feared that re-uploading the (mostly blank) Excel would erase the rest of the product data. Investigation confirmed specs and delivery are preserved on blank cells, but a price update did unconditionally wipe the price tier's condition label and dimensions — a real, if narrow, data loss.

## What Changes
- **Price summary exposes grade + city:** `ProductSummarySerializer` adds `steel_grade` (from the spec) and `city` (from the first offer's delivery). `ProductSummaryViewSet` prefetches `specifications` and `offers__delivery_options` to avoid N+1. The admin bulk-price table renders both as read-only columns.
- **Safe importer:** `upsert_product_row` no longer overwrites an existing price tier's `condition_label`/`dimension_width_mm`/`dimension_length_mm` with blanks — those are touched only when the row supplies a value (dynamic `update_fields`). The `DeliveryLocation` update is likewise made blank-safe (only provided fields are written). So a price-only upload changes only the price.
- **Readable, price-only Excel template:** `admin_import_template` keeps five importable columns (id, name, category code, seller id, new price) and adds display-only identity columns prefixed with «نمایش:» (alloy, city, thickness, width, length, type, surface, factory, availability), prefilled per product. The «نمایش:» prefix makes `normalize_header` leave them unmapped, so they are shown for reading but ignored on upload.

- **Explicit blank price clears pricing:** when the admin product form or inline bulk-price endpoint explicitly submits `price` as blank/null, the product's pricing tiers are removed and the product is marked `inquiry` so public surfaces show price inquiry. This is distinct from an omitted `price` field, which still leaves existing prices untouched.

## Impact
- Affected specs: `product-pricing`
- Backend (tg1): `products/serializers.py` (+2 summary fields), `products/api_views.py` (prefetch), `products/views.py` (`admin_import_template`, inline blank price payloads), `products/admin_import.py` (`upsert_product_row` tier + delivery blank-safe, explicit price clearing). No migration.
- Frontend (kavehmetal): `app/components/admin/BulkPricePanel.js` (+2 columns, blank price edits).
