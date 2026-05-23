# Design: Direct Product Checkout

## Context

Kaveh Metal currently has two separate business concepts:

- Catalog products managed by admins and shown in `/products`.
- Marketplace requests where authenticated/verified users publish buy or sell announcements through `orders`.

Direct purchases of Kaveh-owned catalog products should not use the marketplace request models. They need different ownership, payment, fulfillment, and reporting rules.

## Goals

- Keep direct store sales separate from marketplace order requests.
- Support priced checkout, quote requests, and backorders.
- Preserve immutable item snapshots for audit and accounting.
- Keep the first implementation small enough to test.
- Leave a clean integration point for payment gateway callbacks.

## Non-Goals

- No escrow ledger in the first direct-sales slice.
- No warehouse automation in the first direct-sales slice.
- No replacement of marketplace request feed.
- No anonymous final checkout.

## Decisions

### Decision: Create a Separate Direct Sales Bounded Context

Use a new app such as `sales` or `checkout` rather than extending `orders`.

Rationale:

- Marketplace `OrderRequest` is about other users announcing demand/supply.
- Direct store sales are owned by Kaveh Metal and need direct revenue reporting.
- Future payment/fulfillment states are different from RFQ/marketplace states.

### Decision: Snapshot Product Data on Order Items

`StoreOrderItem` stores product, offer, pricing tier references plus locked snapshots:

- title
- specifications
- delivery origin
- seller name
- unit price
- quantity and total

Rationale:

- Product prices and specs can change after checkout.
- Accounting and support need historical truth.

### Decision: Manual Payment First, Gateway Later

MVP supports `PAYMENT_PENDING` and admin payment confirmation. A `StorePayment`/`StorePaymentIntent` model should exist or be introduced in the same shape the gateway can later use.

Rationale:

- It lets the business start testing direct orders before selecting a gateway.
- It avoids premature gateway-specific coupling.

### Decision: Product CTAs Stop Using `/orders`

Direct product actions should use `/cart`, `/checkout`, or direct quote endpoints.

Rationale:

- `/orders` is the marketplace board.
- Buyers should not accidentally create marketplace requests when buying Kaveh-owned products.

## Suggested Backend Shape

- `sales.models.StoreOrder`
- `sales.models.StoreOrderItem`
- `sales.models.StoreOrderStatusHistory`
- `sales.models.StorePayment`
- `sales.serializers`
- `sales.views`
- `sales.urls_v1`

API:

- `POST /api/v1/store/orders/`
- `GET /api/v1/store/orders/`
- `GET /api/v1/store/orders/{id}/`
- `POST /api/v1/store/orders/{id}/submit/`
- `POST /api/v1/store/orders/{id}/cancel/`
- `GET /api/v1/admin/dashboard/store-orders/`
- `POST /api/v1/admin/dashboard/store-orders/{id}/transition/`

## Suggested Frontend Shape

- `app/cart/page.js`
- `app/checkout/page.js`
- `app/account/purchases/page.js`
- product CTAs in `app/products/page.js` and `app/products/[id]/page.js`
- direct sales panel in `app/components/admin/AdminDashboardPage.js`

## Status Transition Sketch

- `DRAFT -> SUBMITTED`
- `DRAFT -> QUOTE_REQUESTED`
- `SUBMITTED -> PAYMENT_PENDING`
- `QUOTE_REQUESTED -> PRICE_CONFIRMED`
- `PRICE_CONFIRMED -> PAYMENT_PENDING`
- `PAYMENT_PENDING -> PAID`
- `PAID -> FULFILLMENT_PENDING`
- `FULFILLMENT_PENDING -> READY_FOR_PICKUP`
- `READY_FOR_PICKUP -> SHIPPED`
- `SHIPPED -> DELIVERED`
- `DELIVERED -> COMPLETED`
- any non-terminal state -> `CANCELLED`
- quote states -> `EXPIRED`

## Risks / Trade-offs

- Risk: building full payment too early slows the MVP.
  - Mitigation: start with manual payment status, keep payment model idempotency-ready.
- Risk: inventory reservation semantics are unclear.
  - Mitigation: do not decrement inventory until the inventory model exists; show status only.
- Risk: direct sales and marketplace requests confuse users.
  - Mitigation: rename UI surfaces clearly: "خرید از کاوه متال" versus "تالار اعلام بار".

## Migration Plan

1. Add new backend app and API without changing existing `orders`.
2. Update frontend CTAs to direct checkout routes.
3. Add admin panel for direct sales.
4. Add payment gateway integration in a later change.

## Open Questions

- KYC gate: before submit, before payment, or based on order amount?
- Payment provider and callback format?
- Quote expiration time?
- Quantity units and minimum quantities by product type?
