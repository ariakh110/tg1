# Change: Add BUY/SELL orders, expanded roles, and KYC (v1)

## Why
The platform needs transactional BUY/SELL flows with order-based offers, plus expanded roles and KYC gating, aligned to the latest marketplace documentation.

## What Changes
- Add BUY/SELL Order + OrderOffer core models and service-layer workflows (separate from `products.Offer`).
- Introduce KYC requests and expanded role definitions (multi-role, role activation on KYC approval).
- Add versioned API endpoints under `/api/v1` for orders/offers/kyc/roles.
- Preserve existing product/catalog models and endpoints; new flows are additive and do not change `products.*` schemas.

## Impact
- Affected specs: orders, users-roles-kyc
- Affected code: `accounts/`, `orders/`, `tg1/urls.py`, `tg1/settings.py`, `products/` (integration touchpoints)
- **Breaking**: database migrations for roles/KYC/orders (data migration needed if existing data must be preserved)
