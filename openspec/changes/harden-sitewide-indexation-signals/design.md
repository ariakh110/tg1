## Context

The site has two valid product discovery surfaces: canonical category hubs and an interactive filtered price board. Search engines must consolidate the filtered URLs into the hubs without removing the filtering workflow used by buyers. Private routes must communicate indexation policy through HTML meta tags, which requires crawler access.

## Goals / Non-Goals

### Goals

- Make every important public route emit complete, deterministic metadata in initial HTML.
- Consolidate family query URLs without breaking the interactive catalog.
- Prevent transactional and private routes from entering search results.
- Keep sitemap and robots output consistent with route metadata.
- Give category canonicals substantive, crawlable product content.

### Non-Goals

- A 301 redirect from every `?family=` URL is deferred until the category hub reaches filter and comparison parity with `/products`.
- Search Console validation and index requests remain production operations after deployment.
- This change does not alter product pricing, checkout behavior, authentication, or account authorization.

## Decisions

### Server route with client islands

Home, products, orders, account, and admin retain their existing interactive client implementations inside client components. Their route page or layout is server-owned so Next.js Metadata API output is deterministic. Removing `useSearchParams` from the products route boundary also prevents the Suspense fallback from replacing the initial H1.

### Shared public/private metadata builders

`buildPublicMetadata` creates canonical, robots, Open Graph, and Twitter fields from one route contract. `buildNoIndexMetadata` emits either `noindex,follow` for purchase discovery or `noindex,nofollow` for private workflows. Private routes intentionally omit canonical links.

### Canonical before redirect

The family price board stays usable at `/products?family=...`, while its canonical points to the corresponding category hub. Primary navigation points directly to the hub. A later 301 is safe only after all catalog filtering needs are available there.

### Robots and noindex

Routes carrying `noindex` remain allowed to crawl. The frontend sanitizes legacy blocks returned by the configurable backend robots endpoint and always emits the canonical sitemap directive. A Django migration updates existing default settings so the persisted configuration agrees with the public response.

### Canonical-only sitemap

Sitemap entries are normalized to the configured site origin, have query and fragment components removed, exclude private route patterns, and are deduplicated. Dynamic products, category families, landings, and blog entries pass through the same policy.

### Category hub content

Each family hub renders up to 100 API-backed products with product URL, grade, delivery city, and active minimum price or enquiry state. It publishes a product `ItemList` in addition to authored landing links. Empty families use an actionable enquiry state and never claim that content will arrive 'soon'.

## Risks / Mitigations

- Backend downtime during build: metadata and category routes use established legacy family fallbacks; sitemap calls are time-bounded.
- Stale custom robots text: frontend sanitization enforces crawl access for noindex routes at response time.
- Duplicate family discovery: navigation, canonical tags, and sitemap all point at `/category/<family>`.
- Large family lists: the existing summary API is capped at 100 lightweight rows.
