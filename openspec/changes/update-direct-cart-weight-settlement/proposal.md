# Change: Update direct cart, quantity units, and weight settlement

## Why

Direct sales currently behaves too much like immediate checkout. Buyers need to collect multiple products in a cart, choose market-appropriate units, and settle the whole cart. Steel orders also require estimated weight before loading and exact weight after loading, with settlement of any payment difference.

## What Changes

- Product buy CTAs add items to the direct cart instead of starting immediate checkout.
- Checkout submits the whole cart as one direct store order.
- Quantity units are controlled: ton, kilogram, and sheet count for sheet products.
- Store order items keep estimated and final weights.
- Admin can register final loading weight and the system recalculates the order amount.
- Store orders expose paid amount, remaining amount, settlement-term fee, and weight-adjustment amount.
- Settlement deadline is driven by selected settlement term days; multi-day settlement adds a fee.
- User-facing direct sales UI uses Persian labels for status/events and settlement wording.

## Impact

- Affected specs: direct-product-checkout, direct-sales-dashboard-payments
- Affected backend: `sales` models, serializers, services, views, tests, migrations
- Affected frontend: product CTAs, cart, checkout, user dashboard/order detail/payments, admin direct-sales panel
- Migration required for new order/item settlement and weight fields
