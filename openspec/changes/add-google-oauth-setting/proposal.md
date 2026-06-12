# Change: Admin-configurable Google OAuth Client ID

## Why
Google login currently depends on a build-time `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (frontend) and a server `GOOGLE_OAUTH_CLIENT_ID` env var (backend). Changing it requires a rebuild + redeploy. The admin should be able to set/change the Google OAuth Client ID at runtime from the existing site-settings panel.

## What Changes
- Add a `google_oauth_client_id` field to the singleton `SiteSettings` model.
- Expose it in `GET /api/site-settings/` (it is a public OAuth client ID) and accept it in admin `PATCH /api/site-settings/`.
- Backend `GoogleAuthAPIView` verifies the Google ID token against the DB value, falling back to the `GOOGLE_OAUTH_CLIENT_ID` env var when empty.
- Frontend: `SettingsProvider` exposes `googleClientId`; `GoogleLoginButton` initializes Google Sign-In from it (env as fallback); the admin Settings panel gains a field to edit it — no rebuild needed.

## Impact
- Affected specs: `site-settings`
- Affected code (backend): `core/models.py`, `core/serializers.py`, `core/views.py`, `core/admin.py`, `accounts/views.py` + migration `core/0004_sitesettings_google_oauth_client_id`.
- Affected code (frontend, kavehmetal): `components/SettingsProvider.js`, `components/auth/GoogleLoginButton.js`, `components/admin/SettingsPanel.js`.
