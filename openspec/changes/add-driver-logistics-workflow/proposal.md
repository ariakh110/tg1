# Change: Add driver logistics workflow

## Why

Direct orders currently store only free-text driver fields, so dispatchers cannot publish detailed load offers, enforce truck capacity, collect driver acceptances, or track shipment documents.

## What Changes

- Add delivery request, driver offer, assignment, event, and document models for direct store orders.
- Enforce one driver/truck per 25 tons and require multiple accepted drivers for larger loads.
- Add admin dispatch APIs and driver offer/assignment APIs.
- Add admin logistics panel and driver workspace page.
- Add regression tests for capacity, access control, load readiness, driver acceptance, transitions, and document upload.

## Impact

- Affected specs: `direct-sales-logistics`
- Affected backend: `sales` models, services, serializers, views, URLs, migrations, tests
- Affected frontend: admin dashboard, account navigation, driver dashboard, logistics API helpers
