## ADDED Requirements

### Requirement: Interactive Delivery Map Provider
The system SHALL expose direct-sales dispatch locations through a frontend map provider abstraction.

#### Scenario: Neshan map is configured
- **WHEN** `NEXT_PUBLIC_MAP_PROVIDER` is `neshan` and `NEXT_PUBLIC_NESHAN_MAP_KEY` is present
- **THEN** the admin and driver logistics UIs SHALL render an interactive Neshan map for relevant dispatch coordinates
- **AND** map clicks SHALL update provider-neutral latitude/longitude fields.

#### Scenario: Map provider is unavailable
- **WHEN** the map provider key is missing or the SDK fails to load
- **THEN** the logistics UIs SHALL keep manual coordinate entry available
- **AND** SHALL NOT block publishing delivery requests or updating driver profiles.

#### Scenario: Provider replacement
- **WHEN** the platform replaces Neshan with another map or routing system
- **THEN** the change SHALL be isolated to the map provider adapter/configuration
- **AND** admin, driver, and buyer logistics screens SHALL continue to consume provider-neutral coordinate props.

### Requirement: Delivery Location Map Context
The system SHALL show delivery location context where coordinates are available.

#### Scenario: Admin previews nearby drivers
- **WHEN** the admin enters a pickup coordinate and previews matched drivers
- **THEN** the UI SHALL show the pickup point and matched driver points on the map.

#### Scenario: Driver views a load offer
- **WHEN** a driver views an offer with pickup coordinates
- **THEN** the UI SHALL show pickup and driver-current-location context on the map when coordinates exist.

#### Scenario: Buyer views order loading context
- **WHEN** a buyer order has loading-point coordinates in quote metadata
- **THEN** the order detail UI SHALL show those loading points on a provider-neutral map component.
