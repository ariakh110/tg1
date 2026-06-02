## Context

Direct sales already have `StoreOrder`, payment deadlines, remaining-amount calculation, manual `StorePayment` confirmation, and user/admin dashboards. Marketplace trades use `Order` after offer acceptance; `OrderRequest` is only a listing. The MVP should extend these existing boundaries instead of introducing parallel order models.

## Decisions

- Add a dedicated `offline_payments` app with one payment model referencing exactly one source: `StoreOrder` or marketplace `Order`.
- Store each upload as an immutable receipt attempt so rejection history is retained.
- Keep existing payment-link behavior. `StoreOrder.payment_method` chooses `payment_link` or `satna_offline`.
- Approved direct Satna payments create idempotent `StorePayment(provider="satna_offline")` records and reuse remaining-amount logic.
- Approved marketplace Satna payments remain financial records only; operational `Order.status` is not changed automatically.
- Compute Satna deadlines at 10:00 in `Asia/Tehran`. Keep lazy expiry during reads and mutations as a fallback, and run Celery Beat deadline checks every minute.
- Store receipts locally in the MVP and serve them only through authenticated protected endpoints.
- Store managed Satna destination accounts in the database. Admins can add and edit multiple accounts, activate or deactivate non-primary accounts, and choose one active primary account.
- Snapshot destination-account details on payment initiation so later account edits do not change an existing payment instruction.
- Send transactional email through Django SMTP settings. Delivery failures are logged without rolling back financial actions.
- Send one idempotent reminder email two hours before each active deadline and one idempotent expiration email when a payment expires.
- Allow Satna only for amounts of at least `1_000_000_000` toman (`10_000_000_000` rial). Do not impose a software upper limit.

## Configuration

- `OFFLINE_PAYMENT_BANK_ACCOUNTS_JSON` remains an optional fallback when no managed database account exists.
- `OFFLINE_PAYMENT_PRIMARY_IBAN_ID=IBAN_01` selects the fallback account.
- `OFFLINE_PAYMENT_RECEIPT_MAX_SIZE_MB=5`
- Standard Django SMTP env settings
- `CELERY_BROKER_URL=redis://127.0.0.1:6379/0`
- `CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1`

Example account configuration:

```json
[{"id":"IBAN_01","bank_name":"بانک ملت","iban":"IR...","account_holder":"نام صاحب حساب"}]
```

## Deferred

CSV/XLSX reporting, accountant role, approval revert, S3, presigned URLs, ClamAV, and SMS remain later phases.

## Background Worker

Start Redis, one worker, and one Beat scheduler:

```shell
docker compose up -d redis
celery -A tg1 worker --loglevel=info
celery -A tg1 beat --loglevel=info
```

For local Windows development, start the worker with `celery -A tg1 worker --pool=solo --loglevel=info`.
