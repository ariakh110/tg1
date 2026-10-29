## ADDED Requirements
### Requirement: Authenticated account submission
The system SHALL accept authenticated purchase requests using server-owned contact data without sending a verification SMS, preserving idempotency, atomic CRM/notice persistence and owner isolation.
#### Scenario: Signed-in customer submits
- WHEN an active customer submits a valid goods list with a valid account contact
- THEN one inquiry is persisted with the account identity and no verification SMS is sent.
#### Scenario: Foreign receipt or history
- WHEN another user reuses a request UUID or reads own history
- THEN no other user's inquiry reference or details are exposed.
#### Scenario: Missing contact or expired authentication
- WHEN contact is missing or authentication is invalid
- THEN the UI directs to account completion/login without silently sending SMS.
### Requirement: Simple account workspace
The frontend SHALL provide readable primary actions and role-appropriate secondary navigation with accessible mobile and desktop layouts.
#### Scenario: Customer opens account
- WHEN the account workspace loads
- THEN request, purchase tracking, payments and personal information are easy to find, and secondary tools remain accessible.
