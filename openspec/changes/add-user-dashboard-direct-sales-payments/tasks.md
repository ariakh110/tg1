## 1. Backend

- [x] 1.1 Extend `StoreOrder` with payment deadline, payment link, and admin notes fields.
- [x] 1.2 Add `StoreOrderNotification` for SMS/email/system send audit.
- [x] 1.3 Add migrations and indexes for payment deadline and notification lookup.
- [x] 1.4 Add user dashboard summary endpoint.
- [x] 1.5 Add user payment list and pending payment endpoints.
- [x] 1.6 Add user direct order detail endpoint with timeline and payment link fields.
- [x] 1.7 Add admin direct order PATCH/edit support.
- [x] 1.8 Add admin payment deadline update support.
- [x] 1.9 Add admin payment link generate/refresh action.
- [x] 1.10 Add admin send payment link action with SMS-provider abstraction and skipped/failed logging.
- [x] 1.11 Add tests for user visibility, pending payments, overdue flags, admin edit, status transition, payment link generation, and SMS logging.

## 2. Frontend

- [x] 2.1 Add user dashboard shell with sidebar/top summary similar to admin dashboard.
- [x] 2.2 Add overview cards for active orders, pending payments, overdue payments, and completed orders.
- [x] 2.3 Complete `/cart` with item list, quantity update, remove, empty state, and checkout entry.
- [x] 2.4 Expand `/account/purchases` into direct order history with filters.
- [x] 2.5 Add payments/pending payments view with deadline and payment link.
- [x] 2.6 Add direct order detail/timeline view.
- [x] 2.7 Expand admin direct-sales panel with edit form, due date, status action, payment link, and SMS send action.
- [x] 2.8 Add clear Persian status labels and next-action copy.

## 3. Validation

- [x] 3.1 Run `python manage.py makemigrations --check --dry-run --settings=tg1.settings_test`.
- [x] 3.2 Run `python manage.py check`.
- [x] 3.3 Run `python manage.py test --settings=tg1.settings_test`.
- [x] 3.4 Run `npm run lint`.
- [x] 3.5 Stop Next dev processes if needed, then run `npm run build`.
- [x] 3.6 Smoke test user dashboard, cart, payments, order detail, admin direct-sales edit, payment link, and SMS-send action.
