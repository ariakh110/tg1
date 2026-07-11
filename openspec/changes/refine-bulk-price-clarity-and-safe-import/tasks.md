## 1. Backend (tg1)
- [x] 1.1 `ProductSummarySerializer`: `steel_grade` + `city` SerializerMethodFields
- [x] 1.2 `ProductSummaryViewSet.get_queryset`: `select_related("specifications")` + `prefetch_related("offers__delivery_options")`
- [x] 1.3 `upsert_product_row`: existing tier — only set condition_label/dimensions when provided
- [x] 1.4 `upsert_product_row`: existing delivery — only write provided fields
- [x] 1.5 `admin_import_template`: 5 importable columns + «نمایش:» display-only identity columns, prefilled
- [x] 1.6 `upsert_product_row`: explicit blank/null `price` clears product pricing and marks it `inquiry`
- [x] 1.7 `admin-bulk-prices`: keep explicit blank `price` rows instead of dropping them
- [x] 1.8 `manage.py check`

## 2. Frontend (kavehmetal)
- [x] 2.1 `BulkPricePanel`: read-only «آلیاژ» + «شهر» columns

- [x] 2.2 `BulkPricePanel`: treat clearing a price input as a valid edit and submit blank price unchanged

## 3. Verification
- [x] 3.1 `npx eslint`; `npm run build` compiles
- [x] 3.2 `openspec validate refine-bulk-price-clarity-and-safe-import --strict`
- [x] 3.3 `py_compile` for changed backend files; targeted ESLint for `BulkPricePanel`
- [ ] 3.4 After deploy: template shows alloy/city per row; re-upload changes only price (specs + tier condition/dimensions preserved); table shows alloy + city; clearing an inline price changes the product to price inquiry without changing other product data
