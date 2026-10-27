## ADDED Requirements

### Requirement: Generate selectable product combinations
The product admin SHALL generate at most 100 distinct sheet/coil combinations from shared backend taxonomy and positive thickness/width axes, and fixed or over-threshold lengths for sheets. Coil combinations SHALL omit lengths. Each selected combination SHALL have its own optional positive price and existing availability status.

#### Scenario: Two Kavian thickness-30 variants
- **WHEN** width is shared and lengths are fixed 6000 and over 7000 millimetres
- **THEN** two distinct products and prices are previewed and created

#### Scenario: Spreadsheet prices and deselection
- **WHEN** the operator pastes prices into the table and deselects unavailable combinations
- **THEN** pasted values affect only addressed rows and deselected rows are excluded from submission

### Requirement: Safe server validation and atomic creation
Both endpoints SHALL require product-admin authorization and reject unknown fields and invalid numeric values. Preview SHALL write no records. Commit SHALL revalidate and atomically create selected products with audit logs, or leave no writes. Existing physical identities, including inactive entries, SHALL be skipped without changing price or availability. Repeated submission SHALL not duplicate products.

#### Scenario: Existing product and repeated submit
- **WHEN** an equivalent physical identity already exists or the same matrix is submitted again
- **THEN** it is reported as existing and its values remain unchanged

#### Scenario: Invalid row or late write failure
- **WHEN** a row is invalid or a later write fails
- **THEN** the batch leaves no partial products, offers, prices or audit rows

#### Scenario: Preview and permission denial
- **WHEN** preview is requested by an authorized operator
- **THEN** no product, seller, offer, price or audit record is written
- **WHEN** an unauthorized user requests preview or commit
- **THEN** access is denied
