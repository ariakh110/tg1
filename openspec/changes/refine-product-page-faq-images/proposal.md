# Change: Refine product FAQ and image management

## Why

Product FAQs do not expose a clear expand control and render collapsed, while generated Persian product names can place the surface label before the family label. Product images already exist in the API, but administrators have no practical image workflow in the product edit form.

## What Changes

- Render every product FAQ expanded initially with a visible expand/collapse chevron.
- Generate compound Persian product labels in family-first order, including safe handling of labels that already contain the family name.
- Add edit-only product image management for multi-file upload, featured-image selection, and deletion.
- Keep exactly one featured image per product and return that image first for storefront galleries, metadata, and structured data.

## Impact

- Affected specs: `product-seo`
- Affected code: product SEO helpers and SSR content, product admin editor, product image serializer/view/model, product image tests
- Database: model ordering metadata only; no product data rewrite

