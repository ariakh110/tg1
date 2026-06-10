# Change: Admin-managed FAQ (frequently asked questions)

## Why
The site needs a frequently-asked-questions section that staff can manage themselves (add/edit/remove Q&A), grouped by topic like common marketplace FAQs, presented in the site's own theme.

## What Changes
- Add a `FAQItem` model (in the `blog` content app): `category` (grouping), `question`, `answer`, `sort_order`, `is_active`.
- Add `GET /api/blog/faqs/` (public, active items) and admin CRUD `GET/POST/PATCH/DELETE /api/blog/admin/faqs/` (admin only).
- Seed ~12 starter Q&A across 5 categories (registration, ordering, payment, delivery, support) — editable from the admin panel.
- Frontend: a themed `/faq` page (categories with accordions) and an admin **"سوالات متداول"** panel for CRUD; a footer link.

## Impact
- Affected specs: `faq`
- Affected code (backend): `blog/models.py`, `blog/serializers.py`, `blog/views.py`, `blog/urls.py`, `blog/admin.py` + migrations `0007_faqitem`, `0008_seed_faqs`.
- Affected code (frontend, kavehmetal): new `app/faq/page.js`, `app/components/admin/FaqPanel.js`; edits to `app/lib/blogApi.js`, `app/lib/contentApi.js`, `app/components/admin/AdminDashboardPage.js`, `app/components/Footer.js`.
- Mirrors the existing `FeaturedLoad` content pattern (public + admin viewsets, `contentApi.js` helpers, admin panel, public page).
