## Context
The catalog already stores `short_description` and `description`, structured specifications, offers, and price tiers. The public Next.js route is server-rendered for metadata but the visible product body is still primarily a client component. The same admin upsert endpoint handles quick registration and editing.

## Goals / Non-Goals
- Goals: automatic differentiated content for every useful product, manual overrides for priority products, SSR H1/body/FAQ, safe indexing and Offer decisions, and isolation from price imports.
- Non-Goals: changing product slugs, exposing canonical editing, adding fields to quick registration, or generating product copy with an external AI service.

## Decisions
- Reuse `short_description` and `description`; add only dedicated SEO, FAQ, relation, index-mode, and price-verification fields.
- Treat an empty or trivial legacy description as no override and render a deterministic template from category, grade, form, dimensions, factory, and pricing state.
- Store authored full content as sanitized HTML. The existing Editor.js visual editor converts headings, tables, lists, links, and in-content images into that HTML, while an HTML mode remains available. Product content cannot introduce another H1, script, style, event handler, protocol-relative URL, or other unsafe URL.
- Sanitize content both when it is written and when legacy records are serialized, so old unsanitized rows cannot bypass the public-page boundary.
- Save page content as a nested `page_content` object in the existing admin upsert transaction. Quick registration omits that object entirely.
- Keep canonical URLs computed from the immutable public product slug.
- Resolve `auto` indexing from active status and structured-information completeness; explicit `index` and `noindex` remain operator overrides.
- Expose the effective index decision in the product-summary feed and omit effective-noindex products from Sitemap.
- Add `price_verified_at` to each price tier. Price updates refresh it; non-price edits do not. Public current-price UI, the word "today", and Offer JSON-LD all use the same Tehran-date freshness rule.
- Render the H1 and long-form content in server components around the existing client purchasing interface, so H1 precedes all H2 elements in initial HTML.
- Apply the same verified-price filter to the product page, buy flow, cart, checkout, title freshness, and Offer JSON-LD. Without a fresh price, the workflow becomes an inquiry and does not display a stale amount.

## Risks / Trade-offs
- Existing tiers have no trustworthy verification time. They intentionally become inquiry-only until prices are updated, preventing stale prices from being represented as current.
- HTML authoring is flexible but requires sanitization. Both API validation and preview apply a conservative allow-list.
- Legacy descriptions that only repeat the product name are treated as placeholders; substantive descriptions remain manual overrides.

## Migration Plan
1. Add nullable price verification and product SEO/content fields.
2. Seed the T006 override for the known 10 mm product by its existing slug.
3. Deploy backend and run migrations.
4. Deploy frontend.
5. Refresh current prices through bulk price update so verified prices become visible again.

## Rollback
The added columns are backward compatible. Reverting the frontend restores the previous presentation; data remains available. A database rollback must be avoided after editors have entered new content unless that content is exported first.
