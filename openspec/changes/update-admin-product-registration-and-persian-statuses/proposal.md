# Change: Simplify admin product registration and Persian status labels

## Why

Admin product registration has become too complex for a quick operational workflow. Optional pricing-condition fields can also reject product creation when unit text such as `mm` is submitted. Some user-visible order/status history entries still show raw English codes.

## What Changes

- Move pricing condition dimensions out of the primary product-registration path into an optional advanced section.
- Sanitize admin product numeric fields before submit.
- Make backend product upsert tolerant of unit-only optional pricing dimensions.
- Add Persian labels for missing direct-sales status-history events and admin direct-sales filters.
- Replace raw marketplace request status/event labels with Persian labels in visible request pages.
- Document the behavior in PRD and OpenSpec.

## Impact

- Affected specs: `product-taxonomy-admin`, `direct-cart-weight-settlement`, `user-account-workspace`
- Affected backend: `products/admin_import.py`, product admin-upsert tests
- Affected frontend: admin dashboard product form, direct-sales labels, marketplace request pages
- No database migration required.

