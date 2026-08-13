# PRD: Hybrid Product Page Content And SEO

## Objective
Increase the independent search value and conversion usefulness of every product detail page while allowing priority products to receive editorially controlled content. The feature applies to all product families and thicknesses, not only the T006 10 mm example.

## Operator Workflow
1. Create products with the existing quick form; no new fields are shown.
2. Open Edit on a saved product.
3. Expand "Product page content and SEO".
4. Optionally override title, description, H1, short copy, full content in visual Editor.js or HTML mode, FAQ, related products, and index policy.
5. Preview the effective automatic/manual result before saving.
6. Update prices through the existing single or bulk workflow; content remains untouched.

## Automatic Page Contract
- Build copy from product name, family, form, grade, thickness, dimensions, factory, cut type, availability, and related products.
- Show a theoretical unit weight only when a stored weight or a valid family-specific calculation is available.
- Explain relevant price factors and the facts required for inquiry.
- Link to the canonical category/grade and selected related products.
- Generate product-specific FAQ rather than copying one fixed FAQ to every page.

## SEO Contract
- Preserve the current product slug and compute a non-editable self-canonical.
- Render one H1 before H2 headings in initial server HTML.
- Use `auto/index/noindex`; automatic low-value pages become `noindex,follow`.
- Use "today" only with a price verified during the current Tehran date.
- Emit Offer only for the same fresh price visible to the user; schema currency is IRR and UI currency is Toman.
- Keep content, SEO, FAQ, relations, and index choices unchanged during price imports.
- Exclude effective-noindex products from Sitemap, including inactive products even if an old manual index choice remains.
- Keep stale prices out of the detail page, buy flow, cart, checkout, metadata claims, and Offer schema; those orders follow the inquiry workflow until price refresh.

## Deployment Runbook
1. Upload and apply the backend release first.
2. Run Django migrations; migration `0018` adds fields and migration `0019` seeds the T006 10 mm content without changing its slug.
3. Confirm `/api/products/<slug>/` includes the SEO fields and `price_verified_at`.
4. Upload and apply the frontend release.
5. Refresh valid prices through the normal single/bulk/Excel price workflow. Historical tiers intentionally remain hidden until this write records a verification timestamp for the current Tehran date.
6. Check one fresh-price product and one inquiry product: visible amount, title wording, JSON-LD Offer, and buy/cart behavior must agree.
7. Confirm Sitemap excludes manually noindexed and automatic low-information products.

## T006 Seed
The existing URL `/products/ورق-سیاه-برشی-10-میل-مبارکه` receives the supplied T006 title, meta description, H1, substantive HTML, and FAQ. The effective title removes "today" whenever its price is not freshly verified. The migration must not rename or redirect the product.

## Acceptance Criteria
- Existing-product editing exposes all specified controls and quick creation does not.
- Preview works with unsaved values and clearly identifies effective automatic fallbacks.
- Public product initial HTML contains H1, meaningful body content, links, and FAQ.
- The 10 mm T006 page uses its dedicated content after migration.
- At least 3 mm, 8 mm, 10 mm, 12 mm, and 15 mm products receive distinct automatic output from their facts.
- Price-only and Excel tests prove every content/SEO field is preserved.
- Stale prices cannot produce "today" or Offer schema.
- Backend and frontend automated checks and production builds pass.
