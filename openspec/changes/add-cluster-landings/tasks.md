## 1. Backend (blog app)
- [x] 1.1 `Landing` model (family, slug, title, tagline, intro, body, steel_grade, meta_*, sort_order, is_active) + unique (family, slug)
- [x] 1.2 `LandingSerializer`
- [x] 1.3 public `LandingViewSet` (read-only, active, filter family/slug) + admin `AdminLandingViewSet` (CRUD)
- [x] 1.4 register `/blog/landings/` + `/blog/admin/landings/` + Django admin
- [x] 1.5 `makemigrations` (`0009_landing`) + `check`

## 2. Frontend (kavehmetal)
- [x] 2.1 `landingsApi` (getLanding/listFamilyLandings/listAllLandings) + contentApi admin CRUD
- [x] 2.2 `/category/[family]/[slug]` server landing (metadata + Breadcrumb JSON-LD + authored body + product grid + CTA)
- [x] 2.3 `LandingsPanel` admin CRUD + nav in AdminDashboardPage
- [x] 2.4 family page lists its landings; sitemap includes landings; `getFamilyProducts` supports grade

## 3. Verification
- [x] 3.1 `npx eslint`; `npm run build` compiles
- [x] 3.2 `openspec validate add-cluster-landings --strict`
- [ ] 3.3 After deploy: admin creates a landing → `/category/sheet/st52` renders (body + products); appears in sitemap + family page
