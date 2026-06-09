# Change: Phone at registration, optional email, English usernames, and Google sign-in

## Why
Registration friction is too high: email is mandatory, mobile phone (the primary contact channel for this marketplace) is not captured at signup, and there is no social login. We want to collect the phone number up front, make email optional, enforce English-only usernames, and let users sign in with Google.

## What Changes
- Modify `RegisterAPIView`:
  - Make `email` **optional** (only `username` + `password` required).
  - Accept and persist `phone` to the user's `Profile`.
  - Enforce username format `^[a-zA-Z0-9_]{3,}$`.
  - Activation policy: with email → keep current inactive + verification-email flow; without email → activate the account immediately (no other verification channel exists).
- Add endpoint **`POST /api/auth/google/`**: verify a Google ID token (`credential`) and return SimpleJWT `{access, refresh, user}`, creating the user on first sign-in.
- Add setting `GOOGLE_OAUTH_CLIENT_ID` (env) and dependency `google-auth`.
- Frontend (kavehmetal) is already implemented: redesigned auth pages, phone field, optional email, English-username validation, and a Google button that posts to `/auth/google/`.

## Impact
- Affected specs: `authentication`
- Affected code: `accounts/views.py`, `accounts/urls.py`, `tg1/settings.py`, `requirements.txt`
- No database migration (the `Profile.phone` field already exists).
- Frontend already done: `app/auth/*`, `app/lib/{api,auth}.js`, `app/components/auth/GoogleLoginButton.js`.
