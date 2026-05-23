## 1. Backend

- [x] 1.1 Create `sales` or `checkout` Django app and register it.
- [x] 1.2 Add direct order, order item, status history, and payment models.
- [x] 1.3 Add migrations with indexes for buyer, status, created date, and payment status.
- [x] 1.4 Implement serializers that validate active products, active offers, quantity, and price availability.
- [x] 1.5 Implement buyer APIs for order create, retrieve, cancel, and list.
- [x] 1.6 Implement admin APIs for direct sales list/detail/status transition/payment confirmation.
- [x] 1.7 Add audit/status-history writes for every status change.
- [x] 1.8 Add backend tests for priced checkout, quote checkout, out-of-stock order, inactive product rejection, snapshot stability, and admin listing.

## 2. Frontend

- [x] 2.1 Add shared direct sales API helper functions.
- [ ] 2.2 Add full `/cart` route with item list, quantity update, remove, and empty state.
- [x] 2.3 Add `/checkout` route with buyer contact, delivery notes, summary, and submit behavior.
- [x] 2.4 Update `/products` CTA routes away from `/orders`.
- [x] 2.5 Update `/products/[id]` primary CTA and offer-row CTA away from `/orders`.
- [x] 2.6 Add `/account/purchases` for buyer direct purchase history.
- [x] 2.7 Add admin dashboard section for direct sales orders.

## 3. Validation

- [x] 3.1 Run `python manage.py makemigrations --check --dry-run --settings=tg1.settings_test`.
- [x] 3.2 Run `python manage.py check`.
- [x] 3.3 Run `python manage.py test --settings=tg1.settings_test`.
- [x] 3.4 Run `npm run lint`.
- [x] 3.5 Stop Next dev processes if needed, then run `npm run build`.
- [x] 3.6 Smoke test `/products`, `/cart`, `/checkout`, `/account/purchases`, `/admin/dashboard`, and backend `/api/v1/store/orders/`.
