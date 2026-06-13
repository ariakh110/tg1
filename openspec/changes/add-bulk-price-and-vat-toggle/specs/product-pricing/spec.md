## ADDED Requirements

### Requirement: Bulk Product Price Update
Admins SHALL update the «قیمت روز» of many products at once, via either a prefilled Excel round-trip or an inline admin table. The Excel template SHALL export every active product with its current price so the operator edits prices in place rather than rebuilding the sheet; its headers SHALL stay identical to the upload parser's expected columns. The inline table SHALL accept a list of `{product_id, price}` pairs and apply each to the product's day price, defaulting the seller to the store (direct-sales) when none exists, and SHALL NOT create new products.

#### Scenario: Download prefilled template
- **WHEN** an admin downloads the price template
- **THEN** the file contains one row per active product with its id, name, category code, seller id, and current price, using the same headers the bulk upload accepts

#### Scenario: Save inline price edits
- **WHEN** an admin submits changed prices as `{prices:[{product_id, price}]}`
- **THEN** each product's «قیمت روز» is updated, the store seller is used when the product has no seller, and the response reports the count of updated prices

#### Scenario: No valid prices submitted
- **WHEN** the submitted price list is empty or contains no valid entries
- **THEN** the request is rejected with a 400 and no prices change

### Requirement: VAT Display Toggle on Product List
The product list page SHALL provide an «ارزش افزوده» (value-added tax) toggle that defaults to OFF. When OFF, all displayed prices on the list — product rows, group starting prices, and the hero/market-average figures — SHALL be shown 10% lower (×0.9). When ON, full prices SHALL be shown. The toggle state SHALL persist across visits, and market-comparison percentages (ratios) SHALL be unaffected. The toggle SHALL affect only the product list page, not detail, category, or landing pages.

#### Scenario: Default off shows pre-tax prices
- **WHEN** a visitor opens the product list without changing the toggle
- **THEN** the toggle is off and all list prices are displayed at 90% of the stored price

#### Scenario: Enabling the toggle shows full prices
- **WHEN** the visitor enables «ارزش افزوده»
- **THEN** all list prices are displayed at the full stored value, and the choice persists on the next visit

#### Scenario: Scope limited to the list
- **WHEN** the toggle is off and the visitor opens a product detail, category, or landing page
- **THEN** those pages display full prices, unaffected by the list toggle
