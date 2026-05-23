# Design: User Dashboard and Direct Sales Payment Operations

## Context

The direct checkout MVP created a separate `sales` bounded context. The next step is to make it operational for buyers and admins.

The user dashboard should be distinct from the admin dashboard but share the same product philosophy: dense, simple, operational, and clear. It should not look like a marketing landing page.

## Goals

- Give buyers one place to understand direct purchase state.
- Make pending payment and deadline state impossible to miss.
- Give admins a complete operational panel for direct sales.
- Support SMS/payment link workflows without forcing a real provider in MVP.
- Preserve auditability for payment and status actions.

## Non-Goals

- No full payment gateway integration in this change.
- No full accounting ledger.
- No marketplace order board redesign.
- No automatic inventory reservation.

## Decisions

### Decision: Extend `sales`, Do Not Use Marketplace `orders`

User dashboards for direct purchases must read from `StoreOrder` and `StorePayment`, not marketplace `OrderRequest`.

Rationale:

- The buyer is purchasing from Kaveh Metal.
- The marketplace board is for user-submitted demand/supply.
- Payment deadlines and payment links are direct-sales concepts.

### Decision: Store Payment Link Metadata on Store Order

Add payment deadline and link metadata to `StoreOrder`. Keep `StorePayment` for actual payment events.

Rationale:

- A pending direct order may have a payment link before any payment exists.
- Admins need to refresh/send links even before gateway integration.

### Decision: Log SMS Sends Even Without Provider

Add notification records for SMS/email/system sends. When SMS provider is not configured, create a `SKIPPED` or `FAILED` notification record instead of silently doing nothing.

Rationale:

- Operations need to know whether a link was communicated.
- Development can proceed before provider selection.

### Decision: User Dashboard Shell Mirrors Admin Ergonomics

Use a sidebar/top summary layout similar to admin, but with user-relevant sections only.

Rationale:

- Consistency reduces development and user learning cost.
- Buyer workflows need scanning and repeated use, not marketing content.

## Backend Shape

Extend `StoreOrder`:

- `payment_due_at`
- `payment_link_token`
- `payment_link_url`
- `payment_link_created_at`
- `payment_link_sent_at`
- `payment_link_sent_to`
- `admin_notes`

Add `StoreOrderNotification`:

- order
- channel
- recipient
- event
- status
- payload
- created_at

Add APIs:

- `GET /api/v1/store/dashboard/summary/`
- `GET /api/v1/store/payments/`
- `GET /api/v1/store/pending-payments/`
- `PATCH /api/v1/admin/dashboard/store-orders/{id}/`
- `POST /api/v1/admin/dashboard/store-orders/{id}/payment-link/`
- `POST /api/v1/admin/dashboard/store-orders/{id}/send-payment-link/`

## Frontend Shape

Add or expand:

- `app/account/dashboard/page.js`
- `app/account/purchases/page.js`
- `app/account/payments/page.js`
- `app/account/orders/[id]/page.js` or direct purchase detail route
- `app/cart/page.js`
- `app/components/admin/AdminDashboardPage.js`

## Status and Deadline Rules

- Admin can set `payment_due_at`.
- User sees due time and overdue state.
- Overdue does not automatically cancel unless a later automation task is added.
- Admin may transition overdue orders to `EXPIRED` or extend the due time.

## Risks / Trade-offs

- Risk: payment link without real gateway may confuse users.
  - Mitigation: link can initially route to an internal payment instruction page or checkout payment step.
- Risk: SMS provider is undecided.
  - Mitigation: abstract provider; log skipped sends until configured.
- Risk: dashboard scope expands too much.
  - Mitigation: first slice focuses on direct orders, payments, deadlines, and cart.

## Migration Plan

1. Add nullable fields and notification table.
2. Backfill none needed; existing orders simply have no due date/link.
3. Add APIs and UI guarded by authentication/admin permissions.
4. Add tests and smoke checks.

## Open Questions

- SMS provider and sender line?
- Default payment deadline?
- Payment receipt upload before gateway?
- Route naming for direct order detail under account?
