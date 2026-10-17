# Change: Add Iran Commodity Exchange and global metals markets

## Why
The existing `/market` page correctly tracks Kaveh Metal catalog prices, but it does not represent Iran Mercantile Exchange physical trades or licensed global metals prices. Buyers need these three datasets to remain distinct so catalog quotes, official commodity-exchange trades, and international reference prices are not confused.

## What Changes
- Keep the existing catalog-backed domestic market and rename its visible context to `بازار داخلی کاوه‌متال`.
- Add a public Iran Commodity Exchange page sourced from the official IME physical-trade service, limited to steel and industrial/mineral records.
- Persist IME trade rows and expose summaries, searchable/filterable tables, supply-demand metrics, and per-symbol price/volume history.
- Add a public global-metals page backed by an explicit provider adapter, initially supporting Metals.Dev when a server-side API key is configured.
- Persist global observations with provider, source URL, exchange/authority, currency, unit, observation time, and freshness metadata.
- Support reviewed admin/CSV observations for instruments not covered by the configured provider, such as steel, scrap, billet, HRC, or iron ore; imported rows must name their source.
- Add market navigation/tabs, SEO metadata, sitemap entries, loading/empty/error/stale states, and deployment health checks.
- Add management commands and scheduled tasks for idempotent daily synchronization; never copy or scrape competitor data.

## Impact
- Affected specs: `ime-commodity-market`, `global-metals-market`, `market-context-navigation`
- Affected code: Django market models/services/admin/tasks/API, deployment configuration, Next.js market pages/navigation/SEO
- External systems: official `ime.co.ir` physical-trade service; optional Metals.Dev API key and its provider terms
- Data migration: additive market tables and indexes only

