# Design: Steel trade risk controls

## Data Model

`StoreOrder` gets explicit fields for controls that must be queryable and visible:

- `risk_status`: `PENDING`, `APPROVED`, `BLOCKED`
- `price_valid_until`
- `source_price_checked_at`
- `market_price_checked_at`
- `stock_verified_at`
- `proforma_confirmed_at`
- `loading_permission_at`

Free-form details, buyer acknowledgements, and future handbook-specific notes remain in `metadata.risk_control` so we do not create a table for every operational note.

## Backend Rules

- Priced direct orders set `price_valid_until` automatically.
- Quote orders can omit price validity until an admin prices them.
- Payment confirmation is rejected if `price_valid_until` has passed and payment is not already complete.
- Fulfillment statuses require:
  - payment status `PAID`
  - `stock_verified_at`
  - `proforma_confirmed_at`
  - `risk_status != BLOCKED`
- Admin risk-control changes write an order history event.

## Frontend Rules

- The product buy step requires buyer acknowledgements before adding the item to cart.
- Checkout passes buyer risk acknowledgements in metadata.
- Admin direct-sales edit form exposes the risk checklist and price validity time.
- Direct-sales list shows risk status and price validity state.

## Future Extensions

- Upload proforma, receipt, بارنامه, and source confirmation documents.
- Add SMS templates for payment deadline reminders.
- Add automated price refresh checks against market feeds.

