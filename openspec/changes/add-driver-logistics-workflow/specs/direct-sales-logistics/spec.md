## ADDED Requirements

### Requirement: Driver Load Offers
The system SHALL let admins publish direct-order load offers to active drivers with full shipment details.

#### Scenario: Admin publishes load offer
- **WHEN** an admin creates a delivery request for a loading-ready direct order
- **THEN** the system SHALL publish offers to the selected active drivers
- **AND** each offer SHALL include order, buyer, destination, loading, weight, vehicle, and dispatcher-note details.

#### Scenario: Loading blockers prevent dispatch
- **WHEN** a direct order has unpaid amount, risk blocker, missing stock verification, missing proforma confirmation, or missing loading permission
- **THEN** the system SHALL reject delivery request creation.

### Requirement: Twenty-Five Ton Driver Capacity
The system SHALL require one driver assignment for each 25 tons or fraction of 25 tons.

#### Scenario: Load at or below 25 tons
- **WHEN** the total shipment weight is at most 25,000 kg
- **THEN** the delivery request SHALL require one accepted driver.

#### Scenario: Load above 25 tons
- **WHEN** the total shipment weight is more than 25,000 kg
- **THEN** the delivery request SHALL require `ceil(total_weight_kg / 25,000)` accepted drivers.

#### Scenario: Capacity is full
- **WHEN** enough drivers have accepted a delivery request
- **THEN** further acceptances SHALL be rejected.

### Requirement: Driver Offer Response
The system SHALL allow only the targeted active driver to accept or decline their load offer.

#### Scenario: Driver accepts offer
- **WHEN** a targeted driver accepts an open offer
- **THEN** the system SHALL create a delivery assignment for that driver
- **AND** planned assignment weight SHALL not exceed 25,000 kg.

#### Scenario: Non-targeted user responds
- **WHEN** a user who is not the offered driver attempts to respond
- **THEN** the system SHALL reject the request.

### Requirement: Driver Assignment Tracking
The system SHALL let assigned drivers update shipment status and upload shipment evidence.

#### Scenario: Driver updates shipment status
- **WHEN** the assigned driver moves to a valid next delivery status
- **THEN** the system SHALL update the assignment and write an event log.

#### Scenario: Driver uploads proof
- **WHEN** the assigned driver uploads a valid shipment document
- **THEN** the system SHALL store the document and write an event log.
