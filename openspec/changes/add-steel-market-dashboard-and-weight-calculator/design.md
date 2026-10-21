## Context
The storefront already exposes active products with offer pricing tiers and freshness timestamps. It has no durable price series, so a chart cannot be reconstructed reliably from the current row alone. The reference design also includes global exchange data, but the project does not currently have a licensed feed or a verified contract for redistribution.

## Goals / Non-Goals
- Goals: make domestic catalog movement understandable, preserve daily price history, provide accurate section-weight calculations, and connect both tools to existing product/inquiry journeys.
- Non-goals: trading execution, investment advice, scraping a third-party website, or claiming real-time LME/commodity-exchange coverage without an approved feed.

## Decisions
- Decision: add an immutable daily `ProductPriceSnapshot` keyed by product, pricing basis, and Tehran-local calendar date. A same-day price update replaces that day's closing snapshot; earlier days remain unchanged.
- Decision: normalize market comparison to price per kilogram. Per-ton values are divided by 1,000. Per-sheet prices are excluded from percentage comparisons unless the product has a valid `weight_kg_per_unit`; the API explains excluded rows.
- Decision: seed one baseline snapshot for current valid prices during migration/management command execution, without inventing older history.
- Decision: public market endpoints return summary, groups, rows, and bounded history series. Querysets include only active products, active offers, positive prices, and their latest effective tier.
- Decision: render market time series and hierarchical commodity maps with Apache ECharts, loaded in the browser with ResizeObserver cleanup. Tables remain the canonical accessible representation.
- Decision: calculator formulas live in a pure frontend module with deterministic tests. Standard section tables (channel/I-beam) are versioned data with the cited standard name; formula-based shapes use steel density 7,850 kg/m³ by default.
- Decision: external indicators use a future provider interface with source name, source URL, observed timestamp, currency, unit, and freshness. Missing data renders an honest unavailable state.
- Decision: global-market credentials and refresh policy are managed through the singleton site settings. The API key is write-only, the public response exposes only a configured boolean, and the server environment key remains a fallback for existing deployments.
- Decision: Celery checks global-market synchronization hourly; the sync service applies the admin-configured 1–168 hour minimum interval before any provider request.
- Decision: administrators can force a provider sync or import a reviewed licensed CSV. Both actions use authenticated admin-only endpoints and preserve the existing source/timestamp validation.

## Market API Shape
- `GET /api/market/summary/`: counts, advances/declines/unchanged, latest observation time, top gainers/losers, and grouped tiles.
- `GET /api/market/products/`: paginated/searchable current rows with current/previous price, absolute and percentage change, category, factory, grade, basis, and timestamp.
- `GET /api/market/products/{product_id}/history/?range=7d|30d|90d`: bounded daily series.

## Weight Formulas
- Rebar: `diameter² / 162 × length × quantity` kilograms.
- Sheet: `width_mm × length_mm × thickness_mm × 0.00000785 × quantity` kilograms.
- Circular pipe: `π/4 × (D² - (D - 2t)²) × length_m × 0.00785 × quantity` kilograms.
- Rectangular/square hollow section: `[W×H - (W-2t)×(H-2t)] × length_m × 0.00785 × quantity` kilograms.
- Equal/unequal angle: `t × (a + b - t) × length_m × 0.00785 × quantity` kilograms.
- Channel and I-beam: selected standard table weight in kg/m × length × quantity. A custom kg/m field is available for sizes outside the bundled table.

## Risks / Trade-offs
- Sparse initial history means early charts contain one point. The UI states this clearly and becomes richer as prices change.
- Different pricing bases can create misleading comparisons. Normalization/exclusion rules and visible basis labels prevent mixed-unit deltas.
- Standard theoretical weight may differ from factory tolerance. Every result is labelled approximate and points buyers to the product certificate/weighbridge for settlement.
- A large market map can be hard to use on mobile. Mobile uses a compact ranked tile list and retains the full searchable table.

## Migration Plan
1. Add the snapshot schema and price-capture service.
2. Seed one current baseline in an idempotent command.
3. Deploy API endpoints before exposing navigation links.
4. Deploy market and calculator pages and verify empty/sparse/full states.
5. Roll back by hiding navigation links and endpoints; snapshot data is additive and can remain safely in place.

## Open Questions
- Which channel should the market-page call to action prioritize: product purchase, quote request, or direct phone contact?

## Market chart corrections (2026-10-21)
- Use ECharts line/bar charts with zoom, dated Persian axes, separate price/volume axes, and expandable commodity row charts.
- Missing values remain null gaps; a single point is displayed honestly. Ignore aborted requests and avoid showing a previous symbol/range while fetching.
- Aggregate same-day commodity executions by volume for weighted prices, retain base quotes as a distinct series, and separate units/currencies.
- Query both main and secondary IME halls; preserve the original product name and append only explicitly supplied grade/dimension details.
- Commodity tables search the complete saved report, sort before pagination, and expose a group/producer/symbol treemap.
- Store an optional visible metal-code allowlist: null means all, [] means none. Apply it to summary, exchange filters and history while retaining observations.
- Global history and daily changes use the latest observation provider consistently, avoiding duplicate same-day points from mixed providers.

## Review fixes and channel reporting (2026-10-21)
- Treemap drilldown is controlled in React with explicit breadcrumb navigation. Each selection applies group, producer, exact symbol and the map's date to the table; root resets the scope.
- Place the shared dark market navigation at the top of every market hero with matching container dimensions.
- Add a full-admin-only channel drafts panel under messaging. Generate item/producer/delivery reports or separate group summaries only for the requested report date, without falling back to a different day.
- Drafts snapshot platform-specific signatures, destination IDs and report IDs. Use independent write-only Telegram and Bale bot tokens; default channel links are https://t.me/kavehmetal and https://ble.ir/kavehmetal as supplied by the owner.
- Deduplicate offer/demand volumes by official offer ID, weight execution prices by actual traded volume, show absent values explicitly, and add VAT only when the administrator explicitly configures a percentage.
- A persisted per-draft/platform publication claim prevents repeated clicks from posting twice. Platform rejections are retryable explicitly; uncertain network outcomes remain blocked from automatic resend. Every attempt is represented in the existing outbound log.
- Preview generation makes no external requests; publication is triggered only by the administrator's send action. Telegram's HTTPS API root supports a configured relay; Bale uses its documented bot API.

## Telegram proxy recovery (2026-10-22)
- Owner authorized implementation after production HTTPS requests to Telegram timed out. Add an optional bot-only Telethon MTProto transport while preserving HTTPS/Bale defaults.
- Full admins can save API ID, write-only API hash and at most 20 classic/dd MTProxy links, import a small text file, and test saved links without publishing. FakeTLS ee links are explicitly rejected because the selected connector does not support them.
- Resolve and pin public proxy IPs. Try at most the first three links during bounded preflight; verify bot login and channel posting permissions. Do not switch proxies or automatically resend after sending starts. Missing configuration or exhausted preflight is definitely unsent; later network failures remain uncertain.
- Application credentials must be obtained by the owner from my.telegram.org; deployment and mock tests cannot establish live connectivity without those credentials and working proxy links.
- A full administrator may explicitly attest that a completed uncertain message is absent from the channel; record actor/time and mark it failed without sending. Active claims and confirmed deliveries cannot be released. A subsequent send still requires a separate explicit retry.
