# Change: Add steel market dashboard and section weight calculator

## Why
Visitors currently see individual product prices but cannot understand the market at a glance, compare daily movement, or calculate the purchase weight of common steel sections. A dedicated market page and a practical weight calculator will turn the existing catalog into a daily decision tool and create clear paths from research to inquiry or purchase.

## What Changes
- Add a public `/market` page with a responsive market map, gain/loss summary, searchable price table, and product price history chart.
- Record a daily product-price snapshot whenever an effective `PricingTier` price changes, and expose public aggregate/history endpoints backed by active catalog data.
- Show the data timestamp and price basis on every market view; never label stale or manually entered values as live exchange data.
- Keep external/global metal prices behind a provider boundary. No fabricated fallback values will be shown when a licensed or owner-approved source is unavailable.
- Add a public `/tools/steel-weight-calculator` page for rebar, sheet, pipe, rectangular/square hollow section, angle, channel, and I-beam calculations.
- Show weight per metre/unit, total kilograms and tonnes, formula/standard context, and an optional estimated value from a user-entered price per kilogram.
- Add desktop/mobile navigation, footer links, metadata, and sitemap entries for both tools.
- Add focused backend and frontend verification for history capture, aggregate calculations, formulas, empty states, and responsive rendering.

## Impact
- Affected specs: `steel-market-dashboard`, `steel-weight-calculator`
- Backend: `products.models`, price-write paths, a migration, public serializers/views/URLs, Django admin, and product tests.
- Frontend: new market and calculator routes/components, shared SVG chart primitives, header/mobile/footer navigation, and sitemap.
- Data: one additive price-snapshot table; existing products, offers, and pricing tiers remain compatible.
- External services: none for the first release. A future approved provider may populate global indicators through the documented adapter.
