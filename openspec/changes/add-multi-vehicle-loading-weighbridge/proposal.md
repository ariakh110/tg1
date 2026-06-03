# Change: Add multi-vehicle loading and weighbridge slips

## Why

Direct steel orders above 25 tons require multiple trucks and multiple drivers, but the current direct-sales model stores only one driver and one vehicle. Customers also need access to one or more weighbridge slip images after loading.

## What Changes

- Add structured loading vehicles for direct store orders.
- Require enough active loading vehicles for orders whose loaded or estimated weight exceeds 25,000 kg before loading/shipping transitions.
- Add multiple weighbridge slip uploads for direct store orders.
- Show loading vehicles and weighbridge slips to customers in order detail.
- Keep legacy single-driver fields as a compatibility mirror of the first loading vehicle.

## Impact

- Affected specs: `direct-cart-weight-settlement`
- Affected backend: `sales` models, serializers, services, admin APIs, migrations, tests
- Affected frontend: admin direct-sales panel, customer order detail, store sales API helpers
