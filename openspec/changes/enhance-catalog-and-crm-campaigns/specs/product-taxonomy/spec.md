## ADDED Requirements

### Requirement: Category Visual Identity
The taxonomy SHALL let an authorized admin select a stable curated icon and optionally upload a PNG, JPEG, or WebP image for each product category. An uploaded image SHALL take precedence over the curated icon, and the storefront SHALL use a safe product-domain fallback when neither is available.

#### Scenario: Admin selects a curated icon
- **WHEN** an admin saves a category with a supported icon key and no image
- **THEN** public category cards render the corresponding icon

#### Scenario: Admin uploads a category image
- **WHEN** an admin uploads a valid category image
- **THEN** the image is stored and rendered instead of the curated icon

#### Scenario: Unsafe or oversized image is submitted
- **WHEN** an upload is an unsupported format or exceeds the configured size limit
- **THEN** the API rejects it with a validation error and preserves the current category visual

### Requirement: Independent Category Navigation Visibility
The taxonomy SHALL let an authorized admin show or hide each root category in the homepage, desktop header, and mobile category navigation independently of the category's operational `is_active` state. Hiding navigation SHALL NOT deactivate products or remove the category's direct URL.

#### Scenario: Admin hides a root category card
- **WHEN** an admin disables public-navigation visibility for a root category
- **THEN** the category is omitted from homepage, desktop, and mobile category navigation
- **AND** its products and direct category URL remain available

#### Scenario: Admin restores category visibility
- **WHEN** the admin enables public-navigation visibility again
- **THEN** the category returns to every public category navigation surface
