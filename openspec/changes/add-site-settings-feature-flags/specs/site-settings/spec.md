## ADDED Requirements

### Requirement: Site Settings Resource
The system SHALL expose a single global site-settings resource at `GET /api/site-settings/` returning `{ site_name, sections }`, where `sections` contains booleans for `marketplace`, `featured_loads`, `export`, `offers`, and `blog`. The resource SHALL be publicly readable.

#### Scenario: Read settings
- **WHEN** any client GETs `/api/site-settings/`
- **THEN** the response is HTTP 200 with `site_name` and the five section booleans

#### Scenario: Defaults
- **WHEN** no admin has changed settings yet
- **THEN** `sections.marketplace` is `false` and the other sections are `true`

### Requirement: Admin-Only Settings Update
The system SHALL allow only admin users to update site settings via `PATCH /api/site-settings/`. Updates SHALL be partial (only provided fields change).

#### Scenario: Admin updates a flag
- **WHEN** an admin PATCHes `{"sections": {"marketplace": true}}`
- **THEN** the flag is persisted and returned

#### Scenario: Non-admin blocked
- **WHEN** an unauthenticated or non-admin client PATCHes `/api/site-settings/`
- **THEN** the response is HTTP 401/403 and nothing changes

### Requirement: Dynamic Site Name
The frontend SHALL display the configured `site_name` wherever the brand name appears, falling back to a built-in default so the first render is stable.

#### Scenario: Name reflects settings
- **WHEN** an admin sets `site_name` to a new value
- **THEN** the site shows that name across pages after settings load

### Requirement: Section Feature Flags
The frontend SHALL hide a section's entry points and guard its route when its flag is off, and show it when on. The user marketplace (`/orders`) SHALL be hidden by default.

#### Scenario: Disabled section hidden
- **WHEN** a section flag is `false`
- **THEN** its navigation entry points are not rendered and its route shows a "not available yet" page

#### Scenario: Enabled from admin panel
- **WHEN** an admin enables a previously-off section
- **THEN** its entry points and route become available after settings refresh
