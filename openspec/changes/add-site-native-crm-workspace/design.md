## Context

The workbook defines a generic CRM in 33 sheets. The website already implements several of those domains with stronger transactional guarantees. The implementation must preserve existing CRM data, keep checkout and logistics independent from CRM failures, and avoid parallel order/payment records.

## Goals / Non-Goals

### Goals

- A correct opportunity-based direct-sales funnel.
- Complete daily CRM operation from the admin site and Bale.
- Safe Excel round-trip with broad workbook compatibility.
- Reuse of existing product, order, payment, freight, and messaging models.
- Idempotent event synchronization and complete audit history.

### Non-Goals

- Using Excel or Google Sheets as the live database.
- Replacing sales, payment, logistics, product, or account models.
- Counting user-to-user marketplace activity as Kavex store revenue.
- Arbitrary user-authored automation code.
- Supplier procurement or a full inventory ledger in the first implementation phase.

## Domain Boundaries

### Customer

`Customer` remains the stable person/company record keyed by normalized phone. Its existing `stage` and funnel endpoint remain the customer-relationship funnel shown in the current admin dashboard. Existing customer counts, stage history, ledger KPIs, CLV, follow-up totals, and labels remain backward-compatible.

The new opportunity funnel is additive and does not automatically overwrite `Customer.stage`. The two funnels have separate endpoints, labels, and explanations so customer statistics are not confused with deal statistics.

### Lead

`CrmLead` records each inbound event independently:

- customer (nullable until identity is complete)
- source/source detail and optional campaign
- subject/details and structured need snapshot
- received time, assigned user, qualification status/reason
- external source type/id and unique idempotency key
- converted opportunity and audit fields

Signup, assistant inquiry, order submission, manual entry, and Bale entry all use one lead-intake service.

### Opportunity

`CrmOpportunity` is the commercial unit counted by the funnel:

- customer, source lead, title and owner
- stage, expected value in IRR, probability, expected close date
- product/need snapshot, quantity, destination, next action and next follow-up
- failure reason, close time, source type/id
- optional `StoreOrder` identity/link without copying its financial state
- soft-delete and timestamps

`CrmOpportunityStageHistory` records every transition with from/to, actor, reason, event key, metadata, and timestamp.

### Interaction / Follow-up / Task

`CustomerActivity` is retained and extended with optional opportunity, direction, result, next action, external message key, and attachment metadata.

A dedicated `CrmFollowUp` is introduced because the workbook behavior needs assignment, status, snooze, result, next follow-up, sequence step, reminders, and idempotency. Existing open follow-ups embedded in activities are migrated and linked back to their source activity.

`CrmTask` covers non-contact operational work and may point to a customer, lead, opportunity, or store order.

## Site-Native Pipeline

| CRM stage | Website source/status |
|---|---|
| `new_inquiry` | signup with interest, new assistant inquiry, manual/Bale lead, `DRAFT`/`SUBMITTED` order |
| `qualified` | identity and minimum need fields confirmed |
| `pricing` | `StoreOrder.QUOTE_REQUESTED` or admin price/stock/freight review |
| `quote_sent` | `PRICE_CONFIRMED` with `AWAITING_BUYER` |
| `payment_pending` | priced checkout or confirmed quote with `PAYMENT_PENDING` |
| `fulfillment` | `PAID`, `FULFILLMENT_PENDING`, `READY_FOR_PICKUP`, or `SHIPPED` |
| `won` | `DELIVERED` or `COMPLETED` |
| `lost` | final `CANCELLED`/`EXPIRED` or manually closed with a reason |

Quote rejection writes an interaction/reason and returns the opportunity from `quote_sent` to `pricing`. It does not close the opportunity.

Assistant inquiry status maps as follows: `new` to `new_inquiry`, `contacted` to `qualified`, `quoted` to `quote_sent`, `won` to `won`, and `lost` to `lost`.

## Event Synchronization

One service owns event-to-CRM synchronization. Each event has a stable key such as:

- `SIGNUP:<user-id>:<version>`
- `ASSISTANT_INQUIRY:<id>:<updated-at>`
- `STORE_ORDER:<id>:<status-history-id>`
- `PAYMENT:<id>:<status>:<updated-at>`
- `BALE:<update-id>`

The service uses a unique processed-event record or unique constraints to make retries safe. CRM sync runs after the source transaction commits. Failures are logged for retry and never roll back signup, checkout, payment, or logistics.

## Transactional Source of Truth

- Catalog: `products.Product`, `Offer`, and `PricingTier`.
- Quotes/orders/items: `sales.StoreOrder`, `StoreOrderItem`, quote metadata, and status history.
- Payments: `StorePayment` and approved offline payment records.
- Fulfillment: loading vehicles, weighbridge slips, delivery requests/assignments/documents.
- CRM views these records and invokes domain services for allowed actions; it does not duplicate or directly mutate their status/money fields.

Direct-order financial values remain IRR. CRM expected values are stored in IRR. Existing manual `CustomerTransaction` rows are explicitly Toman; a migration or compatibility layer must expose currency/unit and never mix values without a tested ×10 conversion.

## Configurable CRM Data

The first phase uses fixed system stage codes with configurable Persian label, order, probability, SLA, default follow-up, required fields, and active state. Later configuration adds:

- `CrmFailureReason`
- `CrmCampaign`
- `CrmFollowUpSequence` and steps
- `CrmContactChannel` with consent
- `CrmFieldDefinition` / typed values
- `CrmMessageTemplate`
- `CrmAutomationRule` restricted to registered triggers/actions

Changing labels cannot break event mapping because rules bind to stable codes.

## Excel Architecture

The supplied workbook is a presentation/schema reference, not an import contract by itself. A backend workbook service produces a versioned file with:

- guide, dashboard, dictionary, list, and configuration sheets
- editable CRM sheets populated with stable database IDs
- read-only projections for products, orders, items, payments, quotes, shipments, users, and audit
- formulas, validation, tables, right-to-left formatting, and schema metadata

Import is a two-step job:

1. `preview`: parse workbook, verify schema, classify rows as create/update/skip/error, reject protected-sheet edits, and persist a short-lived report.
2. `apply`: require the same file hash and preview token, apply only whitelisted fields row-by-row/transactionally, log every result, and never interpret a blank cell as deletion unless a dedicated clear marker is specified.

Orders, payments, product prices, stock, shipment status, and audit are never import-writable from this CRM workbook.

## Bale Architecture

The generic Telegram-shaped provider remains, configured only with `https://tapi.bale.ai` for this deployment. New models:

- `BaleUserBinding`: unique Bale user id to active website user, with verification/activation metadata.
- `BaleBotSession`: current wizard, step, payload, expiry, and last interaction.
- `BaleProcessedUpdate`: unique update/callback id for replay protection.

Authorization resolves the bound website user and calls the existing role/admin-section permission model. Group chat membership or a text allowlist alone cannot grant write access.

Internal commands/wizards:

- `/مشتری`, `/سرنخ`, `/فرصت`, `/پیگیری`, `/امروز`, `/عقب_افتاده`
- `/جستجو`, `/یادداشت`, `/مرحله`, `/پیشنهاد`, `/سفارش`, `/پرداخت`, `/گزارش`, `/لغو`

Every multi-step write shows a final summary and explicit confirmation. Financial actions, final close, and merge require a second confirmation. Public free-text product search stays available but is routed separately and cannot access CRM commands without a valid binding.

## API and UI Shape

Backend resources:

- `/api/crm/leads/`
- `/api/crm/opportunities/` plus transition action/history
- `/api/crm/follow-ups/` plus complete/snooze/cancel
- `/api/crm/tasks/`, campaigns, pipeline config, reasons, sequences, fields
- `/api/crm/dashboard/`
- `/api/crm/excel/export/`, `import-preview/`, and `import-apply/`

The admin workspace uses operational views rather than one customer-stage table:

- Lead inbox
- Opportunity list/board grouped by site-native stage
- Customer file with linked opportunities, site orders, timeline, balances, and follow-ups
- Follow-up/task work queue
- Funnel and KPI dashboard
- CRM configuration
- Excel operations and import error report

## Additive Data Rollout

1. Add opportunity/history models without removing or redefining existing customer stage/follow-up fields.
2. Backfill opportunities from existing assistant inquiries and direct store orders using stable source keys.
3. Copy open embedded follow-ups to dedicated records only when that phase starts, preserving source activity ids.
4. Add the second funnel endpoint/UI and Bale commands without replacing the customer funnel.
5. Verify that existing customer counts, ledger KPIs, histories, and screenshots remain unchanged.

## Risks / Trade-offs

- Full workbook parity is broad, so implementation is phased while the PRD remains the target contract.
- Eventual CRM synchronization is safer for checkout, but requires retry visibility.
- Configurable stages are limited to stable system codes initially; arbitrary pipelines would make website status mapping ambiguous.
- Excel write restrictions reduce flexibility but protect transactional integrity.
- Bale sessions add state, but are necessary to prevent partial records and unsafe free-text commands.

## Rollback

New models and fields are additive. The opportunity funnel and event handlers can be disabled independently while the current customer funnel continues to work. No existing customer, order, payment, or logistics table is removed or rewritten.

## Approved Priority

The product owner approved keeping both funnels. Website data and Bale operations are the current priority; Excel remains a later controlled reporting/import interface.

## First-Slice Implementation Notes

- `CrmOpportunity` uses a partial unique constraint on `(source_type, source_id)` so one direct order or assistant inquiry cannot create duplicate opportunities.
- `CrmOpportunityStageHistory.event_key` and `CrmSyncEvent.event_key` make source-event replay idempotent. Failed sync events remain visible through an admin API and can be retried.
- `customers.signals` schedules synchronization with `transaction.on_commit`; exceptions are logged and do not roll back checkout, payment, or logistics writes.
- Migration `customers.0007` backfills existing `StoreOrder` and `AssistantInquiry` records without changing customer stages or copying transactional payment/logistics rows.
- `AssistantInquiry.matched_price` is retained as catalog-price metadata and is not treated as total opportunity value without a normalized quantity; direct-order totals remain the monetary source for site sales KPIs.
- The first Bale slice is read-only for opportunities. `BaleUserBinding` maps a Bale user id to an active website user and permissions are recalculated on every internal command/callback; group/chat ids are notification destinations only.
- Financial and final Bale write actions remain disabled until sessions, replay protection, confirmation, and domain-service routing are implemented.
