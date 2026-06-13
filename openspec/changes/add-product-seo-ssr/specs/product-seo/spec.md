## ADDED Requirements

### Requirement: Server-Rendered Product Landing
Each product detail page SHALL be server-rendered so its name, key specs, price, and metadata are present in the initial HTML. The route SHALL export `generateMetadata` producing a title in the form «قیمت {name} امروز + خرید مستقیم — {siteName}», a description, a canonical URL, and Open Graph tags. Interactive UI (image gallery, price refresh) MAY remain a client island seeded with the server-fetched product.

#### Scenario: Metadata in initial HTML
- **WHEN** a crawler requests `/products/<id>`
- **THEN** the response HTML contains a `<title>` with the product name and a canonical `<link>`
- **AND** the product name and specs are present without executing JavaScript

#### Scenario: Missing product
- **WHEN** the product id does not exist
- **THEN** the page responds as not-found and the metadata title is «محصول پیدا نشد | {siteName}»

### Requirement: Product Structured Data
Each product page SHALL emit JSON-LD `Product` with an `Offer` (priceCurrency `IRR`, lowest active tier price, availability, `priceValidUntil` = end of the current day) when a price exists, plus a `BreadcrumbList`. The site SHALL emit `Organization` JSON-LD once globally.

#### Scenario: Product + Offer schema
- **WHEN** a product has at least one active priced tier
- **THEN** the page includes a `Product` JSON-LD block with an `Offer` whose `priceCurrency` is `IRR` and `availability` reflects stock status

#### Scenario: Breadcrumb + Organization
- **WHEN** any product page renders
- **THEN** it includes a `BreadcrumbList` (خانه › محصولات › {product}) and the site root includes `Organization` data with the configured site name, phone, and address

### Requirement: Product Sitemap Coverage
`/sitemap.xml` SHALL list every product URL and the product family routes in addition to the static pages and blog entries.

#### Scenario: Products in sitemap
- **WHEN** `/sitemap.xml` is generated
- **THEN** it contains a URL entry for each product and for each product family
