# Change: Marketer role + section-scoped admin panel access

## Why
Today admin-panel access is all-or-nothing: any user who is staff/superuser or has an active `ADMIN` role can see and use **every** menu (products, taxonomy, users, settings, SEO, payments, logistics, …). The owner wants to grant some people admin access **limited to part of the panel** — specifically a بازاریاب (marketer/salesperson) who should only work with CRM and sales, never touch products/users/settings. The current model has no way to express "admin, but only these sections", and hiding menus in the frontend alone is not security.

## What Changes
- **New role `MARKETER`** added to `RoleCode` (migration `0008`, choices-only — no DB-level change). Granting/revoking it is superuser-only, like `ADMIN`.
- **Admin sections registry** (`accounts/admin_sections.py`): a single source of truth listing every admin-panel section id (identical to the frontend sidebar `id`s) and a `ROLE_SECTIONS` map. `ADMIN` → all sections; `MARKETER` → `crm, crm-followups, crm-funnel, assistant, direct-sales`.
- **Section-scoped enforcement** in `IsAdminOrActiveAdminRole`: superuser/staff and the `ADMIN` role keep full access (unchanged). A restricted role (e.g. `MARKETER`) may reach a view only if the view declares an `admin_section`/`admin_sections` that intersects the role's allowed set. **Views with no declared section are closed to restricted roles by default (fail-safe)** and unchanged for full admins. Only the marketer-relevant viewsets are annotated (customers CRM/funnel/followups, assistant, direct-sales store-orders + their logistics).
- **`/v1/users/me/`** now returns `admin_sections` — `"ALL"` for full admins, or the ordered list of allowed section ids — so the frontend can filter the sidebar from the server's truth.
- **Frontend**: the admin sidebar (`ADMIN_NAV_ITEMS`) is filtered by the user's allowed sections; the panel gate (`/admin` layout + dashboard) accepts any user with ≥1 section; a restricted user lands on their first allowed section; the out-of-band «مدیریت محتوا» (full-admin only) and «تنظیمات» (settings section) sidebar buttons are gated; `UsersPanel` gains a «بازاریاب» role chip (superuser-locked).

Out of scope: per-user section overrides (this is role-level, the same set for every marketer); a UI to edit the role→section map (it's defined in code); auditing.

## Impact
- Affected specs: `users-roles-kyc` (added: restricted admin roles, marketer default sections, `/me` exposes sections).
- Backend (tg1): `accounts/models.py` (+`MARKETER`), `accounts/migrations/0008_*`, new `accounts/admin_sections.py`, `accounts/permissions.py` (section check), `accounts/serializers.py` (`admin_sections` on `UserMeSerializer`), `accounts/views_v1.py` (`set_role` superuser-lock for `MARKETER`), `customers/views.py` + `assistant/views.py` + `sales/views.py` (view `admin_section` annotations), new `accounts/test_admin_sections.py`.
- Frontend (kavehmetal): `app/lib/roles.js` (section helpers + `MARKETER`), `app/lib/auth.js` (`admin_sections` passthrough), `app/admin/layout.js` (panel gate + content guard), `app/components/admin/AdminDashboardPage.js` (nav filter + default panel + footer gates), `app/components/admin/UsersPanel.js` (marketer chip).
- Deploy: `deploy.ps1 both` — migration `0008` is choices-only (no schema change); backend code + frontend rebuild.
