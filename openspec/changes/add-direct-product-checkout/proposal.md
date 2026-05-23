# Change: Add Direct Product Checkout

## Why

The current `orders` feature is a marketplace board for user-submitted buy/sell requests. Kaveh Metal also needs a direct purchase flow for its own catalog products, with cart/checkout, direct sales orders, quote handling, admin review, and future payment integration.

Keeping these workflows separate avoids mixing direct platform revenue with marketplace RFQs and seller listings.

## What Changes

- Add a new direct store-sales capability for catalog products.
- Add direct sales order records with item-level snapshots of product, offer, price, specs, and origin.
- Add direct quote/backorder behavior for products without a price or out-of-stock products.
- Add buyer-facing cart/checkout and purchase history routes.
- Add admin-facing direct sales order management separate from marketplace order requests.
- Update product list/detail CTAs so direct product actions no longer route to `/orders`.
- Keep payment gateway integration optional in the first slice, while modeling payment state cleanly.

## Impact

- Affected specs: `direct-product-checkout`
- Affected backend: new `sales` or `checkout` app, `tg1/urls.py`, product CTA semantics, admin dashboard APIs, tests.
- Affected frontend: `/products`, `/products/[id]`, new `/cart`, new `/checkout`, account purchase history, admin dashboard direct-sales panel.
- Existing marketplace `orders` / `OrderRequest` behavior remains intact and separate.
