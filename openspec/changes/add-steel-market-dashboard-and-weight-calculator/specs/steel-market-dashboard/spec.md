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

### Requirement: Interactive Market Charts And Commodity Details
The system SHALL render market time series using Apache ECharts with chronological dates, explicit missing-value gaps, zoom controls and honest single-observation states. Commodity views SHALL include group/producer/symbol drilldown and independent expandable row charts with separate price and volume axes.

#### Scenario: Commodity trades share a date
- **WHEN** multiple executions for one symbol, currency and unit share a date
- **THEN** the chart receives the traded-volume weighted price for that date and a separate base-price series
- **AND** base quotes are never presented as actual execution prices

#### Scenario: Visitor searches and sorts commodity rows
- **WHEN** a visitor searches for a name, grade, size, symbol or producer and sorts a column
- **THEN** the system filters all saved reports and orders matching rows before pagination
- **AND** the original full source name and any explicitly supplied specifications are displayed

#### Scenario: Administrator selects visible metals
- **WHEN** an administrator saves a subset of global metal codes
- **THEN** only selected instruments appear in public summary, exchange filters and history
- **AND** hidden instrument observations remain stored

#### Scenario: Provider has missing or mixed observations
- **WHEN** a history response includes missing prices or observations from multiple providers
- **THEN** missing prices remain gaps and the global chart uses the latest observation provider consistently

### Requirement: Map Scope And Consistent Market Navigation
Each commodity map selection SHALL filter the table by its group, producer, exact symbol and report date as applicable. Breadcrumb navigation SHALL narrow or clear this scope. All three market pages SHALL place their shared navigation at the top of their hero containers.

#### Scenario: Visitor drills down to a producer and symbol
- **WHEN** a visitor clicks a group, producer and symbol in succession
- **THEN** the table requests that exact symbol and producer for the map date
- **AND** returning to the root clears all map filters

### Requirement: Daily Branded Channel Drafts
Full administrators SHALL be able to preview daily commodity summaries and item/producer/delivery-specific messages and publish selected drafts independently to the configured Kaveh Metal Telegram and Bale channels. Generation SHALL use only the requested report date, preserve missing values, deduplicate physical offer volumes, and disclose any explicitly configured tax adjustment.

#### Scenario: Administrator generates daily messages
- **WHEN** an administrator selects a date, group and report type
- **THEN** the system creates reusable drafts with platform-specific Kaveh Metal signatures and source report references
- **AND** preview generation sends no external messages

#### Scenario: Administrator explicitly publishes a draft
- **WHEN** an administrator publishes a reviewed draft to a configured platform
- **THEN** the system records an outbound attempt and per-platform publication status
- **AND** repeated requests do not resend a successful or uncertain publication

#### Scenario: Delivery outcome is uncertain
- **WHEN** the platform request times out or returns an unconfirmed outcome
- **THEN** the system displays that uncertainty without leaking bot credentials or automatically retrying
- **AND** only a definite platform rejection or a completed uncertain attempt explicitly reviewed as not delivered by a full administrator can be retried through an explicit retry action

### Requirement: Optional Telegram MTProto proxy transport
The system SHALL offer a full-admin-configured bot-only MTProto proxy transport with write-only application hash, validated classic/dd proxy links and message-free connection checks.

#### Scenario: Administrator tests a saved proxy
- **WHEN** a full administrator tests a saved proxy with application and bot credentials
- **THEN** the system checks connection, bot authentication and channel posting permission without publishing a message
- **AND** unsupported FakeTLS links and private proxy destinations are rejected

#### Scenario: Proxy fails before or after sending
- **WHEN** a proxy fails before sending starts
- **THEN** the system tries the next configured candidate within a bounded preflight budget
- **AND** after sending starts it never switches proxies or retries an uncertain delivery automatically

### Requirement: Domestic market hierarchy with synchronized table
The system SHALL group active priced catalog products by product kind, registered subtype, factory and individual product, showing current navigation scope in both map and table.

#### Scenario: Visitor drills into a sheet factory
- **WHEN** a visitor selects sheet, black sheet, and a factory in the map
- **THEN** the map shows only that level's descendants and the table contains only matching products across all pages
- **AND** the path displays each selected ancestor with root and one-step return actions

#### Scenario: Search within a selected path
- **WHEN** a visitor searches or changes table pages within a selected map scope
- **THEN** scope and search are applied before pagination and stale requests cannot overwrite the current table
- **AND** returning to all products clears the map path and search

#### Scenario: Missing or custom catalog metadata
- **WHEN** a priced product uses a custom subtype or lacks classification or factory metadata
- **THEN** it remains accessible in the appropriate registered or explicitly unspecified group without guessing from its name
