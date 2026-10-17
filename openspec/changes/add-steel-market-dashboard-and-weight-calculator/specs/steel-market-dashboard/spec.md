## ADDED Requirements

### Requirement: Catalog-Backed Steel Market Overview
The system SHALL provide a public steel-market overview derived from active Kaveh Metal products and their current valid pricing tiers, including advances, declines, unchanged rows, grouped market tiles, top movers, and the observation timestamp.

#### Scenario: Visitor opens a populated market
- **WHEN** active products have current and previous normalized prices
- **THEN** the market page shows proportional red, green, and neutral groups with counts and percentage changes
- **AND** every value identifies its pricing basis and latest observation time

#### Scenario: Catalog has no comparable prices
- **WHEN** no active products have comparable current prices
- **THEN** the page shows an empty state and routes the visitor to current products or contact
- **AND** it does not render demonstration or fabricated prices

### Requirement: Durable Product Price History
The system SHALL preserve one closing snapshot per product, normalized pricing basis, and Tehran-local date whenever an effective product price is created or changed.

#### Scenario: Price changes twice in one day
- **WHEN** an operator changes the same effective product price more than once on one Tehran-local date
- **THEN** the date retains one snapshot containing the last valid price for that day
- **AND** snapshots for earlier dates remain unchanged

#### Scenario: First deployment seeds current prices
- **WHEN** the idempotent baseline command runs after deployment
- **THEN** it creates at most one current-day snapshot for each valid current product price
- **AND** it does not invent observations for earlier dates

### Requirement: Comparable Price Units
The system SHALL compare market movement only after converting supported prices to a common per-kilogram basis and SHALL disclose rows that cannot be normalized.

#### Scenario: Per-ton and per-kilogram products are compared
- **WHEN** one tier is priced per ton and another is priced per kilogram
- **THEN** the API converts the per-ton price to a per-kilogram value before calculating movement

#### Scenario: Per-sheet weight is unknown
- **WHEN** a product is priced per sheet and has no valid unit weight
- **THEN** the row remains available with its original price basis
- **AND** it is excluded from gain/loss aggregation with an explicit reason

### Requirement: Searchable Market Rows And History
The system SHALL expose searchable current product rows and a bounded 7, 30, or 90-day daily history series for an eligible product.

#### Scenario: Visitor filters market rows
- **WHEN** a visitor searches by product, factory, grade, or category
- **THEN** the table returns matching active products with current price, previous price, movement, basis, and timestamp

#### Scenario: Visitor opens a price chart
- **WHEN** a visitor selects an eligible product and a supported range
- **THEN** the page renders the returned daily observations as an accessible chart and table summary

### Requirement: Honest External Market Data
The system SHALL display a global or exchange indicator only when its response includes an approved source identity, source URL, unit, currency, observation timestamp, and freshness status.

#### Scenario: No approved provider is configured
- **WHEN** the site has no approved external market provider
- **THEN** the external indicator area reports that data is unavailable
- **AND** domestic catalog data remains usable

#### Scenario: Provider data is stale
- **WHEN** the latest provider observation exceeds its configured freshness window
- **THEN** the UI labels it stale and shows the observation timestamp instead of describing it as live

### Requirement: Administrator-Managed Global Market Provider
The system SHALL allow an authorized administrator to enable the approved global-market provider, set its secret API key and refresh interval, force a synchronization, and import reviewed licensed CSV observations without exposing the stored key in any API response.

#### Scenario: Administrator configures the provider
- **WHEN** an authorized administrator submits a provider key and a refresh interval between 1 and 168 hours
- **THEN** subsequent synchronization uses the saved configuration
- **AND** settings responses expose only whether the key is configured

#### Scenario: Administrator synchronizes immediately
- **WHEN** an authorized administrator requests an immediate synchronization with a valid configured provider
- **THEN** the system fetches, validates, and stores the observations and returns the sanitized synchronization status

#### Scenario: Unauthorized user attempts configuration
- **WHEN** an unauthenticated or non-admin user attempts to update provider settings, synchronize, or import a CSV
- **THEN** the system rejects the request without changing credentials or market observations
