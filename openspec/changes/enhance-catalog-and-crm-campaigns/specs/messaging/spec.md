## ADDED Requirements

### Requirement: Reusable Messaging Contact Groups
Authorized operators SHALL be able to create, update, list, and delete messaging groups whose members are normalized Iranian mobile numbers with optional CRM-customer links. A group SHALL declare whether it is website-managed or imported from Kavenegar, and a Kavenegar-import group MAY store an outbound reporting tag.

#### Scenario: Website customer group is created
- **WHEN** an operator creates a group from selected CRM customers
- **THEN** each valid unique customer phone becomes one group member linked to that customer

#### Scenario: Kavenegar export is imported
- **WHEN** an operator pastes or uploads phone numbers exported from a Kavenegar panel group
- **THEN** valid normalized numbers replace the local group's members and duplicates/invalid rows are reported

### Requirement: Campaign Audience Preview
Before bulk delivery, the system SHALL resolve and preview an audience from selected customer ids, saved group ids, product category ids, or CRM filters. The resolver SHALL normalize and deduplicate phone numbers and SHALL return the valid count, invalid count, sample recipients, and source summary without sending a message.

#### Scenario: Recipient belongs to multiple selected audiences
- **WHEN** the same normalized phone is present in a group and a product-consumer segment
- **THEN** the preview counts it once

#### Scenario: Audience is empty
- **WHEN** no valid recipient matches the submitted selectors
- **THEN** sending is rejected and no outbound message is created

### Requirement: CRM SMS and Bale Campaign Delivery
An authorized operator SHALL be able to send a confirmed message to one CRM customer or a previewed bulk audience over SMS or Bale. Provider enable switches, dry-run behavior, SMS daily cap, per-recipient audit logs, and customer timeline activities SHALL continue to apply.

#### Scenario: SMS product campaign is sent
- **WHEN** an operator confirms an SMS campaign to consumers of a product category
- **THEN** Kavenegar receives only valid deduplicated receptors and every recipient has an outbound audit record

#### Scenario: Bale customer message is sent
- **WHEN** an operator chooses Bale for a CRM customer with a valid phone
- **THEN** the existing Safir provider handles the send and its result is shown in the customer's message history

#### Scenario: SMS daily cap would be exceeded
- **WHEN** a campaign would exceed the configured daily SMS cap
- **THEN** recipients beyond the remaining allowance are not sent and the response reports the cap-limited result
