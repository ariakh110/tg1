## 1. Backend (tg1, accounts) — no migration
- [x] 1.1 `AdminUserViewSet(ReadOnlyModelViewSet)` replacing `AdminUserListAPIView`: same queryset (prefetch roles/kyc, `q`/`role` filters), `[IsAuthenticated, IsAdminOrActiveAdminRole]`, serializer `AdminUserSummarySerializer`
- [x] 1.2 `_guard_target`: 403 if target `is_superuser` and requester not superuser
- [x] 1.3 `@action set_active` `{is_active}` — block deactivating self (400); save `is_active`
- [x] 1.4 `@action set_password` `{password}` (min 8) — `set_password()` + `save(update_fields=["password"])`
- [x] 1.5 `@action set_role` `{role, is_active}` — validate role in `RoleCode`; ADMIN grant/revoke superuser-only; get_or_create `UserRole` and set `is_active`/`activated_at`
- [x] 1.6 `accounts/urls_v1.py`: register `r"admin/users"` on the router (drop the old `path`)
- [x] 1.7 `AdminSetPasswordSerializer`/`AdminSetRoleSerializer`/`AdminSetActiveSerializer` in `accounts/serializers.py`; add `first_name`/`last_name` to `AdminUserSummarySerializer`
- [x] 1.8 `manage.py check --settings=tg1.settings_test` clean

## 2. Frontend (kavehmetal)
- [x] 2.1 `app/lib/usersApi.js`: `fetchMe()`, `fetchAdminUsers(q, role)`, `setUserActive`, `setUserPassword`, `setUserRole`
- [x] 2.2 `app/components/admin/UsersPanel.js`: self-contained list + search; per-user approve/suspend, password-reset field, role chips (admin chip locked to superuser via `fetchMe`), KYC + joined date
- [x] 2.3 Swap inline `activePanel === "users"` block in `AdminDashboardPage.js` for `<UsersPanel notify={notify} />`; removed now-redundant `users` state + its dashboard fetch

## 3. Verification
- [x] 3.1 `manage.py test accounts --settings=tg1.settings_test` (12 pass): set_active gates login; set_password new-login; set_role(ADMIN) by superuser grants admin access; self-deactivate=400; non-superuser→superuser=403; non-superuser ADMIN grant=403; non-admin=403
- [x] 3.2 `npm run lint` (eslint clean) + `npm run build` (compiled + types OK; build-time ECONNREFUSED is only local prerender hitting a down backend — n/a on server)
- [x] 3.3 `openspec validate add-admin-user-management --strict`
- [ ] 3.4 After deploy: create/suspend a test user → cannot log in; approve → can; reset password; grant seller/admin role
