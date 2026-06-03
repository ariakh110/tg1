# Change: Add Satna financial report

## Why

Satna receipt review now supports partial payments and multiple receipt attempts, but finance users still lack a reconciliation report that totals only approved money movements.

## What Changes

- Add an admin Satna financial report endpoint with date, source type, bank account, and search filters.
- Calculate report totals from approved receipt attempts, not from the overall offline payment status or requested amount.
- Add CSV export for approved Satna receipt rows.
- Surface the report in the existing admin Satna panel.

## Impact

- Affected specs: `offline-satna-payments`
- Affected backend: `offline_payments` report service/view/URL/tests and receipt amount migration
- Affected frontend: Satna API helpers, user receipt amount input, admin Satna panel report
