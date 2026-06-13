## MODIFIED Requirements

### Requirement: Bulk Product Price Update
Admins SHALL update the «قیمت روز» of many products at once, via either a prefilled Excel round-trip or an inline admin table. To keep products distinguishable, both surfaces SHALL show each product's steel grade and city alongside its price. The Excel template SHALL export every active product with its current price and SHALL prefill readable identity columns (alloy, city, dimensions, type, surface, factory, availability) that are display-only — marked so the importer ignores them — while the importable columns remain id, name, category code, seller id, and new price. The inline table SHALL accept a list of `{product_id, price}` pairs and apply each to the product's day price, defaulting the seller to the store (direct-sales) when none exists, and SHALL NOT create new products. Re-uploading the template SHALL change only the price: blank cells SHALL NOT clear any existing field, and updating a price SHALL preserve the price tier's condition label and dimensions and the offer's delivery details.

#### Scenario: Download readable template
- **WHEN** an admin downloads the price template
- **THEN** each active product appears with its id, name, category code, seller id, current price, and read-only identity columns (alloy, city, dimensions, type, surface, factory, availability) filled in

#### Scenario: Safe price-only re-upload
- **WHEN** an admin edits only the price column and re-uploads the template
- **THEN** each product's day price is updated and no other field is changed — specifications, the price tier's condition label and dimensions, and delivery details are all preserved

#### Scenario: Display-only columns ignored
- **WHEN** the uploaded file contains the «نمایش:»-prefixed identity columns
- **THEN** the importer does not map them to any field and leaves the corresponding product data untouched

#### Scenario: Save inline price edits
- **WHEN** an admin submits changed prices as `{prices:[{product_id, price}]}`
- **THEN** each product's «قیمت روز» is updated, the store seller is used when the product has no seller, and the response reports the count of updated prices

#### Scenario: Grade and city visible in the table
- **WHEN** an admin opens the inline bulk-price table
- **THEN** each row shows the product's steel grade and city next to its current and new price
