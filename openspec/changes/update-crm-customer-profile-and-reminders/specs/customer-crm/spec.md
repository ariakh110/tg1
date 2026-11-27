## ADDED Requirements

### Requirement: Shared customer profile
The system SHALL store contact name, organization role and final decision authority in the shared CRM customer record. Mobile users with a scoped CRM sales role SHALL edit only assigned customer profiles.

#### Scenario: Name recorded while logging a call
- **WHEN** a salesperson confirms a call with a valid new mobile number and profile details
- **THEN** the CRM customer is created with those details and is visible under the same name in the website CRM

#### Scenario: Existing customer profile changed
- **WHEN** an authorized operator updates the profile from mobile or website
- **THEN** both clients read the shared values and ownership and phone identity are preserved

### Requirement: Private due reminders in Bale
The system SHALL attempt a due reminder for open dated CRM work to the responsible operator's active verified private Bale binding. Work with an explicit owner SHALL use that owner. Work without one SHALL use the assigned customer operator or work creator when available. A claim SHALL be unique per item, recipient and deadline.

#### Scenario: Work becomes due
- **WHEN** the scheduler finds open work at or past its due time and its recipient has an eligible private binding
- **THEN** the bot attempts delivery only to that recipient
- **AND** a repeated tick does not send the same reminder a second time
