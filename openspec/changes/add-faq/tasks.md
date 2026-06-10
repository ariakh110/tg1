## 1. Backend (blog app)
- [x] 1.1 `FAQItem` model (category, question, answer, sort_order, is_active, timestamps)
- [x] 1.2 `FAQItemSerializer`
- [x] 1.3 `FAQViewSet` (public, active only) + `AdminFAQViewSet` (admin CRUD)
- [x] 1.4 Register `/blog/faqs/` and `/blog/admin/faqs/` + Django admin
- [x] 1.5 `makemigrations` + seed data migration (~12 Q&A / 5 categories) + `migrate` + `check`
- [x] 1.6 Verify public GET returns seeded items; admin write blocked without auth (401)

## 2. Frontend (kavehmetal)
- [x] 2.1 `blogApi.fetchFaqs()` (public) + `contentApi` admin helpers (fetch/save/delete, JSON)
- [x] 2.2 `/faq` page — themed, grouped-by-category accordion
- [x] 2.3 `FaqPanel` admin CRUD + nav item in `AdminDashboardPage` + render
- [x] 2.4 Footer link to `/faq`

## 3. Verification
- [x] 3.1 `openspec validate add-faq --strict`
- [x] 3.2 eslint on new/changed frontend files
- [x] 3.3 curl `/faq` → 200 + compiles; public API returns seeded items (list loads client-side)
- [ ] 3.4 Admin panel CRUD works end-to-end (manual, after admin login)
