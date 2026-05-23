# PRD: User Direct Sales Dashboard and Payment Operations

## Summary

Kaveh Metal needs a user-facing dashboard, similar in structure and quality to the admin dashboard, for customers who buy directly from the platform. The dashboard should give users a clear view of their cart, direct orders, order history, pending payments, payment deadlines, payment links, and payment records.

The admin direct-sales panel also needs to evolve from a read/confirm surface into an operations panel where admins can edit direct order records, change statuses, set payment deadlines, generate/send payment links, and notify users by SMS when payment is required.

This work extends the direct checkout capability and remains separate from the marketplace `orders` request board.

## Problem / Opportunity

The direct checkout MVP can create direct store orders, but the buyer has no complete operational dashboard. Admins also cannot yet fully manage direct sales records from the custom dashboard.

Without this feature:

- users do not know which payments are pending,
- payment deadlines are not visible,
- admins cannot send a structured payment link,
- direct sales order history is incomplete,
- support and finance cannot easily audit direct purchase status,
- direct Kaveh sales remain too manual for a production buying workflow.

## Users & Use Cases

- Buyer/customer:
  - sees a dashboard after login,
  - reviews direct orders and current status,
  - sees pending payments and payment deadlines,
  - opens payment link when available,
  - sees paid/failed/expired payment history,
  - reviews order timeline and previous purchases,
  - returns to cart/checkout when a draft or pending item exists.
- Admin/operator:
  - edits direct sales order contact, destination, notes, due date, and admin metadata,
  - changes order status through controlled transitions,
  - confirms/voids manual payments,
  - generates or refreshes a payment link,
  - sends payment link by SMS,
  - sees notification send history and order audit history.
- Finance:
  - filters pending, paid, expired, and overdue direct orders,
  - reconciles payments and payment references,
  - verifies that payment deadlines and links were communicated.

## Goals

- Add a user account dashboard for direct sales.
- Make dashboard navigation consistent with the admin dashboard style: sidebar, top summary, sections, compact cards/tables.
- Add user sections for overview, cart, orders, payments, pending payments, and order history.
- Add payment deadline support for direct orders.
- Add payment link support for direct orders.
- Add admin edit and status transition tools for direct sales.
- Add SMS sending workflow for payment links, with audit logs even when SMS provider is not configured.
- Keep marketplace `orders` separate from direct store sales.

## Non-Goals

- Do not redesign the marketplace request board in this change.
- Do not require a real bank gateway in the first implementation.
- Do not build a full accounting ledger here.
- Do not implement real SMS provider integration unless credentials/provider are already available.
- Do not expose admin-only controls in the user dashboard.

## Current State

Already available from the direct checkout MVP:

- `sales` app exists.
- `StoreOrder`, `StoreOrderItem`, `StoreOrderStatusHistory`, and `StorePayment` exist.
- Buyer can create/list direct store orders.
- Admin can list direct store orders and confirm manual payment.
- Product CTAs route to `/checkout`.
- `/account/purchases` exists as a basic purchase history page.
- `/cart` exists as a placeholder, not a full cart.

## Proposed User Dashboard

Route options:

- Preferred: `/account/dashboard`
- Existing `/account` can redirect to or host the dashboard shell.

Navigation sections:

- `overview`: summary cards for active orders, pending payments, overdue payments, completed orders.
- `cart`: current local/server cart and continue checkout.
- `orders`: active direct orders with status and item summary.
- `payments`: payment records and payment references.
- `pending-payments`: only orders/payments that require user action.
- `history`: completed, cancelled, expired, and delivered direct orders.
- `profile`: current account/KYC status link if needed.

User order detail should show:

- order ID,
- items and locked snapshots,
- delivery destination,
- origin/delivery snapshot,
- status,
- payment status,
- payment deadline,
- payment link/button,
- timeline/status history,
- support note/contact action.

## Proposed Admin Direct Sales Enhancements

Admin direct-sales section should support:

- filter by order status, payment status, overdue, buyer, search,
- edit contact name/phone, destination, notes, payment deadline,
- edit admin-only notes/metadata,
- transition status through controlled actions,
- confirm manual payment,
- create or refresh payment link,
- send payment link by SMS,
- see order timeline and notification history,
- see the locked item snapshots before editing anything.

## Proposed Backend Additions

Extend `StoreOrder`:

- `payment_due_at`
- `payment_link_url` or generated path/token fields
- `payment_link_token`
- `payment_link_created_at`
- `payment_link_sent_at`
- `payment_link_sent_to`
- `admin_notes`

Add or extend audit/notification records:

- `StoreOrderNotification`
  - order
  - channel (`SMS`, `EMAIL`, `SYSTEM`)
  - recipient
  - event
  - payload
  - status (`PENDING`, `SENT`, `FAILED`, `SKIPPED`)
  - created_at
- status/payment events continue to use `StoreOrderStatusHistory`.

Suggested APIs:

- `GET /api/v1/store/dashboard/summary/`
- `GET /api/v1/store/orders/`
- `GET /api/v1/store/orders/{id}/`
- `GET /api/v1/store/payments/`
- `GET /api/v1/store/pending-payments/`
- `PATCH /api/v1/admin/dashboard/store-orders/{id}/`
- `POST /api/v1/admin/dashboard/store-orders/{id}/transition/`
- `POST /api/v1/admin/dashboard/store-orders/{id}/payment-link/`
- `POST /api/v1/admin/dashboard/store-orders/{id}/send-payment-link/`

## Payment Deadline Rules

- Admin can set or update `payment_due_at`.
- User sees deadline in dashboard and order detail.
- If `payment_due_at < now` and payment is not paid:
  - user sees overdue state,
  - payment button can remain available or become disabled based on admin setting,
  - admin can extend deadline or expire/cancel the order.
- Payment deadline changes must be auditable.

## Payment Link Rules

- Payment links must be tied to a direct order and a token/reference.
- Link generation must be idempotent enough to avoid accidental duplicate active links.
- Link must respect payment status:
  - no payment link required for fully paid orders,
  - link can be refreshed for pending/price confirmed/payment pending orders.
- SMS send must be logged whether provider sends successfully or is unavailable.

## UX Requirements

- Dashboard must be usable for non-technical users.
- Use compact operational layout, not marketing layout.
- Use Persian labels.
- Show primary next action clearly:
  - `پرداخت کن`
  - `در انتظار اعلام قیمت`
  - `مهلت پرداخت گذشته`
  - `پرداخت شده`
  - `سفارش تکمیل شده`
- Avoid showing raw backend statuses alone; show a Persian label plus the raw status only where useful for admin.

## Acceptance Criteria

- User can open a dashboard and see direct order summary.
- User can see all direct orders and their history.
- User can see pending payments with due date and payment link.
- User can open direct order detail and see timeline/status history.
- Admin can edit a direct order record from `/admin/dashboard`.
- Admin can change direct order status from `/admin/dashboard`.
- Admin can set/update payment deadline.
- Admin can generate a payment link.
- Admin can send payment link by SMS or log a skipped send when SMS provider is not configured.
- Payment and notification actions are audited.
- Marketplace `orders` remains unchanged.
- Backend and frontend validation pass.

## Metrics

- pending direct payments count,
- overdue direct payments count,
- payment link sends per day,
- payment link click/pay conversion,
- average time from `PAYMENT_PENDING` to `PAID`,
- cancelled/expired due to missed payment deadline.

## Rollout Plan

1. Extend backend direct sales models and migrations.
2. Add user dashboard summary/order/payment APIs.
3. Add admin edit, due date, payment link, and SMS actions.
4. Build user dashboard UI.
5. Expand admin direct-sales UI.
6. Add tests for payment deadline, payment link, SMS logging, user visibility, and admin edit/status changes.
7. Run backend/frontend validation and smoke tests.

## Open Questions

- Which SMS provider should be used first?
- Should expired payment links block payment or only warn the user?
- Should users be able to upload payment receipts before a real gateway exists?
- Should KYC be required before showing payment links for large orders?
- What default payment deadline should be used: 2 hours, 24 hours, or admin-only manual?
