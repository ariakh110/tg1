# Change: Steel trade risk controls for direct sales

## Why

The direct-sale flow must follow real steel-market controls from `Steel Trade Risk Control Handbook.md`: price validity, source/market checks, stock verification, payment deadline, no loading before confirmed payment, proforma documentation, and final-weight settlement.

## What Changes

- Add structured risk-control fields to direct `StoreOrder`.
- Set a price validity deadline for priced orders.
- Expose price-expiry and risk-blocker status in order APIs.
- Let admins update risk checks from the direct-sales dashboard.
- Block payment confirmation after price expiry unless the admin extends price validity.
- Block fulfillment/loading status transitions until payment and required risk checks are complete.
- Extend frontend pre-cart confirmations, checkout metadata, admin direct-sales form, and order list badges.

## Impact

- Affected specs: direct-steel-risk-control, direct-cart-weight-settlement
- Affected backend: `sales.StoreOrder`, serializers, services, admin APIs, tests
- Affected frontend: product buy step, checkout metadata, admin direct-sales dashboard, store-sales API helpers

