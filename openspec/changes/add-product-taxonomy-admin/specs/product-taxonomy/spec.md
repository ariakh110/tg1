## ADDED Requirements

### Requirement: Backend-driven product taxonomy

The system SHALL source product categories and controlled product options from backend APIs rather than static frontend arrays.

#### Scenario: Admin opens product creation form

- **GIVEN** the admin dashboard is opened by an authorized admin
- **WHEN** product metadata loads
- **THEN** main categories SHALL come from `/api/categories/`
- **AND** sellers SHALL come from `/api/sellers/`
- **AND** controlled options SHALL come from `/api/attribute-options/`
- **AND** the product form SHALL use these values for searchable dropdowns.

### Requirement: Dependent sheet taxonomy

The system SHALL enforce dependencies between sheet manufacturing process, sheet type, grade, and factory.

#### Scenario: Admin selects sheet product

- **GIVEN** the admin selects a category whose resolved product kind is `sheet`
- **WHEN** the product form is displayed
- **THEN** the admin SHALL choose `manufacturing_process`
- **AND** the admin SHALL choose `surface_finish`
- **AND** grade options SHALL be filtered by the selected `surface_finish`
- **AND** factory options SHALL be filtered by the selected `manufacturing_process`.

#### Scenario: Admin selects coil

- **GIVEN** the admin selects `manufacturing_process=coil`
- **WHEN** the product is submitted
- **THEN** length SHALL not be required
- **AND** cut type SHALL not be required
- **AND** the backend SHALL clear or ignore length for coil products.

#### Scenario: Admin selects sheet

- **GIVEN** the admin selects `manufacturing_process=sheet`
- **WHEN** the product is submitted
- **THEN** thickness, width, length, factory, surface finish, grade, and cut type SHALL be required.

### Requirement: Public product categories reflect active inventory

The system SHALL expose public category/type choices only when matching active products exist.

#### Scenario: Public product list loads

- **GIVEN** active products exist under category `sheet`
- **WHEN** `/api/categories/active-with-products/` is requested
- **THEN** the response SHALL include the active root category
- **AND** include only active child categories/types with matching active products
- **AND** exclude categories/types with no active products.

### Requirement: Admin product inventory includes inactive products

The admin product list SHALL allow admins to view active, inactive, or all products.

#### Scenario: Admin deactivates a product

- **GIVEN** an active product is visible in the admin product list
- **WHEN** the admin deactivates it
- **THEN** the product SHALL be hidden from the public product list
- **AND** the product SHALL remain visible in the admin list when the filter is `all` or `inactive`
- **AND** a product audit log SHALL be created.

### Requirement: Taxonomy management panel

The admin dashboard SHALL provide a dedicated panel for managing product taxonomy.

#### Scenario: Admin creates a taxonomy option

- **GIVEN** the admin is on the taxonomy panel
- **WHEN** the admin creates a new controlled option
- **THEN** the form SHALL require label and stable value
- **AND** require parent selection for options that need it, such as factory and city
- **AND** refresh the option list after success.

#### Scenario: Admin reviews existing taxonomy

- **GIVEN** product categories and options exist
- **WHEN** the admin opens the taxonomy panel
- **THEN** categories SHALL be displayed with parent path, product kind, active state, and code
- **AND** options SHALL be grouped by purpose with label, value, product kind, parent label, and active state.

### Requirement: Product price import template

The system SHALL provide an Excel template for product creation and price updates.

#### Scenario: Admin downloads template

- **GIVEN** the admin requests the product import template
- **WHEN** the backend returns the file
- **THEN** the file SHALL contain headers for product id, name, category code, seller id, price, grade, manufacturing process, surface finish, factory, cut type, dimensions, availability, province, city, and address
- **AND** include sample rows that demonstrate sheet and non-sheet products.
