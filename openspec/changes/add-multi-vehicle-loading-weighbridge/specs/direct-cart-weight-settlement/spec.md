## ADDED Requirements

### Requirement: Multi-Vehicle Loading
The system SHALL support multiple loading vehicles and drivers for direct store orders.

#### Scenario: Admin registers multiple loading vehicles
- **WHEN** an admin records loading vehicles for a direct store order
- **THEN** the system SHALL store each vehicle with driver, contact, vehicle type, plate, planned weight, loaded weight, and note
- **AND** the first vehicle SHALL mirror into the legacy single-driver order fields for compatibility.

#### Scenario: Order above twenty-five tons requires multiple vehicles
- **WHEN** a direct store order has estimated or final loaded weight above 25,000 kg
- **AND** an admin attempts a loading or shipping transition
- **THEN** the system SHALL require at least `ceil(total_weight_kg / 25,000)` active loading vehicles with non-empty driver names and plates
- **AND** the required driver names SHALL be distinct.

### Requirement: Weighbridge Slip Evidence
The system SHALL let admins upload multiple weighbridge slip files for direct store orders and expose them to the buyer.

#### Scenario: Admin uploads multiple slips
- **WHEN** an admin uploads one or more JPG, JPEG, PNG, WEBP, or PDF weighbridge slips
- **THEN** the system SHALL attach them to the order
- **AND** each slip MAY be associated with a loading vehicle.

#### Scenario: Buyer views weighbridge slips
- **WHEN** the buyer views their direct order detail
- **THEN** the system SHALL show uploaded weighbridge slip metadata and file URLs.
