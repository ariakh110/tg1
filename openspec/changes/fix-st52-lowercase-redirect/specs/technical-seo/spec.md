## ADDED Requirements

### Requirement: Legacy ST52 Landing Consolidation

The storefront SHALL permanently consolidate the previously published uppercase ST52 landing on its lowercase canonical URL. The redirect SHALL be one hop, preserve the query string, and target the canonical production origin.

#### Scenario: Legacy URL without trailing slash
- **WHEN** a client requests `/category/sheet/ST52`
- **THEN** the response status is HTTP 301
- **AND** the Location is `https://kavex.ir/category/sheet/st52`

#### Scenario: Legacy URL with query string
- **WHEN** a client requests `/category/sheet/ST52?source=legacy`
- **THEN** the response status is HTTP 301
- **AND** the Location is `https://kavex.ir/category/sheet/st52?source=legacy`

#### Scenario: Canonical lowercase URL
- **WHEN** a client requests `/category/sheet/st52`
- **THEN** no legacy-path redirect is applied
