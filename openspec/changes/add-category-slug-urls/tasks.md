## 1. Backend (tg1, additive)
- [x] 1.1 `ProductSummarySerializer` returns `slug`
- [x] 1.2 `ProductViewSet.get_object` resolves numeric id OR slug; `manage.py check` OK

## 2. Frontend (kavehmetal)
- [x] 2.1 `navCategories`: `PRODUCT_FAMILIES` + family tiles → `/category/<family>` + `familyTitle()`
- [x] 2.2 `productsSeo.getFamilyProducts(family)` via `category_code`/`product_kind`
- [x] 2.3 `/category/[family]` server landing (metadata + Breadcrumb/ItemList JSON-LD + grid + CTA)
- [x] 2.4 Product canonical/schema + ProductCard + sitemap use slug
- [x] 2.5 `/products` list + filters untouched

## 3. Verification
- [x] 3.1 `npx eslint`; `npm run build` compiles
- [x] 3.2 `openspec validate add-category-slug-urls --strict`
- [ ] 3.3 After deploy: `/category/sheet` renders product grid; `/products/<slug>` resolves; sitemap uses slug + /category URLs
