## ADDED Requirements

### Requirement: Bale Safir Channel
The system SHALL support sending a message to a customer in Bale by their mobile number through the Safir service, configured by an admin with an enable switch, a write-only access key, and a sender bot id. The access key SHALL be write-only — never returned by the read endpoint, with a flag reporting whether it is set. Sending SHALL be gated by the switch and configuration: when Safir is disabled or unconfigured, a Bale send SHALL be recorded as `skipped` (dry-run) on the `bale` channel and SHALL NOT contact the service. Destination numbers SHALL be converted to the `989XXXXXXXXX` form Safir requires, and a provider error (invalid phone, not a Bale user, insufficient credit) SHALL be captured as a failed message rather than raising.

#### Scenario: Dry-run when Safir disabled
- **WHEN** an admin sends a Bale message while Safir is disabled or unconfigured
- **THEN** an outbound message is logged on the `bale` channel with status `skipped`, and the Safir service is not contacted

#### Scenario: Phone is converted to Safir format
- **WHEN** a Bale message is sent to a customer whose stored phone is `09120000001`
- **THEN** the number passed to Safir is `989120000001`

#### Scenario: Provider result is recorded
- **WHEN** Safir is configured and a send succeeds
- **THEN** the outbound message status becomes `sent` and the Safir message id is stored

### Requirement: Channel Selection on Sends
The single-send and bulk-send messaging APIs SHALL accept a channel selector that routes the message either through SMS (default) or through the Bale Safir channel, so the admin can choose how to reach customers.

#### Scenario: Send routed to Bale
- **WHEN** an admin sends a message with the channel set to Bale
- **THEN** the outbound message is recorded on the `bale` channel rather than SMS
