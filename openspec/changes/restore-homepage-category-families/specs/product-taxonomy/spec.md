## ADDED Requirements

### Requirement: Stable Public Product Family Navigation
The homepage category grid and header category menus SHALL retain the six established product families and SHALL merge active root categories from the backend by stable category code. A family SHALL NOT disappear only because it currently has no active products or because the category request fails. New active coded roots SHALL be appended without duplicating established families.

#### Scenario: Only one established family has active products
- **WHEN** the catalog currently contains active products only under `sheet`
- **THEN** the homepage still displays sheet, rebar, beam, pipe, profile, and billet

#### Scenario: New active root category exists
- **WHEN** the taxonomy contains an active root category with code `raw-materials`
- **THEN** `raw-materials` is added to the public family navigation without removing or duplicating established families

#### Scenario: Category API is unavailable
- **WHEN** the public category request fails
- **THEN** the six established family cards and menu entries remain visible

### Requirement: Complete Secure Taxonomy Pagination
The storefront SHALL load every page of the active taxonomy before deriving root product families. Same-host pagination links SHALL use the secure scheme of the configured API base when a reverse proxy emits an `http` next link for an `https` deployment.

#### Scenario: Active roots span multiple pages
- **WHEN** one or more active root categories are returned after the first API page
- **THEN** those roots are included in the derived storefront family list

#### Scenario: Proxy emits an insecure next link
- **WHEN** the configured API base uses `https` and pagination returns an `http` next link for the same host
- **THEN** the storefront requests that page over `https` and completes category loading
