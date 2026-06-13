## ADDED Requirements

### Requirement: Family Category Landing
Each product family (sheet, rebar, beam, pipe, profile, billet) SHALL have a server-rendered landing at `/category/<family>` with its own metadata (title «قیمت روز {family} + خرید عمده — {siteName}», description, canonical), a `BreadcrumbList` and `ItemList` JSON-LD, a server-rendered grid of that family's products, and a link to the full filterable `/products?family=<family>`. The family→products query SHALL reuse the existing `category_code`/`product_kind` API filters; the `/products` list page and its filters SHALL be unchanged.

#### Scenario: Category landing renders products
- **WHEN** a crawler requests `/category/sheet`
- **THEN** the response HTML contains the family title in `<h1>`, a product grid, and an `ItemList` JSON-LD without executing JavaScript

#### Scenario: Unknown family
- **WHEN** the family segment is not one of the known families
- **THEN** the page responds as not-found

### Requirement: Slug Product URLs
Products SHALL be reachable by slug at `/products/<slug>` in addition to the numeric id. The detail API (`/api/products/<id-or-slug>/`) SHALL resolve either form. The product detail canonical, its structured-data URLs, product cards, and the sitemap SHALL use the slug URL; numeric URLs SHALL still resolve and point their canonical to the slug.

#### Scenario: Resolve by slug
- **WHEN** `/products/<slug>` is requested
- **THEN** the correct product page renders with the canonical set to the slug URL

#### Scenario: Numeric still works
- **WHEN** `/products/<numeric-id>` is requested
- **THEN** the product page renders and its canonical points to the slug URL
