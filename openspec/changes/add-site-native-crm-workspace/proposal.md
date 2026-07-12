# Change: Add a site-native CRM workspace with Bale and Excel round-trip

## Why

The project already has customers, a manual ledger, activities, follow-ups, a customer-level funnel, automatic site lead intake, direct-sales orders, payments, logistics, and a two-way Bale bot. The supplied CRM workbook is broader, but it was designed around Google Sheets and Telegram and uses a generic retail funnel.

The current customer-level `stage` cannot represent two simultaneous deals for one customer and cannot reliably follow the real website journey from quote request through pricing, buyer confirmation, payment, loading, shipment, and delivery. Copying the workbook's order/payment/product tables into the CRM would also create a second source of truth beside the site's existing transactional models.

## What Changes

- Make Django/PostgreSQL the authoritative CRM store and use the supplied Excel workbook as a versioned export/import/reporting bridge.
- Separate customer lifecycle from commercial pipeline state.
- Add independent CRM leads and opportunities so one customer can have multiple concurrent sales journeys.
- Define the Kavex direct-sales pipeline from actual `AssistantInquiry` and `StoreOrder` events: new inquiry, qualified need, pricing, quote sent, payment pending, fulfillment, won, or lost.
- Synchronize direct-sales status history, quote confirmation, payment, loading, shipment, and delivery into the matching opportunity without duplicating transactional rows.
- Expand the admin CRM into a lead inbox, opportunity workspace, customer timeline, follow-up/task view, site-native funnel, configuration, and Excel operations.
- Expand the Bale bot from three shortcuts into authenticated, role-scoped CRM wizards with persistent sessions and replay protection.
- Add safe Excel preview/apply semantics: editable CRM sheets, read-only transactional sheets, schema versioning, row errors, audit, and no blank-cell deletion.
- Add configurable stage labels/SLA, failure reasons, follow-up sequences, message templates, campaigns, custom fields, and whitelisted automation in later phases of the same product program.

## Important Decisions

- Telegram and Google Sheets are not runtime dependencies.
- Marketplace/barandaz user-to-user activity is excluded from the direct-store conversion funnel.
- Order, product, payment, freight, loading, weighbridge, and delivery data remain owned by their existing apps.
- Sensitive transitions use existing domain services; CRM and Excel do not write status or money fields directly.
- This proposal requires product-owner approval before runtime implementation begins.

## Impact

- Affected specs: `customer-crm`, `messaging`, `crm-excel`.
- Backend: `customers`, `messaging`, `assistant`, `sales`, `offline_payments`, and event/audit integration.
- Frontend: CRM, follow-up, funnel, messaging settings, and a new Excel operations surface in the admin workspace.
- Data: additive CRM models plus a controlled migration away from customer-level commercial stage semantics.
- Source artifacts: `openspec/crm/store-crm-design-fa.md` and `openspec/crm/CRM-Store-Template-v1.xlsx`.
- Product requirements: `openspec/prd/site-native-crm-bale-excel-prd.md`.
