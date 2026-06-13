## 1. Backend (tg1)
- [x] 1.1 `ProductSummarySerializer`: `steel_grade` + `city` SerializerMethodFields
- [x] 1.2 `ProductSummaryViewSet.get_queryset`: `select_related("specifications")` + `prefetch_related("offers__delivery_options")`
- [x] 1.3 `upsert_product_row`: existing tier — only set condition_label/dimensions when provided
- [x] 1.4 `upsert_product_row`: existing delivery — only write provided fields
- [x] 1.5 `admin_import_template`: 5 importable columns + «نمایش:» display-only identity columns, prefilled
- [x] 1.6 `manage.py check`

## 2. Frontend (kavehmetal)
- [x] 2.1 `BulkPricePanel`: read-only «آلیاژ» + «شهر» columns

## 3. Verification
- [x] 3.1 `npx eslint`; `npm run build` compiles
- [x] 3.2 `openspec validate refine-bulk-price-clarity-and-safe-import --strict`
- [ ] 3.3 After deploy: template shows alloy/city per row; re-upload changes only price (specs + tier condition/dimensions preserved); table shows alloy + city
