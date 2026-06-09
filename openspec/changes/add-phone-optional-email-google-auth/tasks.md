## 1. Backend — registration
- [x] 1.1 Make `email` optional in `RegisterAPIView` (require only `username` + `password`)
- [x] 1.2 Enforce username regex `^[a-zA-Z0-9_]{3,}$`
- [x] 1.3 Persist `phone` to `Profile` via `update_or_create`
- [x] 1.4 Activation policy: active immediately when no email; inactive + verification email when email present

## 2. Backend — Google sign-in
- [x] 2.1 Add `GoogleAuthAPIView` (`POST /api/auth/google/`) verifying the ID token and returning `{access, refresh, user}`
- [x] 2.2 Register the URL in `accounts/urls.py`
- [x] 2.3 Add `GOOGLE_OAUTH_CLIENT_ID` to `tg1/settings.py`
- [x] 2.4 Add `google-auth` to `requirements.txt` (already present in the runtime env)

## 3. Verification
- [x] 3.1 `python manage.py check`
- [x] 3.2 curl: register without email → 201 + active; then `/api/token/` succeeds
- [x] 3.3 curl: register with non-English username → 400
- [x] 3.4 curl: `/api/auth/google/` unconfigured → 503 (invalid-credential → 400 reachable once configured)
- [x] 3.5 Confirmed `phone` saved on `Profile` (via `/api/me/`); test users cleaned up

## 4. Frontend (already implemented in kavehmetal)
- [x] 4.1 Redesigned login/register pages (split-screen, themed)
- [x] 4.2 Phone field (required) + optional email + English-username validation
- [x] 4.3 Google button wired to `/auth/google/` (`GoogleLoginButton.js`, env-gated)
- [x] 4.4 `loginWithGoogle` in auth context + `googleLoginApi` in api layer
