# Change: Clean category landings + slug product URLs (SEO phase 1b)

## Why
Family browsing only existed as the JS-driven `/products?family=X` (no crawlable landing, no metadata), and product URLs were numeric (`/products/123`) with no keyword. Phase 1b adds crawlable category landings and keyword (slug) product URLs, reusing existing APIs.

## What Changes
- Backend (additive): `ProductSummarySerializer` now returns `slug`; `ProductViewSet.get_object` accepts either a numeric id or a slug, so `/api/products/<slug>/` works (numeric unchanged). No migration — the `slug` field already exists on `Product`.
- New server route `/category/[family]` (sheet/rebar/beam/pipe/profile/billet): metadata, BreadcrumbList + ItemList JSON-LD, a server-rendered product grid (via the existing `category_code`/`product_kind` filter on `/products-summary/`), and a CTA to the full filterable `/products?family=X`.
- `navCategories` points the family tiles to `/category/<family>` (homepage + mobile menu); the list page and its filters are unchanged.
- Product detail canonical + Product/Breadcrumb schema + ProductCard links + sitemap now use the slug URL; numeric URLs still resolve and canonicalize to the slug.

## Impact
- Affected specs: `product-seo`
- Backend: `products/serializers.py`, `products/views.py` (no migration).
- Frontend: new `app/category/[family]/page.js`; `app/lib/navCategories.js`, `app/lib/productsSeo.js`, `app/sitemap.js`, `app/products/[id]/page.js`, `app/components/ProductCard.js`.
