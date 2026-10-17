## ADDED Requirements

### Requirement: Provider-Backed Global Metal Observations
The system SHALL display a global metal price only when a configured provider supplies a price, currency, unit, exchange or authority, observation timestamp, provider identity and source URL.

#### Scenario: Provider returns a valid observation
- **WHEN** the configured connector returns a schema-valid metal observation
- **THEN** the system stores it idempotently and exposes its provider, source, unit, currency and freshness

#### Scenario: No provider key is configured
- **WHEN** no global provider is enabled
- **THEN** the page explains that global data is unavailable
- **AND** it does not display sample or competitor prices

### Requirement: Global Market Filters And History
The system SHALL provide exchange/authority and instrument filters, current observations, daily movement and bounded history for supported global metals.

#### Scenario: Visitor changes the market filter
- **WHEN** a visitor selects an exchange or authority
- **THEN** the table contains only observations attributed to that market
- **AND** each row retains its original currency and unit

#### Scenario: Visitor opens a global metal chart
- **WHEN** stored observations exist for the selected instrument and range
- **THEN** the page renders the real stored series and labels sparse history clearly

### Requirement: Optional Toman Conversion
The system SHALL treat a toman conversion as a derived estimate using a separately identified USD/toman rate supplied by the operator or a configured currency source.

#### Scenario: Visitor enters an exchange rate
- **WHEN** the visitor supplies a positive USD/toman rate for a USD observation
- **THEN** the page shows the derived toman value and its formula
- **AND** preserves the original USD price beside it

### Requirement: Reviewed Supplemental Instruments
The system SHALL allow staff to import licensed observations for supported instruments that are absent from the automated provider, with mandatory source metadata and validation.

#### Scenario: Staff imports a steel benchmark
- **WHEN** an authorized staff user imports a valid row for HRC, billet, scrap or iron ore
- **THEN** the observation is stored with its source URL, provider, exchange, currency, unit and observation time
- **AND** duplicate time buckets are updated idempotently

#### Scenario: Imported source metadata is incomplete
- **WHEN** a row lacks provider identity, source URL, price, currency, unit or observation time
- **THEN** the row is rejected with a clear validation error

