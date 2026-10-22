## ADDED Requirements
### Requirement: Catalog asset write boundaries
The system SHALL permit catalog asset writes only for staff or authorized sellers and SHALL reject parent reassignment and active document formats.
#### Scenario: Foreign product write
- **WHEN** a seller attempts to create specifications for a product without their offer
- **THEN** the request is denied and no record is created
### Requirement: Safe editorial HTML
The system SHALL sanitize landing HTML on write and read and clean historical stored bodies during migration.
#### Scenario: Stored event handler
- **WHEN** a landing contains an image event handler
- **THEN** public and admin responses omit the handler while preserving safe content
### Requirement: Bounded public assistant usage
The system SHALL enforce atomic shared-cache minute and daily limits keyed by IP and authenticated identity before AI calls and SHALL fail closed when quota storage is unavailable.
#### Scenario: Burst or cache failure
- **WHEN** a quota is exhausted or quota storage is unavailable
- **THEN** the request returns 429 or 503 respectively and no AI call is made
