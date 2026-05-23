## Context

Steel direct sales are priced operationally by weight, but some products are purchased by count. Sheet products are a special case because users often know the requested count and dimensions before exact loading weight is available.

The current direct store order model locks price snapshots but does not separate estimated and final weight. It also creates payable orders without modeling settlement term fee or remaining amount after a final loading adjustment.

## Goals

- Keep the current `sales` app and direct order flow.
- Add fields without breaking existing API consumers.
- Keep pricing based on the existing pricing tier unit price, assumed to be per ton.
- Let checkout accept ton, kilogram, and sheet count.
- Let admin set final weights after loading.
- Make remaining amount visible to both user and admin.

## Decisions

- Quantity unit values remain stable ASCII values in APIs:
  - `ton`
  - `kg`
  - `sheet`
- Persian labels are frontend-only display labels.
- `StoreOrderItem.estimated_weight_kg` stores the calculated initial weight.
- `StoreOrderItem.final_weight_kg` stores the exact loaded weight when available.
- `StoreOrderItem.price_weight_kg` stores the weight used for current item pricing.
- `StoreOrderItem.final_price_amount` stores the final recalculated amount after final weight.
- `StoreOrder.weight_adjustment_amount` stores the total final-weight delta.
- `StoreOrder.settlement_term_fee_amount` stores the extra fee for longer settlement terms.
- `remaining_amount` is computed from `total_amount - paid_amount` rather than stored.
- Multi-day settlement fee uses basis points in service code, with defaults that can later move to settings.

## Risks / Trade-offs

- If product dimensions are incomplete, sheet-count pricing cannot be safely calculated. The system will mark that item as needing quote.
- Existing price tier minimum quantities are treated as ton thresholds. Kilogram and sheet count are converted to ton before tier selection.
- Real gateway partial payment flows are still future work; manual payment confirmation can cover the remaining amount now.

## Migration Plan

1. Add order settlement fields.
2. Add order-item weight fields.
3. Keep nullable/default fields so existing orders remain readable.
4. Backfill is not required; old orders will show empty weight data.

## Open Questions

- Should the settlement-term fee rates be editable from admin later?
- Should overpayment create a credit balance in a separate finance ledger?
- Should exact weight require an uploaded باسکول document before status can move to shipped?
