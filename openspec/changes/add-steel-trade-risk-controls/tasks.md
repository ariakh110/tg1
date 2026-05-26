## 1. Documentation

- [x] 1.1 Create PRD from the risk-control handbook.
- [x] 1.2 Add OpenSpec proposal, design, tasks, and spec delta.

## 2. Backend

- [x] 2.1 Add risk-control fields to `StoreOrder`.
- [x] 2.2 Expose risk status, price validity, expiry, and blockers in serializers.
- [x] 2.3 Set default price validity for priced orders.
- [x] 2.4 Block expired-price payment confirmation.
- [x] 2.5 Block fulfillment/loading transitions until payment and risk checks pass.
- [x] 2.6 Add backend tests for expiry, risk blockers, and successful release.

## 3. Frontend

- [x] 3.1 Add risk labels/helpers to store sales API helper.
- [x] 3.2 Extend product buy acknowledgements.
- [x] 3.3 Send checkout risk metadata.
- [x] 3.4 Add admin risk checklist and price-validity controls.
- [x] 3.5 Show risk status and expiry signals in direct-sales list.

## 4. Validation

- [x] 4.1 Validate OpenSpec change.
- [x] 4.2 Run backend migration checks and tests.
- [x] 4.3 Run frontend lint/build.
