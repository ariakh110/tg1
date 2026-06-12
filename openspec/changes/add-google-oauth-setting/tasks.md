## 1. Backend (core + accounts)
- [x] 1.1 Add `google_oauth_client_id` to `SiteSettings` + migration `0004_...`
- [x] 1.2 Expose in `SiteSettingsSerializer` (public GET) + accept in admin `PATCH`
- [x] 1.3 `GoogleAuthAPIView` reads `client_id` from `SiteSettings` (env fallback)
- [x] 1.4 Show field in Django admin; `manage.py check`

## 2. Frontend (kavehmetal)
- [x] 2.1 `SettingsProvider` exposes `googleClientId`
- [x] 2.2 `GoogleLoginButton` uses `googleClientId` (env fallback), re-inits GSI when it loads
- [x] 2.3 Admin `SettingsPanel` input + include in `PATCH` payload

## 3. Verification
- [x] 3.1 `openspec validate add-google-oauth-setting --strict`
- [x] 3.2 `manage.py check`; eslint on changed frontend files
- [ ] 3.3 Manual: set Client ID in admin → Google button activates without rebuild
