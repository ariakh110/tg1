# Change: Admin-managed cluster landing pages (SEO phase 2)

## Why
The SEO strategy needs keyword cluster landings (e.g., «ورق ST52», «شمش 3SP») with real, human-authored content — the strategy doc explicitly warns that auto-generated thin pages risk Google's scaled-content penalty. So landings must be admin-authored, not generated.

## What Changes
- Backend (blog app): new `Landing` model (family, slug, title, tagline, intro, body[HTML], steel_grade, meta_title, meta_description, sort_order, is_active; unique family+slug) + `LandingSerializer` + public `LandingViewSet` (read-only, active, filterable by family/slug) + admin `AdminLandingViewSet` (CRUD, `IsAdminOrActiveAdminRole`) + Django admin + migration `0009_landing`.
- Frontend: public server route `/category/<family>/<slug>` (metadata from the landing, BreadcrumbList JSON-LD, hero, authored HTML body, auto product grid filtered by family[+grade], contact CTA); admin `LandingsPanel` CRUD registered in the dashboard; the family page lists its landings; sitemap includes active landings.
- Reuses existing APIs: products via the `category_code`/`product_kind`/`steel_grade` filters; content-API pattern mirrors FAQ.

## Impact
- Affected specs: `product-seo`
- Backend: `blog/models.py`, `blog/serializers.py`, `blog/views.py`, `blog/urls.py`, `blog/admin.py` + migration `blog/0009_landing`.
- Frontend: new `app/category/[family]/[slug]/page.js`, `app/lib/landingsApi.js`, `app/components/admin/LandingsPanel.js`; edits to `app/lib/contentApi.js`, `app/lib/productsSeo.js`, `app/sitemap.js`, `app/category/[family]/page.js`, `app/components/admin/AdminDashboardPage.js`.
