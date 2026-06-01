## ADDED Requirements

### Requirement: Clear User Domain Naming

The system SHALL use distinct Persian labels for direct purchases, cart checkout, settlements, marketplace load-board requests, and marketplace request status history.

#### Scenario: User views marketplace request detail
- **WHEN** a user opens a marketplace request detail page
- **THEN** request type, status, status-history transitions, and events SHALL be shown in Persian
- **AND** raw labels such as `Event`, `ACTIVE`, or `PENDING_WAREHOUSE` SHALL not be the primary visible text.

#### Scenario: User views marketplace feed
- **WHEN** a user opens the marketplace load-board feed
- **THEN** request type and status SHALL be shown with Persian labels
- **AND** backend codes SHALL remain only internal filter values.
