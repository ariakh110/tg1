# Change: Admin user management — approve/suspend, reset password, manage roles

## Why
The admin panel can only **view** users — there is no way to approve a pending account, suspend a bad actor, reset a forgotten password, or grant/revoke a role from the UI. Login is gated by `is_active` (an inactive account is refused a JWT with `inactive_account`), so today an owner literally cannot let a new user in or lock one out without the Django shell. This adds the missing admin-only write actions on the existing `/v1/admin/users/` surface. No model/migration is needed — it uses the existing `is_active`, `password`, and `UserRole` machinery.

## What Changes
- **`/v1/admin/users/` becomes a viewset** (was a list-only view): list/retrieve unchanged, plus admin-only detail actions:
  - `POST /v1/admin/users/{id}/set_active/` `{is_active}` — approve (activate) or suspend a user.
  - `POST /v1/admin/users/{id}/set_password/` `{password}` — set/reset a user's password (min 8 chars).
  - `POST /v1/admin/users/{id}/set_role/` `{role, is_active}` — grant or revoke a role (reuses `UserRole`); granting/revoking the `ADMIN` role is restricted to superusers.
- **Safety guards**: an admin cannot deactivate their own account; a non-superuser cannot modify a superuser target. All actions require `IsAdminOrActiveAdminRole`.
- **Frontend**: the read-only «کاربران» tab becomes an interactive `UsersPanel` — search, approve/suspend toggle, password reset, and role chips (incl. admin) — backed by a new `usersApi` client.

Out of scope: deleting users, editing email/profile fields, bulk actions, audit-logging of these admin actions (can follow later).

## Impact
- Affected specs: `users-roles-kyc` (added admin-management requirements).
- Backend (tg1): `accounts/views_v1.py` (`AdminUserListAPIView` → `AdminUserViewSet`), `accounts/urls_v1.py` (router registration), `accounts/serializers.py` (small password write serializer), `accounts/tests.py`. **No migration.**
- Frontend (kavehmetal): new `app/lib/usersApi.js`, new `app/components/admin/UsersPanel.js`, swap the inline `activePanel === "users"` block in `app/components/admin/AdminDashboardPage.js`.
- Deploy: `.\deploy.ps1 both` (no migration; backend code + frontend rebuild).
