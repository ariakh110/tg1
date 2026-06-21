## ADDED Requirements

### Requirement: Admin User Account Control
Admins SHALL be able to approve (activate) and suspend (deactivate) any user account from the admin API, controlling whether that user can authenticate (login is gated by the active flag). An admin SHALL NOT be able to deactivate their own account. A non-superuser admin SHALL NOT be able to modify a superuser account. These actions SHALL require admin access (staff/superuser or an active admin role).

#### Scenario: Approve lets a user log in
- **WHEN** an admin activates a previously inactive user
- **THEN** that user can obtain an authentication token
- **AND** when the admin deactivates the user, the user can no longer obtain a token

#### Scenario: Admin cannot deactivate themselves
- **WHEN** an admin tries to deactivate their own account
- **THEN** the request is rejected

#### Scenario: Superuser is protected from non-superuser admins
- **WHEN** a non-superuser admin tries to change a superuser account
- **THEN** the request is denied

### Requirement: Admin Password Reset
Admins SHALL be able to set a new password for a user account through the admin API, with a minimum length, so a user who is locked out can be recovered without database access.

#### Scenario: Reset password and log in
- **WHEN** an admin sets a new password (meeting the minimum length) for a user
- **THEN** the user can log in with the new password

#### Scenario: Too-short password is rejected
- **WHEN** an admin submits a password shorter than the minimum
- **THEN** the request is rejected and the password is unchanged

### Requirement: Admin Role Management
Admins SHALL be able to grant or revoke a user's roles through the admin API, including the admin role. Granting or revoking the admin role SHALL be restricted to superusers. Revoking a role SHALL deactivate it without deleting the user's history.

#### Scenario: Grant a seller role
- **WHEN** an admin grants the seller role to a user
- **THEN** the user's seller role becomes active and appears on the user's record

#### Scenario: Only superusers manage the admin role
- **WHEN** a non-superuser admin tries to grant the admin role to a user
- **THEN** the request is denied
