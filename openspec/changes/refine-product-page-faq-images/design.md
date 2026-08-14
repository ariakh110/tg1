## Context

The storefront uses nested `ProductImage` records for its gallery and chooses the first image for metadata. The API currently permits multiple featured images and does not guarantee featured-first ordering. The product content editor is already intentionally limited to existing products, making it the appropriate place for image management without expanding quick product creation.

## Goals / Non-Goals

- Goals: clear FAQ interaction, correct Persian product word order, practical image administration, and deterministic primary-image behavior.
- Non-goals: shared media-library reuse for product images, image cropping, or changing product URLs.

## Decisions

- The public FAQ continues to use native `details` elements for keyboard and browser accessibility. Each item receives the `open` attribute initially and a Lucide chevron that rotates with the native open state.
- Product identity text is assembled as family then surface. If the surface label already contains the family label, it is treated as the complete identity and is not duplicated.
- Image controls live at the start of the existing edit-only product content accordion. Uploads use the current authenticated `/product-images/` endpoint.
- The serializer makes the first image featured automatically and atomically clears the previous featured flag when another image is selected. Model ordering places featured images first. Deleting the featured image promotes the next remaining image.

## Risks / Trade-offs

- Existing products with more than one featured image are not rewritten by the migration. The next create or featured-image update normalizes that product, and deterministic ordering still keeps featured records first.
- Product uploads remain independent from the article media library so deleting a product image cannot break article content.

## Migration Plan

Apply the model-options migration, deploy backend and frontend together, and use the product edit form to normalize the featured image on existing products as needed.

