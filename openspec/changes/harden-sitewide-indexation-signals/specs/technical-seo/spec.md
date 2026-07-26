## ADDED Requirements

### Requirement: Complete Metadata for Public Routes

Every indexable public route in the static sitemap SHALL emit a unique title, meta description, self-referencing canonical URL, Open Graph metadata, and `index,follow` in the initial HTML.

#### Scenario: Sale hall metadata is complete
- **WHEN** a crawler requests `/sale-hall`
- **THEN** the initial HTML contains a sale-hall-specific title and description
- **AND** canonical points to `/sale-hall`
- **AND** robots permits indexing and following

#### Scenario: Products HTML exposes its primary heading
- **WHEN** a crawler requests `/products` without executing client JavaScript
- **THEN** the initial HTML contains the products page H1
- **AND** canonical points to `/products`

### Requirement: Product Family Query Consolidation

The product price board SHALL canonicalize an active or established `family` query to the matching `/category/<family>` hub while preserving the filtered user interface.

#### Scenario: Established family query
- **WHEN** `/products?family=rebar` is requested
- **THEN** the page remains usable as a filtered catalog
- **AND** its canonical URL is `/category/rebar`

#### Scenario: Non-family product filters
- **WHEN** `/products` is requested with a search or ordering parameter but no recognized family
- **THEN** canonical points to `/products` without a query string

### Requirement: Non-Indexable Workflow Routes

Product purchase routes SHALL emit `noindex,follow`. Authentication, account, admin, cart, checkout, private order, and offer routes SHALL emit `noindex,nofollow`. These routes SHALL remain crawlable through robots.txt so crawlers can observe the directives.

#### Scenario: Product purchase route
- **WHEN** a crawler requests `/products/<id>/buy?intent=buy`
- **THEN** the initial HTML includes `noindex,follow`
- **AND** robots.txt does not disallow the purchase route

#### Scenario: Authentication and account routes
- **WHEN** a crawler requests `/auth/login` or `/account/dashboard`
- **THEN** the initial HTML includes `noindex,nofollow`
- **AND** robots.txt does not disallow `/auth/` or `/account/`

### Requirement: Canonical-Only Sitemap

The sitemap SHALL contain only same-origin, query-free, unique, indexable canonical URLs and SHALL exclude transactional and private route patterns.

#### Scenario: Sitemap is inspected
- **WHEN** `/sitemap.xml` is generated
- **THEN** no URL contains a query string or fragment
- **AND** no URL targets auth, account, admin, checkout, cart, offer, private order detail, or product buy routes
- **AND** duplicate canonical URLs occur only once

### Requirement: Substantive Product Family Hubs

Each product family hub SHALL render its matching product summaries in server HTML, including links and price or enquiry state, and SHALL publish a matching Product ItemList when products exist.

#### Scenario: Family has products
- **WHEN** `/category/<family>` resolves products
- **THEN** all fetched product summaries are visible without pagination
- **AND** each product links to its canonical product detail URL
- **AND** the page contains no 'coming soon' placeholder

#### Scenario: Family has no public price
- **WHEN** no active product price exists for a family
- **THEN** the page shows a current enquiry action
- **AND** it does not promise future content using a thin placeholder
