# Change: Add a site-native CRM workspace with Bale and Excel round-trip

## Why

The project already has customers, a manual ledger, activities, follow-ups, a customer-level funnel, automatic site lead intake, direct-sales orders, payments, logistics, and a two-way Bale bot. The supplied CRM workbook is broader, but it was designed around Google Sheets and Telegram and uses a generic retail funnel.

The current customer-level `stage` is useful as a customer-relationship funnel and its dashboard statistics must remain available, but it cannot represent two simultaneous deals for one customer or reliably follow the real website journey from quote request through delivery. A second opportunity funnel is required. Copying the workbook's order/payment/product tables into the CRM would also create a second source of truth beside the site's existing transactional models.

## What Changes

- Make Django/PostgreSQL the authoritative CRM store and use the supplied Excel workbook as a versioned export/import/reporting bridge.
- Preserve the existing customer funnel and add an independent opportunity/direct-sales funnel.
- Add independent CRM leads and opportunities so one customer can have multiple concurrent sales journeys.
- Define the Kavex direct-sales pipeline from actual `AssistantInquiry` and `StoreOrder` events: new inquiry, qualified need, pricing, quote sent, payment pending, fulfillment, won, or lost.
- Synchronize direct-sales status history, quote confirmation, payment, loading, shipment, and delivery into the matching opportunity without duplicating transactional rows.
- Expand the admin CRM into a lead inbox, opportunity workspace, customer timeline, follow-up/task view, site-native funnel, configuration, and Excel operations.
- Expand the Bale bot from three shortcuts into authenticated, role-scoped CRM wizards with persistent sessions and replay protection.
- Defer Excel behind site data and Bale; later add safe preview/apply semantics with read-only transactional sheets.
- Add configurable stage labels/SLA, failure reasons, follow-up sequences, message templates, campaigns, custom fields, and whitelisted automation in later phases of the same product program.

## Important Decisions

- Telegram and Google Sheets are not runtime dependencies.
- Marketplace/barandaz user-to-user activity is excluded from the direct-store conversion funnel.
- Order, product, payment, freight, loading, weighbridge, and delivery data remain owned by their existing apps.
- Sensitive transitions use existing domain services; CRM and Excel do not write status or money fields directly.
- The product owner approved implementation with both funnels retained and site data/Bale prioritized over Excel.

## Implemented First Slice

- Added additive opportunity, transition-history, and retryable sync-event models plus backfill migrations.
- Synchronizes direct store orders and assistant inquiries after commit without changing `Customer.stage` or blocking source transactions.
- Added admin-scoped opportunity/list/funnel/sync-retry APIs and a second funnel tab while preserving the existing customer funnel.
- Added read-only Bale reports, inline button navigation and opportunity drill-down, plus website-managed Bale-user bindings with live website role checks and explicit unbound-user feedback.
- Deferred Bale write wizards, automation, dedicated leads/follow-ups, and Excel round-trip to later slices.

## Impact

- Affected specs: `customer-crm`, `messaging`, `crm-excel`.
- Backend: `customers`, `messaging`, `assistant`, `sales`, `offline_payments`, and event/audit integration.
- Frontend: CRM, follow-up, funnel, messaging settings, and a new Excel operations surface in the admin workspace.
- Data: additive opportunity models; existing customer stage semantics and dashboard remain intact.
- Source artifacts: `openspec/crm/store-crm-design-fa.md` and `openspec/crm/CRM-Store-Template-v1.xlsx`.
- Product requirements: `openspec/prd/site-native-crm-bale-excel-prd.md`.
