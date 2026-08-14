## ADDED Requirements

### Requirement: Accessible Product FAQ Disclosure

Each product FAQ item SHALL expose a visible expand or collapse control and SHALL be expanded in the initial server-rendered page while remaining individually collapsible.

#### Scenario: Visitor opens a product page with FAQ
- **WHEN** a product page contains automatic or authored FAQ items
- **THEN** every answer is visible initially and each question displays a chevron that reflects its current disclosure state

### Requirement: Natural Persian Product Identity

Automatic product headings and descriptions SHALL place the product family before its surface or subtype and SHALL avoid repeating the family when an option label already contains it.

#### Scenario: Surface is stored as an adjective
- **WHEN** a sheet product has family `ورق` and surface label `سیاه`
- **THEN** its automatic identity contains `ورق سیاه` and does not contain `سیاه ورق`

#### Scenario: Surface already includes the family
- **WHEN** a sheet product has family `ورق` and surface label `ورق سیاه`
- **THEN** its automatic identity contains one occurrence of `ورق سیاه`

### Requirement: Product Image Administration

An authorized administrator editing an existing product SHALL be able to upload one or more product images, choose one primary image, and delete images. The quick-create form SHALL remain unchanged.

#### Scenario: First product image is uploaded
- **WHEN** an authorized user uploads an image to a product with no images
- **THEN** the image is stored as the primary image and is shown first in product API responses

#### Scenario: Administrator changes the primary image
- **WHEN** an authorized user marks another product image as primary
- **THEN** all other images for that product are unfeatured and the selected image becomes first in product API responses

#### Scenario: Primary image is deleted
- **WHEN** the primary image is deleted from a product that still has images
- **THEN** the next remaining image is promoted as primary and storefront image selection remains deterministic
