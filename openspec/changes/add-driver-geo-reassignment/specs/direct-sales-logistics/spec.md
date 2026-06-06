## ADDED Requirements

### Requirement: Driver Operational Profile
The system SHALL maintain one operational logistics profile per driver user.

#### Scenario: Driver updates location and availability
- **WHEN** an active driver submits availability, location, vehicle, plate, capacity, and service radius
- **THEN** the system SHALL save the profile for future dispatch matching.

#### Scenario: Admin verifies a driver
- **WHEN** an admin marks a driver operational profile as verified
- **THEN** that driver SHALL become eligible for automatic geo matching if their `DRIVER` role is active and the profile is available.

### Requirement: Geo-Based Driver Matching
The system SHALL find nearby valid drivers for direct-order load offers.

#### Scenario: Coordinates are available
- **WHEN** a loading point and driver profiles have latitude/longitude
- **THEN** the system SHALL compute approximate distance in kilometers
- **AND** return verified available drivers inside the applicable search/service radius sorted by nearest first.

#### Scenario: Coordinates are missing
- **WHEN** coordinates are unavailable but city/province values exist
- **THEN** the system SHALL match verified available drivers by exact city/province.

#### Scenario: Auto publish uses nearby drivers
- **WHEN** an admin creates a delivery request without explicit driver ids
- **THEN** the system SHALL create offers for the nearest eligible drivers rather than broadcasting to every active driver.

### Requirement: Time-Limited Driver Offers
The system SHALL expire unanswered driver load offers.

#### Scenario: Offer is published
- **WHEN** a delivery offer is created
- **THEN** it SHALL include an expiration timestamp
- **AND** the system SHALL record an internal notification log for the targeted driver.

#### Scenario: Driver responds after expiration
- **WHEN** a driver attempts to accept or decline an expired open offer
- **THEN** the system SHALL mark the offer expired and reject the response.

#### Scenario: Periodic expiry runs
- **WHEN** the delivery-offer expiry task runs after offer expiration
- **THEN** it SHALL mark stale open offers as expired and write delivery events.

### Requirement: Delivery Offer Reassignment
The system SHALL reassign underfilled delivery requests after declined or expired offers.

#### Scenario: Driver declines offer
- **WHEN** a driver declines a delivery offer and the request still needs drivers
- **THEN** the system SHALL offer the load to the next eligible nearby driver if auto reassignment is enabled.

#### Scenario: Offer expires
- **WHEN** an open offer expires and the request still needs drivers
- **THEN** the system SHALL offer the load to the next eligible nearby driver if auto reassignment is enabled.

#### Scenario: Duplicate prevention
- **WHEN** reassignment selects candidates
- **THEN** the system SHALL exclude drivers who already received an offer for the same delivery request.
