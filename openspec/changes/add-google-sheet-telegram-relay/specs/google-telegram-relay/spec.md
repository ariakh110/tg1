## ADDED Requirements

### Requirement: Approved Private Relay Queue
The system SHALL queue only admin-approved market messages for the optional Google transport and SHALL expose immutable text and target only to a separately authenticated relay.

#### Scenario: Owner approves a report
- **WHEN** Google transport is selected and an admin approves a report
- **THEN** one delivery job is queued without a Telegram request from the website
- **AND** repeating approval does not create another publication

### Requirement: Conservative Delivery Recovery
The system SHALL claim each attempt once and SHALL NOT automatically redeliver an attempt with an unknown outcome.

#### Scenario: Google cannot acknowledge a successful send
- **WHEN** Telegram returns a message ID but the receipt request fails
- **THEN** the script persists and retries only the receipt
- **AND** no second Telegram send occurs

#### Scenario: A claimed attempt expires
- **WHEN** no receipt arrives before the claim deadline
- **THEN** the attempt becomes unknown and requires channel review before a new attempt

### Requirement: Existing Bot Compatibility
The Google extension SHALL retain private polling, owner authorization and existing channel schedules and SHALL pin the website destination without requiring a public Web App.

#### Scenario: The website supplies a different channel
- **WHEN** the job destination differs from the channel configured in Script Properties
- **THEN** the script rejects it before sending to Telegram
