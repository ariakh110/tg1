## MODIFIED Requirements

### Requirement: Site Settings Resource
The system SHALL expose a single global site-settings resource at `GET /api/site-settings/` returning `{ site_name, google_oauth_client_id, sections }`, where `sections` contains booleans for `marketplace`, `featured_loads`, `export`, `offers`, and `blog`. The resource SHALL be publicly readable. `google_oauth_client_id` MAY be empty.

#### Scenario: Read settings
- **WHEN** any client GETs `/api/site-settings/`
- **THEN** the response is HTTP 200 with `site_name`, `google_oauth_client_id`, and the five section booleans

#### Scenario: Defaults
- **WHEN** no admin has changed settings yet
- **THEN** `sections.marketplace` is `false`, the other sections are `true`, and `google_oauth_client_id` is an empty string

## ADDED Requirements

### Requirement: Admin-Configurable Google Login
The system SHALL store the Google OAuth Client ID in site settings, editable only by admins via `PATCH /api/site-settings/`. Both the frontend Google Sign-In initialization and the backend ID-token verification SHALL use the stored value, falling back to the `GOOGLE_OAUTH_CLIENT_ID` environment variable when it is empty. Changing it SHALL NOT require a rebuild.

#### Scenario: Admin sets the client ID
- **WHEN** an admin PATCHes `{"google_oauth_client_id": "<id>.apps.googleusercontent.com"}`
- **THEN** the value is persisted and returned by subsequent GETs

#### Scenario: Google login uses the configured ID
- **WHEN** `google_oauth_client_id` is set and a user signs in with Google
- **THEN** the frontend initializes Google Sign-In with that ID and the backend verifies the ID token's audience against it

#### Scenario: Empty falls back to env or disabled
- **WHEN** `google_oauth_client_id` is empty
- **THEN** the system uses the `GOOGLE_OAUTH_CLIENT_ID` env var if present, otherwise the Google button is shown disabled and `POST /api/auth/google/` returns 503
