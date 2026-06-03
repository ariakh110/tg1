## 1. Backend

- [x] 1.1 Add reversed receipt status migration.
- [x] 1.2 Add admin reversal service/action with required reason and audit log.
- [x] 1.3 Reverse linked direct `StorePayment` and recalculate direct order payment state.
- [x] 1.4 Add regression tests for full-payment reversal, partial-payment reversal, report exclusion, and access control.

## 2. Frontend

- [x] 2.1 Add reversal API helper.
- [x] 2.2 Add admin UI action for approved receipts with required reason and refresh behavior.

## 3. Validation

- [x] 3.1 Run OpenSpec strict validation.
- [x] 3.2 Run Django migration check, system check, and relevant tests.
- [x] 3.3 Run frontend lint/build as feasible.
