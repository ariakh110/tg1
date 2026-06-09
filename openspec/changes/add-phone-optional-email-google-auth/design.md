## Context
The Django backend (`accounts` app) issues SimpleJWT tokens via `/api/token/`. `RegisterAPIView` currently requires `username`, `email`, `password` and creates an inactive user pending email verification. `Profile.phone` already exists. The frontend has been updated to send `phone` and an optional `email`, and to call a not-yet-existing `/api/auth/google/`.

## Goals / Non-Goals
- Goals: optional email, capture phone at signup, English usernames, Google sign-in returning JWTs.
- Non-Goals: SMS/phone verification (no SMS provider is wired — see existing project notes); changing the email-verification flow when an email IS provided; password reset.

## Decisions
- **Optional email + activation policy:** If `email` is omitted, activate the user immediately (`is_active=True`) because there is no verification channel; the user can log in right away via `/api/token/`. If `email` is present, preserve the existing inactive + verification-email flow unchanged.
  - Alternative considered: always require verification → rejected, defeats "email optional".
- **Phone storage:** `Profile.objects.update_or_create(user=user, defaults={"phone": phone})` after user creation (Profile is otherwise created lazily by `ProfileDetailView`). No model/migration change.
- **Google verification:** Verify the ID token server-side with `google.oauth2.id_token.verify_oauth2_token(credential, google_requests.Request(), GOOGLE_OAUTH_CLIENT_ID)` — the `audience` check ensures only tokens minted for this app are accepted. Match/create the user by verified `email`; generate a unique username from the email local-part or Google `sub`; set `is_active=True`; ensure a `Profile` exists. Return `{access, refresh, user}` from `RefreshToken.for_user`.
- **Username rule:** `^[a-zA-Z0-9_]{3,}$`, validated server-side (defense in depth; the frontend validates too).

## Risks / Trade-offs
- `GOOGLE_OAUTH_CLIENT_ID` unset → endpoint returns `503 google_login_unconfigured` (never crashes); the frontend already shows a disabled button until configured.
- Username collisions for Google users → resolve by appending a numeric suffix until unique.
- Blank emails are non-unique by default in Django's User model, which is fine (multiple phone-only accounts).

## Migration Plan
No DB migration. Deploy = code + `pip install google-auth` + set `GOOGLE_OAUTH_CLIENT_ID` env (optional; Google login stays disabled until set).

## Open Questions
- Should phone be globally unique? Currently no (left as free CharField). Can be tightened later if business requires.
