## ADDED Requirements

### Requirement: Multi-role support
The system SHALL allow a user to hold multiple roles (BUYER, SELLER, CUTTER, DRIVER, QC, STRUCTURAL_DESIGNER, ADMIN).

#### Scenario: User has multiple roles
- **WHEN** an admin assigns multiple roles to a user
- **THEN** the user profile reflects all assigned roles

### Requirement: KYC request lifecycle
The system SHALL allow users to submit KYC requests with documents and track status (PENDING, APPROVED, REJECTED).

#### Scenario: Submit KYC request
- **WHEN** a user submits required KYC documents
- **THEN** a KYC request is created with status=PENDING

#### Scenario: Approve KYC request
- **WHEN** an admin approves the KYC request
- **THEN** the status updates to APPROVED and professional roles become active

### Requirement: Role gating by KYC
The system SHALL prevent non-approved professional roles from performing restricted actions.

#### Scenario: Unverified seller attempts restricted action
- **WHEN** a user with SELLER role but no approved KYC attempts to create a SELL order
- **THEN** the system returns a forbidden response

### Requirement: API versioning for roles and KYC
The system SHALL expose role and KYC endpoints under `/api/v1`.

#### Scenario: Fetch current user roles via v1
- **WHEN** a client calls `/api/v1/users/me`
- **THEN** the response includes the user's roles and KYC status
