# Change: Add offline Satna receipt payment MVP

## Why

Buyers need a bank-transfer option beside the existing direct-sales payment-link workflow. Store operators need a controlled receipt review flow instead of confirming manual payments without uploaded evidence. Marketplace trades also need a receipt-backed payment record after an offer is accepted.

## What Changes

- Add an `offline_payments` Django app for Satna initiation, receipt upload, review, lock, expiry, audit, protected file access, and transactional email logs.
- Support direct `StoreOrder` payments and accepted marketplace `Order` payments while leaving `OrderRequest` listings unchanged.
- Add direct checkout payment-method selection and create Satna payments automatically for payable direct orders.
- Add a unified user Satna page and an admin-dashboard Satna receipt review panel.
- Read the primary bank account from environment-backed configuration and keep local receipt storage for the MVP.

## Impact

- Affected specs: `offline-satna-payments`, `direct-cart-weight-settlement`
- Affected backend: new `offline_payments` app, `sales` checkout/payment integration, marketplace accepted-offer amount snapshot
- Affected frontend: checkout, account navigation/payments, unified Satna page, admin dashboard
- Additive migrations required.
