# Change: Add User Dashboard and Payment Operations for Direct Sales

## Why

Direct product checkout now creates Kaveh-owned store orders, but users still need a proper account dashboard to track orders, cart, pending payments, deadlines, and payment history. Admins also need stronger direct-sales operations: edit records, change statuses, set payment deadlines, generate payment links, and send payment links by SMS.

## What Changes

- Add a user dashboard for direct sales with overview, cart, orders, payments, pending payments, and history.
- Extend direct sales records with payment deadline and payment-link metadata.
- Add user-facing direct order detail/timeline views.
- Add admin direct-sales edit, status transition, due date, payment-link, and SMS-send actions.
- Add notification/audit records for payment-link sends.
- Keep direct sales separate from marketplace `orders` / `OrderRequest`.

## Impact

- Affected specs: `direct-sales-dashboard-payments`
- Depends on active change: `add-direct-product-checkout`
- Affected backend: `sales` models, serializers, views, urls, tests, migrations.
- Affected frontend: account dashboard routes, cart route, purchases/orders/payments pages, admin dashboard direct-sales panel.
- External integration: SMS provider abstraction; real provider can be skipped/logged in MVP.
