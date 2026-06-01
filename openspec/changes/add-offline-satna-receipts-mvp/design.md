## Context

Direct sales already have `StoreOrder`, payment deadlines, remaining-amount calculation, manual `StorePayment` confirmation, and user/admin dashboards. Marketplace trades use `Order` after offer acceptance; `OrderRequest` is only a listing. The MVP should extend these existing boundaries instead of introducing parallel order models.

## Decisions

- Add a dedicated `offline_payments` app with one payment model referencing exactly one source: `StoreOrder` or marketplace `Order`.
- Store each upload as an immutable receipt attempt so rejection history is retained.
- Keep existing payment-link behavior. `StoreOrder.payment_method` chooses `payment_link` or `satna_offline`.
- Approved direct Satna payments create idempotent `StorePayment(provider="satna_offline")` records and reuse remaining-amount logic.
- Approved marketplace Satna payments remain financial records only; operational `Order.status` is not changed automatically.
- Compute Satna deadlines at 10:00 in `Asia/Tehran`. Expiry is applied lazily during reads and mutations.
- Store receipts locally in the MVP and serve them only through authenticated protected endpoints.
- Send transactional email through Django SMTP settings. Delivery failures are logged without rolling back financial actions.

## Configuration

- `OFFLINE_PAYMENT_BANK_ACCOUNTS_JSON`
- `OFFLINE_PAYMENT_PRIMARY_IBAN_ID=IBAN_01`
- `OFFLINE_PAYMENT_RECEIPT_MAX_SIZE_MB=5`
- Standard Django SMTP env settings

Example account configuration:

```json
[{"id":"IBAN_01","bank_name":"بانک ملت","iban":"IR...","account_holder":"نام صاحب حساب"}]
```

## Deferred

CSV/XLSX reporting, accountant role, approval revert, S3, presigned URLs, ClamAV, SMS, Celery, and Redis remain later phases.
