## ADDED Requirements

### Requirement: Account Registration
The system SHALL allow registration with `username` and `password` as the only required fields. `email` SHALL be optional. `username` MUST match `^[a-zA-Z0-9_]{3,}$`. When an email is provided the account SHALL be created inactive and an email-verification message sent; when no email is provided the account SHALL be activated immediately so the user can sign in.

#### Scenario: Register without email
- **WHEN** a client POSTs `{username, password, phone}` (no email) to `/api/auth/register/`
- **THEN** the account is created with `is_active = true`
- **AND** the user can immediately obtain tokens via `/api/token/`

#### Scenario: Register with email
- **WHEN** a client POSTs `{username, email, password}` to `/api/auth/register/`
- **THEN** the account is created with `is_active = false`
- **AND** a verification email is sent, and `/api/token/` fails until verification

#### Scenario: Reject non-English username
- **WHEN** the `username` contains characters outside `[a-zA-Z0-9_]` or is shorter than 3 characters
- **THEN** the request is rejected with HTTP 400 and no account is created

### Requirement: Mobile Phone Capture At Registration
The system SHALL accept an optional `phone` value at registration and persist it on the user's `Profile`.

#### Scenario: Phone stored on profile
- **WHEN** a registration request includes `phone`
- **THEN** the value is saved to the user's `Profile.phone`
- **AND** it is returned by the profile endpoint (`/api/me/`)

### Requirement: Google Sign-In
The system SHALL provide `POST /api/auth/google/` that accepts a Google ID token (`credential`), verifies it against the configured `GOOGLE_OAUTH_CLIENT_ID`, and returns SimpleJWT `access`/`refresh` tokens plus the user. On first sign-in the user SHALL be created (active) with a unique username derived from the Google account. When `GOOGLE_OAUTH_CLIENT_ID` is not configured the endpoint SHALL fail gracefully without creating a user.

#### Scenario: Valid Google credential
- **WHEN** a valid `credential` is posted to `/api/auth/google/` and `GOOGLE_OAUTH_CLIENT_ID` is configured
- **THEN** the token is verified, the matching user is found or created and activated
- **AND** the response contains `access`, `refresh`, and `user`

#### Scenario: Invalid Google credential
- **WHEN** an invalid or expired `credential` is posted
- **THEN** the response is HTTP 400 with `{"detail": "invalid_google_token"}`

#### Scenario: Google login not configured
- **WHEN** `/api/auth/google/` is called while `GOOGLE_OAUTH_CLIENT_ID` is empty
- **THEN** the response is HTTP 503 with `{"detail": "google_login_unconfigured"}`
- **AND** no user is created
