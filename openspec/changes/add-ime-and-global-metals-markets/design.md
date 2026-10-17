## Context
The completed steel-market dashboard stores daily Kaveh Metal catalog prices. The clarified request adds two different datasets: physical trades published by Iran Mercantile Exchange (IME) and international metal reference prices. The reference pages demonstrate useful layouts, but their data and code are not a source for this implementation.

The official IME page calls `GetAmareMoamelatList` and returns product, symbol, producer, hall, contract type, base/min/weighted/max price, supply, demand, traded quantity, trade value, unit, trade date, delivery date, and a stable report identifier. Global exchange prices require a provider contract/API; LME also distinguishes public display/distribution licences.

## Goals / Non-Goals
- Goals: show official IME steel trades, compare supply/demand and weighted prices, show provider-backed global metals with history, and keep catalog prices as a separate first-party dataset.
- Non-goals: trading execution, investment advice, copying companion-site data, bypassing provider authentication, or presenting an unlicensed number as an official LME settlement.

## Decisions
- Decision: expose three named market contexts: `/market` for Kaveh Metal catalog prices, `/commodity-exchange` for IME physical trades, and `/global-metals` for international observations.
- Decision: fetch IME from `https://www.ime.co.ir/subsystems/ime/services/home/imedata.asmx/GetAmareMoamelatList` using a server-side client with a fixed allowlisted origin, timeout, bounded date window, response-size limit, and schema validation.
- Decision: persist IME rows by the official `xTalarReportPK` identifier. Store both the published Jalali date text and a converted Gregorian `trade_date` for correct range queries.
- Decision: include only the industrial/mineral hall rows matching a maintained steel-chain vocabulary (steel, rebar, beams, sheets, billet/bloom/slab, iron ore, pellet, sponge iron, angle/channel, wire and scrap). The raw official product name remains visible.
- Decision: display IME monetary values in their official currency and unit. The UI SHALL not silently change rial to toman; any conversion must be labelled.
- Decision: use a global provider interface. The first connector is Metals.Dev and is disabled until `METALS_DEV_API_KEY` is configured server-side. Secrets never reach the browser or API response.
- Decision: provider observations are immutable by instrument/provider/time bucket and carry source URL, exchange/authority, currency, unit, observed time, fetched time, and freshness state.
- Decision: compute daily change from stored observations when the provider response does not supply it. Historical charts never invent points.
- Decision: allow staff to import reviewed global observations by CSV for uncovered steel-chain instruments. Required columns include instrument code/name, price, currency, unit, exchange, observed time, provider and source URL.
- Decision: one daily scheduled sync is compatible with the free Metals.Dev quota. Staff may run manual sync, but the service enforces a minimum refresh interval and preserves the last successful data when a provider fails.
- Decision: add lightweight accessible SVG charts and tables using the existing frontend stack; no new chart package is required.

## Data Shape
### IME trade
- Official report ID, symbol, product, producer, hall, contract type
- Base, minimum, weighted closing and maximum price
- Offered, demanded and traded quantity; transaction value
- Currency, unit, Jalali/Gregorian trade date, delivery date
- Source URL, fetched timestamp and selected official raw fields

### Global observation
- Stable instrument code and Persian/English labels
- Provider and exchange/authority
- Price, currency and unit
- Observed timestamp, fetched timestamp, source URL and freshness
- Optional open/high/low/bid/ask fields when the provider supplies them

## Risks / Trade-offs
- The legacy IME ASMX service can change without versioning. Schema validation, last-good-data retention, bounded requests and sync alerts prevent a broken upstream from corrupting public data.
- IME dates and currencies are easy to misread. Persisting Gregorian and Jalali dates together and showing the official currency/unit avoids ambiguous charts.
- Global feeds have licence and quota constraints. The page remains useful with a clear unavailable state until a key is configured, and every value identifies its provider.
- The Metals.Dev starter connector covers common industrial/precious metals but not every steel-chain benchmark. Reviewed CSV import and the provider interface allow later Fastmarkets or another licensed feed without changing the public API.

## Migration Plan
1. Add IME and global observation tables, constraints, admin and migrations.
2. Add validated sync services, management commands, scheduled tasks and tests with recorded fixtures.
3. Add public summary/list/history APIs.
4. Add the two pages and shared three-market navigation while preserving `/market`.
5. Configure the optional provider key, run initial IME sync, verify source/freshness labels, and deploy.
6. Roll back by hiding the two new navigation entries; additive observations may remain.

## Open Questions
- The implementation can be completed with the global page in an honest unavailable state; a Metals.Dev API key is required before live global prices appear.
- Broader benchmarks such as HRC, billet, scrap and iron ore require a separately approved provider or staff-imported licensed data.

