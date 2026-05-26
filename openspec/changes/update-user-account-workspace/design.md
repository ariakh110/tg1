# Design: User Account Workspace

## Context

Direct sales and marketplace load-board workflows are separate domains:

- Direct sales: buyer purchases products from Kaveh Metal catalog.
- Marketplace/load board: users publish buy/sell requests for their own market activity.

The UI must make this separation obvious.

## Decisions

### Decision: Use Workspace Shell for Account Area

`/account/*` will use a full-screen operational shell with fixed sidebar and sticky topbar. The public site header/footer will be hidden by `AppShell`.

Rationale:

- Repeated account tasks are operational, not marketing.
- The admin dashboard already uses this mental model successfully.

### Decision: Keep Routes Stable, Rename UI

Routes remain unchanged, but labels become domain-specific:

- `خریدهای من از کاوه` instead of generic `خریدها`
- `تالار اعلام بار` instead of `سفارشات`
- `تسویه‌ها` instead of generic `پرداخت‌ها`

Rationale:

- Avoid breaking links.
- Reduce user confusion without backend churn.

### Decision: Keep Cart and Checkout Outside Account Layout But Without Public Chrome

`/cart` and `/checkout` keep their focused pages, but public header/footer are hidden so the buyer workflow feels continuous.

## Risks

- Risk: hiding public header on `/orders` may make marketplace discovery less obvious.
  - Mitigation: use explicit title/copy: `تالار اعلام بار کاربران`.
- Risk: account pages that were built for narrow content may look sparse.
  - Mitigation: shell constrains content and keeps cards simple.

## Validation

- Run `npm run lint`.
- Run `npm run build`.
- Smoke-test `/account/dashboard`, `/account/purchases`, `/account/payments`, `/cart`, `/checkout?cart=1`, and `/orders`.

