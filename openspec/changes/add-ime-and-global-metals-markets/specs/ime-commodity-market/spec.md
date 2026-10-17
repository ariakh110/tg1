## ADDED Requirements

### Requirement: Official IME Physical Trade Data
The system SHALL ingest steel-chain physical-trade records from the official Iran Mercantile Exchange service and SHALL preserve the official product, producer, currency, unit and observation dates.

#### Scenario: Official sync succeeds
- **WHEN** the IME service returns valid physical-trade rows for the configured date window
- **THEN** the system idempotently stores eligible steel-chain rows by their official report identifier
- **AND** records their official source and fetch timestamp

#### Scenario: Official service fails or changes schema
- **WHEN** the upstream request times out, exceeds its bounds or returns an invalid schema
- **THEN** the sync fails without replacing the last successful public dataset
- **AND** operators can see the failure state without exposing internal errors to visitors

### Requirement: IME Price And Volume Transparency
The system SHALL show official base, weighted, minimum and maximum prices together with offered, demanded and traded volumes, transaction value, currency and unit when supplied by IME.

#### Scenario: Visitor reviews a trade
- **WHEN** a visitor opens an IME trade row
- **THEN** every monetary and volume value identifies its official unit and trade date
- **AND** rial values are not silently presented as toman values

### Requirement: Searchable IME Market And History
The system SHALL provide searchable and filterable IME summaries, trade rows and bounded symbol history.

#### Scenario: Visitor filters steel trades
- **WHEN** a visitor searches or filters by product, producer, group, symbol or date
- **THEN** the system returns only matching steel-chain physical trades within the supported bounds

#### Scenario: Visitor selects an IME symbol
- **WHEN** a visitor selects a symbol with multiple trade dates
- **THEN** the page charts weighted/base price and supply, demand and traded volume without inventing missing dates

