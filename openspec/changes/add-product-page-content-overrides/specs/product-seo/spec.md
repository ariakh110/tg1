## ADDED Requirements

### Requirement: Hybrid Product Content
Every active product page SHALL render a differentiated server-side content layer generated from its real structured facts. An administrator SHALL be able to override the SEO title, meta description, H1, short description, full content, FAQ, related products, and index mode while editing an existing product. Empty overrides SHALL fall back independently to automatic values.

#### Scenario: Automatic content
- **WHEN** a product has no substantive manual description
- **THEN** its initial HTML contains an H1, introduction, technical facts, applicable theoretical weight, price factors, inquiry guidance, relevant form guidance, links, and FAQ derived from that product
- **AND** products with different grades, dimensions, factories, or forms do not receive identical full copy

#### Scenario: Manual override
- **WHEN** an administrator saves dedicated page content for a product
- **THEN** the public page uses the saved fields where present and automatic fallbacks for fields left empty
- **AND** the product URL and self-canonical remain unchanged and non-editable

### Requirement: Edit-Only Product SEO Controls
The normal product edit workflow SHALL contain a collapsible "Product page content and SEO" section with a pre-save preview. Quick product registration SHALL NOT display or submit those controls.

#### Scenario: Edit an existing product
- **WHEN** an administrator selects Edit for an existing product
- **THEN** the administrator can edit content fields, add or remove FAQ rows, select multiple related products, choose auto/index/noindex, and preview the effective page before saving

#### Scenario: Quick registration
- **WHEN** an administrator opens quick product registration
- **THEN** the content and SEO controls are absent
- **AND** product creation uses automatic page content defaults

### Requirement: Content Isolation From Price Import
Price-only, bulk-price, and Excel update workflows SHALL NOT overwrite product content, FAQ, SEO fields, related products, or index mode unless a dedicated page-content update is explicitly submitted.

#### Scenario: Blank content columns in price import
- **WHEN** an existing product price is updated and content values are omitted or blank
- **THEN** all existing page-content and SEO values remain byte-for-byte unchanged

### Requirement: Product Index Policy
Each product SHALL support `auto`, `index`, and `noindex` modes. Inactive products SHALL always be excluded from search. For active products, `auto` SHALL produce `noindex,follow` for materially incomplete products and `index,follow` for products with enough structured information to provide independent value.

#### Scenario: Low-information product
- **WHEN** a product uses auto mode and lacks sufficient category/specification/content information
- **THEN** metadata emits `noindex,follow`

#### Scenario: Explicit decision
- **WHEN** an administrator selects index or noindex for an active product
- **THEN** that explicit setting controls robots metadata without changing canonical

#### Scenario: Inactive product
- **WHEN** a product is inactive
- **THEN** it remains excluded from search and Sitemap even if its saved index mode is `index`

#### Scenario: Sitemap policy
- **WHEN** a product's effective decision is noindex or the product is inactive
- **THEN** its canonical product URL is omitted from Sitemap

## MODIFIED Requirements

### Requirement: Server-Rendered Product Landing
Each product detail page SHALL place one effective H1 before all H2 headings and SHALL render the H1, introduction, long-form content, internal links, and FAQ in the initial HTML. Metadata SHALL use manual overrides when present and deterministic product-derived fallbacks otherwise. The word "today" SHALL appear in an effective title only when a public price was verified on the current Tehran date.

#### Scenario: Initial HTML ordering
- **WHEN** a crawler requests a product URL
- **THEN** the initial response contains the effective H1 before every H2 and contains the effective product content without executing JavaScript

#### Scenario: Unverified price title
- **WHEN** the product has no price verified on the current Tehran date
- **THEN** its effective title does not claim the price is for today

### Requirement: Product Structured Data
Each product page SHALL emit Product and BreadcrumbList JSON-LD. Offer JSON-LD SHALL be emitted only when the exact active, in-stock price is visible on the page and was verified on the current Tehran date. A Toman price SHALL be converted to IRR by multiplying by ten. FAQPage JSON-LD SHALL match the FAQ visibly rendered on the page.

#### Scenario: Verified visible offer
- **WHEN** an active in-stock price tier was verified today in Tehran and is shown publicly
- **THEN** Product JSON-LD contains an Offer with `priceCurrency` equal to `IRR` and price equal to the visible Toman value multiplied by ten

#### Scenario: Missing or stale price
- **WHEN** no active price tier was verified today or the product is not in stock
- **THEN** the detail, buy, cart, and checkout workflow presents an inquiry without the stale amount
- **AND** Product JSON-LD omits Offer
