# Change: Hybrid product-page content and SEO overrides

## Why
Product detail pages currently expose only a short, mostly repeated description and derive all metadata from the product name. Important products cannot receive dedicated content, FAQ, related-product links, or an explicit indexing decision, while unverified prices are presented as current and can enter structured data.

## What Changes
- Add optional product-page overrides for SEO title, meta description, H1, short description, full HTML content, FAQ, related products, and index mode.
- Keep quick product creation unchanged; expose the new controls only while editing an existing product.
- Generate useful SSR content from structured product facts whenever an override is empty.
- Add a pre-save preview to the product editor.
- Track price verification time and use "today" and Offer schema only for a price verified on the current Tehran date.
- Keep product URLs and automatic self-canonical behavior unchanged.
- Preserve content and SEO fields during price-only and Excel updates.
- Seed the T006 content for the existing 10 mm ST37 cut-sheet product without changing its URL.

## Impact
- Affected specs: `product-seo`
- Backend: `products` model, serializers, admin import, API response, migrations, tests.
- Frontend: admin product editor, product metadata/schema, SSR content, product detail presentation, tests.
- Deployment: backend migration plus frontend rebuild. Existing prices without a verification timestamp fall back to inquiry until refreshed through the normal price update workflow.
