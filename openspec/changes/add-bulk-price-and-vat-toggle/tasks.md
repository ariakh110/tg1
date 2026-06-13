## 1. Backend (tg1)
- [x] 1.1 `admin_import_template`: prefill every active product + current price (headers unchanged)
- [x] 1.2 `admin-bulk-prices` action (POST `{prices:[{product_id, price}]}`) → `bulk_upsert_products` + `resolve_store_seller_id`, `create_missing=False`
- [x] 1.3 `SummaryPagination` on `ProductSummaryViewSet` (`page_size` query param, max 1000)
- [x] 1.4 `manage.py check`

## 2. Frontend (kavehmetal)
- [x] 2.1 `contentApi`: `fetchProductsForPricing` + `bulkUpdatePrices`
- [x] 2.2 `BulkPricePanel` (table of all products + editable price + «ذخیرهٔ همه») + nav/render in AdminDashboardPage
- [x] 2.3 `/products` «ارزش افزوده» checkbox (default OFF, ×0.9 on list/hero prices, localStorage persist)

## 3. Verification
- [x] 3.1 `npx eslint`; `npm run build` compiles
- [x] 3.2 `openspec validate add-bulk-price-and-vat-toggle --strict`
- [ ] 3.3 After deploy: download template shows all products+prices; inline table saves prices (direct-sales, no seller error); `/products` checkbox OFF shows 10%-lower, ON shows full
