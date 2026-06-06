# Change: Add driver geo matching, expiry, and reassignment

## Why

The current driver workflow can publish offers, but dispatchers still need to choose drivers manually and drivers must refresh their page. High-tonnage dispatch needs a marketplace-like flow that finds verified nearby drivers, sends time-limited offers, and reassigns open capacity when drivers do not respond.

## What Changes

- Add operational driver profiles with location, availability, verification, vehicle, plate, capacity, and service radius.
- Add geo matching for nearby eligible drivers using coordinates or city/province fallback.
- Add offer TTL, notification audit fields, and internal notification logs.
- Add periodic expiry and reassignment tasks.
- Add admin APIs for driver matching, profile verification, and reassignment.
- Add driver APIs/UI for operational profile updates and admin/driver UI for matching and offer expiry.

## Impact

- Affected specs: `direct-sales-logistics`
- Affected backend: `sales` models, migrations, services, serializers, views, URLs, tasks, tests; `tg1.settings` Celery beat schedule
- Affected frontend: delivery API helpers, admin logistics panel, driver account page
