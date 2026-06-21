## ADDED Requirements

### Requirement: Section-scoped admin access
The admin API SHALL support admin roles that are limited to a subset of admin-panel sections. Each admin section has a stable id shared between backend and frontend. Full admins (staff, superuser, or the active `ADMIN` role) SHALL have access to all sections. A user whose only admin access comes from a restricted role SHALL be able to reach an admin endpoint only when that endpoint declares a section the role is allowed. An admin endpoint that declares no section SHALL remain accessible to full admins and SHALL be denied to restricted roles (fail-safe default).

#### Scenario: Restricted role reaches an allowed section
- **WHEN** a user whose only admin role allows the `crm` section calls a CRM admin endpoint declared for `crm`
- **THEN** the request is allowed

#### Scenario: Restricted role is blocked from other sections
- **WHEN** that same user calls an admin endpoint that is not in any of their allowed sections (e.g. user management)
- **THEN** the request is denied

#### Scenario: Full admin is unaffected
- **WHEN** a staff/superuser or active-`ADMIN`-role user calls any admin endpoint, with or without a declared section
- **THEN** the request is allowed

### Requirement: Marketer role
There SHALL be a `MARKETER` role that grants restricted admin access scoped to the CRM and direct-sales sections only (`crm`, `crm-followups`, `crm-funnel`, `assistant`, `direct-sales`) and no other admin section. Granting or revoking the `MARKETER` role SHALL be restricted to superusers, as with the `ADMIN` role.

#### Scenario: Marketer can use CRM and sales but not management
- **WHEN** a user has an active `MARKETER` role
- **THEN** they can access the CRM, follow-ups, funnel, sales-assistant, and direct-sales admin endpoints
- **AND** they are denied products, taxonomy, users, settings, and other management endpoints

#### Scenario: Only superusers manage the marketer role
- **WHEN** a non-superuser admin tries to grant the `MARKETER` role to a user
- **THEN** the request is denied

#### Scenario: Inactive marketer role grants nothing
- **WHEN** a user has a `MARKETER` role that is not active
- **THEN** they are treated as having no admin sections

### Requirement: Current user exposes allowed admin sections
The current-user endpoint (`/v1/users/me/`) SHALL return the caller's allowed admin sections so clients can render only permitted menus. The value SHALL be `"ALL"` for full admins, or the list of allowed section ids (in a stable order) for a restricted role, or an empty list for non-admins.

#### Scenario: Full admin sees ALL
- **WHEN** a staff/superuser or active-`ADMIN`-role user requests `/v1/users/me/`
- **THEN** `admin_sections` is `"ALL"`

#### Scenario: Marketer sees only their sections
- **WHEN** a user with an active `MARKETER` role requests `/v1/users/me/`
- **THEN** `admin_sections` lists exactly the marketer sections and no others
