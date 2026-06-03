# Change: Add Satna receipt approval reversal

## Why

Admins can now approve Satna receipt attempts and those approvals create financial effects. Finance operations need a controlled way to correct mistaken approvals without deleting audit history.

## What Changes

- Add an admin-only reversal action for approved Satna receipt attempts.
- Preserve the original receipt and mark it reversed with reviewer, timestamp, and reason.
- Reverse the linked direct `StorePayment` effect for direct orders and recalculate order payment state.
- Exclude reversed receipts from Satna financial reporting.
- Add UI controls for reversing approved receipts from the admin Satna panel.

## Impact

- Affected specs: `offline-satna-payments`
- Affected backend: receipt status choices, migration, services, serializers, views, URLs, tests
- Affected frontend: Satna API helper and admin receipt review panel
