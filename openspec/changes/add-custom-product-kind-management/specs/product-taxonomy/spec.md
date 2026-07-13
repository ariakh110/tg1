## ADDED Requirements

### Requirement: Admin can define a custom product kind
The taxonomy admin SHALL allow an authorized operator to create a root category with a new stable product-kind code without changing application code. Saved custom kinds SHALL become selectable for controlled taxonomy options and subsequent category operations. Child categories SHALL inherit their parent's product kind.

#### Scenario: Admin creates a new angle kind
- **GIVEN** the admin is creating a root category
- **WHEN** the admin enters the category name `نبشی`, selects new product kind, and enters code `angle`
- **THEN** the category SHALL be saved with `product_kind=angle` and `material_type=angle` defaults
- **AND** `نبشی` SHALL appear as a product-kind choice in controlled-option management

#### Scenario: Admin creates a child category
- **GIVEN** a root category uses custom product kind `angle`
- **WHEN** the admin creates a child under that root
- **THEN** the child SHALL inherit `angle` and SHALL NOT define an unrelated kind

### Requirement: Custom product kinds support generic product registration
The admin product form SHALL preserve common dimensions for a custom kind and SHALL show controlled process, surface, grade, factory, and cut inputs when active options have been defined for that kind. Existing specialized behavior for built-in kinds SHALL remain unchanged.

#### Scenario: Admin registers a custom-kind product
- **GIVEN** an active `angle` category and an active `angle` grade option exist
- **WHEN** the admin registers an angle product with grade and dimensions
- **THEN** the product specification SHALL retain `material_type=angle`, the selected grade, and supplied dimensions

### Requirement: Storefront navigation includes backend-created product kinds
The desktop header, mobile category menu, and homepage category tiles SHALL derive visible families from active backend categories that have active products. Built-in families MAY use dedicated landing hubs; custom families SHALL link to the product list filtered by their category code.

#### Scenario: Custom kind receives its first active product
- **GIVEN** a custom root category has at least one active product
- **WHEN** storefront category navigation is loaded
- **THEN** the custom category SHALL be visible and SHALL link to its filtered product list

#### Scenario: Custom kind has no active products
- **GIVEN** a custom root category has no active products
- **WHEN** storefront category navigation is loaded
- **THEN** that category SHALL NOT be shown publicly
