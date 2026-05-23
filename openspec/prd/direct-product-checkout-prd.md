# PRD: Direct Product Checkout for Kaveh Metal

## Summary

Kaveh Metal needs a direct online purchase path for products owned and priced by the platform. This must be separate from the existing `orders` / `OrderRequest` marketplace flow, where verified users publish buy or sell requests for their own inventory.

The new feature introduces a store-sales workflow: product CTA, cart/checkout, direct sales order, quote handling for price-less products, admin review, and later payment integration.

## Problem / Opportunity

The current product catalog can show prices and product details, but purchase actions still point toward `/orders`, which is designed for user-submitted marketplace requests. Mixing direct Kaveh sales with marketplace requests will create problems in:

- accounting and payment reconciliation,
- admin ownership and fulfillment,
- reporting direct revenue versus marketplace activity,
- UX clarity for buyers,
- future escrow/dispute workflows.

## Users & Use Cases

- Storefront buyer:
  - buys a priced Kaveh product from `/products`,
  - asks for a quote when the product has no price,
  - registers a direct backorder/reservation when the product is out of stock,
  - tracks direct purchases from account pages.
- Admin/operator:
  - sees direct sales orders separately from marketplace requests,
  - confirms price, delivery origin, and payment status,
  - cancels, expires, or fulfills direct sales orders,
  - exports/reviews direct sales history.
- Finance/operations:
  - distinguishes direct Kaveh revenue from marketplace RFQ activity,
  - audits locked checkout price and payment state.

## Goals

- Keep marketplace `orders` for user buy/sell announcements only.
- Add a direct sales capability for Kaveh-owned catalog products.
- Route product-list and product-detail CTAs to cart/checkout or direct quote flow.
- Lock product price, offer, seller, and delivery snapshot at checkout time.
- Support products with price, price inquiry, and out-of-stock/backorder states.
- Add admin visibility for direct sales without loading unrelated KYC/order-request data unnecessarily.
- Keep payment gateway integration pluggable and optional for MVP.

## Non-Goals

- Do not replace the existing marketplace request board.
- Do not implement escrow for direct Kaveh-owned products in the first slice.
- Do not build full warehouse/WMS integration in MVP.
- Do not require product images for checkout.
- Do not allow public anonymous final order submission; checkout should require login before final submit.

## Product Model

The existing catalog remains the source of truth:

- `Product`: item being sold.
- `ProductSpecification`: dimensions, grade, factory, process, surface.
- `Offer`: seller/owner offer. For direct Kaveh sales, the seller is the Kaveh seller profile.
- `PricingTier`: unit price used for priced checkout.
- `DeliveryLocation`: origin and delivery place snapshot.

The direct sales feature will reference these records but store immutable snapshots on order items.

## Proposed Backend Capability

Create a new bounded context, preferably a Django app named `sales` or `checkout`.

Suggested API prefix:

- `/api/v1/store/cart/`
- `/api/v1/store/orders/`
- `/api/v1/store/quotes/`
- `/api/v1/admin/dashboard/store-orders/`

Suggested models:

- `StoreOrder`
  - buyer/user
  - status
  - contact fields
  - delivery preference/destination
  - subtotal/total/currency
  - payment status
  - created/updated/submitted timestamps
- `StoreOrderItem`
  - product
  - offer
  - pricing tier
  - quantity/unit
  - locked unit price
  - locked product title
  - locked product specification snapshot
  - locked delivery origin snapshot
- `StoreOrderStatusHistory`
  - order
  - from/to status
  - actor
  - event
  - meta
- `StorePaymentIntent` or `StorePayment`
  - order
  - amount/currency
  - provider/reference/status
  - raw callback payload

## Suggested Status Model

- `DRAFT`: cart/checkout draft before final submission.
- `SUBMITTED`: buyer submitted direct order.
- `QUOTE_REQUESTED`: no price exists; admin must quote.
- `PRICE_CONFIRMED`: admin confirmed/edited final price.
- `PAYMENT_PENDING`: buyer must pay or transfer.
- `PAID`: payment confirmed.
- `FULFILLMENT_PENDING`: payment done, warehouse/logistics pending.
- `READY_FOR_PICKUP`: product ready at origin.
- `SHIPPED`: shipment started.
- `DELIVERED`: buyer received goods.
- `COMPLETED`: commercial workflow closed.
- `CANCELLED`: cancelled by buyer/admin.
- `EXPIRED`: quote/order expired.

## Frontend UX

### Product List

- Priced active product: CTA = `خرید`, route to product detail or add-to-cart.
- No price but inquiry-enabled product: CTA = `استعلام قیمت`, route to direct quote request, not `/orders`.
- Out-of-stock product: CTA = `ثبت سفارش`, route to direct backorder/request flow, not `/orders`.

### Product Detail

- Primary panel should support quantity entry, selected offer/delivery, and direct action.
- `خرید` adds the product to cart or opens checkout.
- `استعلام قیمت` creates a direct quote request.
- `ثبت سفارش` creates a direct store order with `QUOTE_REQUESTED` or `SUBMITTED` depending on availability rules.

### Cart / Checkout

- `/cart`: current selected items, quantity, price snapshot preview, remove/update quantity.
- `/checkout`: authenticated final submission, buyer contact, destination, delivery notes, payment method.
- `/account/purchases`: buyer direct purchase history.

### Admin Dashboard

- Add a "Direct Sales" section separate from marketplace order requests.
- Admin can view, filter, open, status-change, cancel, and confirm payment for direct orders.
- Admin can see locked item snapshots so old catalog edits do not rewrite historical orders.

## Security & Permissions

- Cart may be local/client-side before login, but final checkout must require authentication.
- Final checkout should require at least active user account; KYC can be required before payment or large orders.
- Admin endpoints require staff/admin role.
- Payment callbacks must be idempotent.
- Direct order status changes must be audited.

## Functional Requirements

### FR-1 Direct Checkout Separation

Direct product purchases MUST be represented separately from marketplace `OrderRequest` records.

### FR-2 Product CTA Routing

Product list/detail CTAs MUST route to direct store flows and MUST NOT create marketplace order requests for Kaveh-owned catalog products.

### FR-3 Price Snapshot

When a priced order is submitted, the system MUST lock product title, offer, delivery origin, quantity, unit price, and total price on the order item.

### FR-4 Quote Request

When no valid price exists, the system MUST create a direct quote/order in a quote status instead of pretending the item can be paid immediately.

### FR-5 Admin Review

Admins MUST be able to see direct sales orders in a dedicated dashboard section with status, buyer, items, amount, and timestamps.

### FR-6 Payment Readiness

The first implementation MAY use manual/offline payment confirmation, but the data model MUST leave a clean place for future gateway transactions and callbacks.

## Acceptance Criteria

- A priced product can be added to cart and submitted as a direct store order.
- A price-less product creates a direct quote request.
- An out-of-stock product creates a direct backorder/order request in the store-sales context.
- Product CTAs no longer route direct product actions to `/orders`.
- Admin sees direct sales orders separately from KYC and marketplace order requests.
- Order item price/spec/origin snapshots remain stable after catalog edits.
- Backend tests cover priced checkout, quote checkout, inactive product rejection, and admin listing.
- Frontend build and lint pass.

## Metrics

- Direct checkout submissions per day.
- Quote requests per product category.
- Quote-to-order conversion rate.
- Payment pending aging.
- Cancelled/expired direct sales orders.

## Rollout Plan

1. Add backend `sales`/`checkout` app with direct order models, serializers, viewsets, and tests.
2. Add `/cart` and `/checkout` frontend routes.
3. Update product list/detail CTAs to use direct store routes.
4. Add admin dashboard direct-sales section.
5. Add manual payment confirmation and status history.
6. Integrate real payment gateway after the MVP status model is stable.

## Open Questions

- Should checkout require full KYC immediately or only before payment/large orders?
- Which payment gateway will be used first?
- Is quantity unit always ton, kg, or product-dependent?
- Should direct quote expiration be automatic after N hours?
- Should the platform reserve inventory when checkout is submitted, or only after payment confirmation?
