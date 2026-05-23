## 1. Backend

- [x] 1.1 Add settlement-term and adjustment fields to `StoreOrder`.
- [x] 1.2 Add estimated/final/price weight fields to `StoreOrderItem`.
- [x] 1.3 Add migration for the new fields.
- [x] 1.4 Add quantity-unit validation and ton/kg/sheet conversion.
- [x] 1.5 Calculate estimated sheet weight from unit weight or dimensions.
- [x] 1.6 Calculate settlement-term fee and payment due date.
- [x] 1.7 Expose paid amount, remaining amount, and item weight fields in serializers.
- [x] 1.8 Add admin final-weight action and audit event.
- [x] 1.9 Update manual payment confirmation to default to remaining amount.
- [x] 1.10 Add tests for unit conversion, sheet count, settlement fee, final weight adjustment, and remaining amount.

## 2. Frontend

- [x] 2.1 Change product list/detail buy CTAs to add to cart.
- [x] 2.2 Add controlled Persian quantity unit selection to cart and checkout.
- [x] 2.3 Show estimated weight in cart/checkout and order detail.
- [x] 2.4 Add settlement-term selection to checkout.
- [x] 2.5 Show settlement fee, paid amount, remaining amount, and weight adjustment in user order detail/payments.
- [x] 2.6 Add admin final weight controls in direct-sales panel.
- [x] 2.7 Replace raw status/history event labels with Persian labels where visible to users.

## 3. Validation

- [x] 3.1 Run `python manage.py makemigrations --check --dry-run --settings=tg1.settings_test`.
- [x] 3.2 Run `python manage.py check --settings=tg1.settings_test`.
- [x] 3.3 Run `python manage.py test --settings=tg1.settings_test`.
- [x] 3.4 Run `npm run lint`.
- [x] 3.5 Stop Next dev processes if needed, then run `npm run build`.
- [x] 3.6 Smoke test add-to-cart, cart checkout, order detail, admin final weight, and remaining payment.
