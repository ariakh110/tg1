## ADDED Requirements

### Requirement: Product List Grouped by Grade
The product price list SHALL group products by steel grade and product form, rendering one titled section per comparable group (for example, «CK45 · ورق فابریک»), with grade-less products under a «سایر گریدها» section. Each row SHALL still display its factory and delivery/seller, so grouping does not hide that information.

#### Scenario: Multiple grades under one factory
- **WHEN** a category contains products of several grades from the same factory
- **THEN** the list shows a separate titled section per grade rather than one section per factory

#### Scenario: One grade has multiple product forms
- **WHEN** a grade contains factory sheets, cut sheets, or coils
- **THEN** each form is rendered as a separate comparable price group

#### Scenario: Grade-less products
- **WHEN** a product has no steel grade set
- **THEN** it appears under the «سایر گریدها» section

### Requirement: Complete Filtered Product List
The public price list SHALL render every active product matching the selected category, type, form, search, and ordering in one continuous view without end-user pagination controls. Backend pagination MAY remain in place, but the storefront MUST retrieve all backend pages before constructing the displayed groups.

#### Scenario: CK45 thicknesses span backend pages
- **WHEN** matching CK45 factory-sheet products from 8 mm through 30 mm span more than one backend response page
- **THEN** all matching thicknesses appear in the same CK45 factory-sheet section
- **AND** no previous, next, or page-number controls are shown

#### Scenario: Visitor changes a filter
- **WHEN** the visitor changes category, type, form, search, or ordering
- **THEN** the storefront retrieves and displays all products matching the new filter state

### Requirement: Market Comparison Uses Comparable Group Average
Each priced row's market comparison SHALL use the arithmetic mean of positive current best prices in the same displayed steel-grade and product-form group. Products with no positive price MUST be excluded from the mean. Category-wide prices from other grades or forms MUST NOT affect the row percentage.

#### Scenario: CK45 and ST37 prices differ
- **WHEN** CK45 factory sheets and ST37 products are visible in the same category
- **THEN** each CK45 row is compared only with priced CK45 factory-sheet rows
- **AND** ST37 prices do not affect the CK45 percentage

#### Scenario: Group contains inquiry-only products
- **WHEN** one or more products in a group have no positive price
- **THEN** those inquiry-only products are excluded from the group's arithmetic mean
