## 1. Backend (core)
- [x] 1.1 Add singleton `SiteSettings` model (site_name + 5 section flags, marketplace default false)
- [x] 1.2 `SiteSettingsSerializer` returning `{ site_name, sections }`
- [x] 1.3 `SiteSettingsAPIView` — GET public, PATCH admin-only (partial)
- [x] 1.4 Route `GET/PATCH /api/site-settings/` + register model in Django admin
- [x] 1.5 `makemigrations` + `migrate` + `manage.py check`
- [x] 1.6 Verify GET defaults, PATCH 401 without auth, PATCH works with admin token

## 2. Frontend infrastructure (kavehmetal)
- [x] 2.1 `lib/siteSettingsApi.js` (fetch + admin update)
- [x] 2.2 `SettingsProvider` + `useSiteSettings()` (seeded defaults, fetch on mount, refresh)
- [x] 2.3 Wire provider into `app/layout.js`

## 3. Section gating
- [x] 3.1 `SectionDisabled` "coming soon" component
- [x] 3.2 Guard routes: /orders, /orders/[id], /barandaz, /export, /blog (/offers has no route)
- [x] 3.3 Hide entry points: Navbar, sale-hall cards, homepage tiles/banners/blog slider, account-layout marketplace item, Sidebar
- [x] 3.4 Marketplace hidden by default

## 4. Dynamic site name
- [x] 4.1 `brandify` helper + dynamic `siteName` across chrome (Header/Footer) and all primary public pages (home, terms, privacy, sale-hall, export, about, contact, barandaz, categories, blog slider) — verified rendering 0 "کاوه متال"
- [ ] 4.2 Remaining internal/lower-traffic surfaces (same pattern): account area (layout/dashboard/payments/purchases), blog content pages (BlogArchive/[categories]/[slug]), admin dashboard internal labels, products/[id]/buy, blog page metadata title

## 5. Admin Settings panel
- [x] 5.1 Add `SettingsPanel` (site name + section toggles) wired to the update API
- [x] 5.2 Add "settings" nav item + wire the sidebar Settings button

## 6. Verification
- [x] 6.1 `openspec validate add-site-settings-feature-flags --strict`
- [x] 6.2 eslint on new/changed frontend files
- [x] 6.3 curl `/`, `/orders` (coming soon), `/sale-hall` (no marketplace card) → 200
- [ ] 6.4 Toggle marketplace on from admin panel → /orders becomes available (manual, after admin logs in)
