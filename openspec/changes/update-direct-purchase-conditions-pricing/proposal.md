# Change: Direct purchase conditions and pricing basis

## Why

Direct purchase currently assumes a single ton-based price and lets users reach the cart without choosing all commercial conditions. Steel products, especially sheets, need controlled purchase dimensions and explicit price basis so kg, ton, and sheet-count pricing are not mixed.

## What Changes

- Add explicit pricing basis to product pricing tiers: per ton, per kilogram, or per sheet.
- Allow admins to attach sheet pricing dimensions/labels to pricing tiers.
- Add a controlled pre-cart purchase step where users select price/dimension, quantity unit, quantity, settlement term, and required risk confirmations.
- Preserve selected pricing tier and condition snapshots through cart, checkout, and direct store orders.
- Update admin product upsert and Excel template/import to support the new pricing fields.

## Impact

- Affected specs: direct-cart-weight-settlement, direct-product-checkout
- Affected backend: `products.PricingTier`, product serializers/import/template, `sales` order calculation
- Affected frontend: product CTAs, new pre-cart purchase page, cart/checkout amount previews, admin product form
