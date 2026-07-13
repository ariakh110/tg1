## Context

`ProductCategory.product_kind` and `ProductAttributeOption.product_kind` are already free string fields. The backend already resolves category defaults and validates options within any non-empty kind. The missing constraint is entirely in the frontend, where selectors and navigation use a fixed six-item array.

## Decisions

### Root category is the custom-kind definition

A custom kind is created together with a root category. The root category name is its Persian display label, while `product_kind` stores a stable lowercase technical code such as `angle`. Child categories inherit the selected parent's kind.

This avoids a parallel product-kind table and keeps the visible catalog hierarchy as the source of truth.

### Built-in kinds remain field templates

The built-in sheet, rebar, profile, pipe, beam, and billet kinds retain their specialized field behavior. A custom kind uses a generic form: all common dimensions remain optional, and controlled specification inputs appear when options for that custom kind have been configured.

### Dynamic admin choices

The admin combines built-in templates with unique kind codes discovered from category API data. After creating a custom root, the same kind becomes available in the controlled-option form without another deployment.

### Dynamic public navigation

Header, mobile menu, and homepage tiles use `/categories/active-with-products/`. Known built-in roots keep their dedicated `/category/<family>` landing hubs. New roots link to `/products?family=<category-code>` so they work without a hard-coded landing page.

## Validation

- A new custom kind code is required and limited to lowercase ASCII letters, digits, hyphens, and underscores.
- Duplicate kind codes must be selected from the existing list instead of recreated.
- Selecting a parent category forces inheritance of the parent's product kind.
- Custom products continue to use existing backend option validation and category spec defaults.
