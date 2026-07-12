## ADDED Requirements

### Requirement: Admin can edit product categories

The system SHALL allow authorized admins to edit product category metadata from the custom admin dashboard.

#### Scenario: Admin updates a category label

- **GIVEN** an authorized admin is on the taxonomy panel
- **WHEN** the admin edits a category name and submits
- **THEN** the category SHALL be updated in the backend
- **AND** product records linked to the category SHALL remain linked
- **AND** an audit event SHALL be recorded.

#### Scenario: Admin deactivates a category

- **GIVEN** a category exists and may have products
- **WHEN** the admin deactivates the category
- **THEN** the category SHALL remain in the database
- **AND** public category/type endpoints SHALL exclude it
- **AND** admin taxonomy tables SHALL still show it as inactive
- **AND** an audit event SHALL be recorded.

### Requirement: Admin can edit controlled taxonomy options

The system SHALL allow authorized admins to edit controlled product option metadata from the custom admin dashboard.

#### Scenario: Admin updates an option label

- **GIVEN** a controlled option exists
- **WHEN** the admin edits the display label
- **THEN** future dropdowns SHALL show the new label
- **AND** existing product specification values SHALL remain valid
- **AND** an audit event SHALL be recorded.

#### Scenario: Admin deactivates an option

- **GIVEN** a controlled option exists
- **WHEN** the admin deactivates the option
- **THEN** the option SHALL remain visible in admin taxonomy management
- **AND** product creation/update dropdowns SHALL exclude the inactive option
- **AND** new product writes using that inactive option SHALL be rejected
- **AND** existing product detail/list displays SHALL still render legacy values safely.

### Requirement: Taxonomy dependencies remain valid

The system SHALL enforce parent dependency rules for taxonomy options and product writes.

#### Scenario: Admin creates or edits a factory option

- **GIVEN** the admin selects option group `factory`
- **WHEN** the admin submits the option
- **THEN** the option SHALL require a `manufacturing_process` parent.

#### Scenario: Admin creates or edits a sheet grade option

- **GIVEN** the admin selects option group `steel_grade` and product kind `sheet`
- **WHEN** the admin submits the option
- **THEN** the option SHALL require a `surface_finish` parent.

#### Scenario: Product write uses wrong grade for sheet type

- **GIVEN** a product write selects a sheet type
- **WHEN** the selected grade is not parented by that sheet type
- **THEN** the backend SHALL reject the write with a validation error.

### Requirement: Admin can see taxonomy usage impact

The system SHALL show admins how category and option changes affect existing products.

#### Scenario: Category has products

- **GIVEN** a category has products under itself or descendants
- **WHEN** the taxonomy table is shown
- **THEN** the category row SHALL show a product usage count or impact hint.

#### Scenario: Option is used by products

- **GIVEN** an option value is stored on product specifications
- **WHEN** the taxonomy table is shown
- **THEN** the option row SHALL show a product usage count or impact hint.

### Requirement: Public product list is grade/form-grouped, complete, and active-only

The public product list SHALL render every matching active product through backend-driven category/type filters and steel-grade/product-form grouping. Factory, origin, and seller information SHALL remain visible per row.

#### Scenario: Visitor selects sheet category

- **GIVEN** active sheet products exist
- **WHEN** the visitor opens `/products?family=sheet`
- **THEN** type tabs SHALL be derived from backend data with active products
- **AND** product rows SHALL be grouped by steel grade and product form
- **AND** every matching row SHALL be shown without public pagination controls
- **AND** inactive products SHALL be excluded.

#### Scenario: Product has no price

- **GIVEN** an active product has no current price
- **WHEN** the product row is rendered
- **THEN** the row SHALL show inquiry/contact action if availability is inquiry or in stock without price.

#### Scenario: Product is out of stock

- **GIVEN** a product has availability `out_of_stock`
- **WHEN** the product row is rendered
- **THEN** the row SHALL show a register-order/request action instead of a buy action.

### Requirement: Public list filters remain stable

The product list SHALL preserve category, type, form, search, and ordering filters through URL query parameters while retrieving every backend page internally.

#### Scenario: Visitor changes type tab

- **GIVEN** the visitor has filters selected
- **WHEN** the visitor selects a different type tab
- **THEN** the new category/type/filter state SHALL be represented in the URL
- **AND** all products matching that state SHALL be displayed.

#### Scenario: Results span multiple backend pages

- **GIVEN** filters are selected
- **WHEN** matching products span multiple paginated API responses
- **THEN** the storefront SHALL retrieve every response page
- **AND** no previous, next, or page-number controls SHALL be rendered.
