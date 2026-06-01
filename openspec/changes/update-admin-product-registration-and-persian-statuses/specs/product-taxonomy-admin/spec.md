## ADDED Requirements

### Requirement: Product Create/Update

The admin product form SHALL keep common product registration fields simple while preserving advanced pricing-condition controls for exceptional cases.

#### Scenario: Admin registers a normal priced product
- **GIVEN** an admin enters category, seller, unit price, price basis, required product specs, and origin
- **WHEN** the admin submits the form without opening advanced pricing conditions
- **THEN** the product SHALL be created or updated
- **AND** optional pricing-condition dimensions SHALL remain empty.

#### Scenario: Admin enters unit text in optional pricing dimensions
- **GIVEN** optional pricing-condition dimensions contain unit-only text such as `mm`
- **WHEN** the admin submits product registration
- **THEN** the system SHALL treat those optional dimensions as empty
- **AND** product registration SHALL NOT fail with a raw decimal error.

#### Scenario: Admin uses advanced pricing condition
- **GIVEN** a product has a dimension-specific or per-sheet price
- **WHEN** the admin opens advanced pricing settings and enters condition label, width, or length
- **THEN** the system SHALL preserve those values on the pricing tier after numeric cleanup.

#### Scenario: Admin selects a product kind with specific dimension fields
- **GIVEN** the admin selects a product family such as sheet/coil, rebar, pipe, or profile
- **WHEN** the admin reviews the product specification fields
- **THEN** the form SHALL show only dimensions relevant to that product kind
- **AND** diameter SHALL only be shown for rebar and pipe.
