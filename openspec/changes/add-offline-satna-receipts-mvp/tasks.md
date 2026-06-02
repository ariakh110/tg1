## 1. Backend

- [x] 1.1 Add the `offline_payments` models, settings, migration, admin registration, and protected storage flow.
- [x] 1.2 Add Satna initiation, eligibility, listing, receipt upload, protected file, admin review, and unlock APIs.
- [x] 1.3 Integrate direct checkout payment method, quote-confirm Satna initiation, direct `StorePayment` confirmation, and marketplace accepted-offer amount snapshot.
- [x] 1.4 Add audit logs, lazy expiry, rejection lock, upload throttling, and SMTP notification logging.
- [x] 1.5 Add backend regression tests.
- [x] 1.6 Add Redis-backed Celery Beat tasks for idempotent deadline reminders and expiry notifications.

## 2. Frontend

- [x] 2.1 Add Satna API helpers and Persian labels.
- [x] 2.2 Add checkout payment-method selection and Satna next action.
- [x] 2.3 Add `/account/offline-payments` for bank details, countdown, upload, and status tracking.
- [x] 2.4 Link account payment surfaces to Satna and add the admin dashboard receipt-review panel.
- [x] 2.5 Add admin-managed Satna destination accounts with primary selection, activation controls, and payment snapshots.
- [x] 2.6 Surface failed Satna notification counts in the admin receipt panel.

## 3. Validation

- [x] 3.1 Run OpenSpec strict validation.
- [x] 3.2 Run Django migration check, system check, and full tests.
- [x] 3.3 Run frontend lint and production build.
- [x] 3.4 Smoke test Satna user and admin routes.
