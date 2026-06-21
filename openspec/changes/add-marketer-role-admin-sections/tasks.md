## 1. Backend (tg1)
- [x] 1.1 Add `MARKETER` to `accounts/models.RoleCode`; migration `0008_alter_userrole_role_add_marketer` (choices-only, no schema change)
- [x] 1.2 New `accounts/admin_sections.py`: `ADMIN_SECTIONS` (ids = frontend sidebar ids), `ALL` sentinel, `ROLE_SECTIONS` (`ADMIN`→ALL, `MARKETER`→crm/crm-followups/crm-funnel/assistant/direct-sales), `effective_admin_sections(user)`
- [x] 1.3 `IsAdminOrActiveAdminRole`: staff/superuser/ALL → allow; else require `view.admin_section`/`admin_sections` ∩ user sections; unannotated view → deny restricted roles (fail-safe)
- [x] 1.4 Annotate marketer views: `customers` (CustomerViewSet→crm,crm-funnel; CustomerActivityViewSet→crm,crm-followups; CustomerTransactionViewSet→crm), `assistant` (4 admin views→assistant), `sales` (AdminStoreOrder + loading/weighbridge/freight→direct-sales; driver/delivery→direct-sales+delivery-logistics)
- [x] 1.5 `UserMeSerializer.admin_sections` ("ALL" or ordered list)
- [x] 1.6 `set_role` superuser-lock extended to `MARKETER`
- [x] 1.7 `manage.py check` + `makemigrations --check` clean

## 2. Frontend (kavehmetal)
- [x] 2.1 `app/lib/roles.js`: `MARKETER` in `ROLE_OPTIONS`; `getAdminSections`, `canAccessSection`, `canAccessAdminPanel`, `isFullAdmin`
- [x] 2.2 `app/lib/auth.js`: carry `admin_sections` from `/me` into the merged user object
- [x] 2.3 `app/admin/layout.js`: gate by `canAccessAdminPanel`; `/admin/content` requires `isFullAdmin`
- [x] 2.4 `app/components/admin/AdminDashboardPage.js`: filter sidebar (desktop + mobile) by sections; redirect restricted user to first allowed panel; gate footer «مدیریت محتوا»/«تنظیمات»; `canAccess = canAccessAdminPanel`
- [x] 2.5 `app/components/admin/UsersPanel.js`: «بازاریاب» role chip, superuser-locked

## 3. Verification
- [x] 3.1 `manage.py test accounts customers assistant` — existing 25 pass (permission change backward compatible)
- [x] 3.2 New `accounts/test_admin_sections.py` (9 pass): effective sections for superuser/admin/marketer/inactive; `/me` payload; marketer allowed on CRM/funnel/follow-ups/assistant; marketer denied on users-admin; admin keeps full access
- [x] 3.3 `npx eslint` clean on changed frontend files
- [x] 3.4 `openspec validate add-marketer-role-admin-sections --strict`
- [ ] 3.5 After deploy: grant a test user `MARKETER` (as superuser) → they see only CRM/فروش menus, other API calls 403; revoke → access removed
