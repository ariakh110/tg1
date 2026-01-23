
# ADR-0003: Escrow & Milestone Payments Using an Internal Ledger

- **Status:** Accepted
- **Date:** 2026-01-02

## Context

Transactions are high-value and multi-party. We must reduce fraud and disputes by:

- Taking **deposit / installments** before allowing the workflow to continue.
- Holding funds until conditions are met (“escrow-like”).
- Supporting partial refunds/adjustments (e.g., final weight differs from estimate).
- Charging platform fees and paying out providers.

Payment gateways often confirm payments asynchronously, and callbacks can be retried (idempotency needed).

## Decision

We will implement escrow-like behavior using:

1. A **Payment** record for each gateway transaction (deposit, installment, final, service fees).
2. An **internal ledger** (append-only `LedgerEntry` table) to track value movements:
   - buyer -> escrow
   - escrow -> seller/provider payout
   - escrow -> refund
   - platform fee accrual
3. A set of **release rules** tied to order status transitions:
   - Funds are released only after a defined milestone is reached (delivery confirmation, report submission, etc.)
4. Idempotent gateway callback handling using:
   - unique gateway reference
   - database constraints (unique index)
   - atomic transactions

## Consequences

### Positive

- Strong auditability for disputes and financial reconciliation.
- Supports complex flows (weight adjustment, cancellation, partial refunds).
- Clear accounting boundaries: escrow is represented explicitly in the ledger.

### Negative

- More engineering complexity than a simple “pay and transfer” approach.
- Requires careful operational controls and reconciliation tools.
- Depending on local regulations and gateway capabilities, “true escrow” may require special licensing.
  - **MVP** can still simulate escrow by delaying provider payouts until milestones, while legally the platform may be a payment facilitator.

## Alternatives considered

1. **Direct pay to provider at time of payment**
   - Pros: easy
   - Cons: high fraud risk; cannot safely handle disputes/adjustments
2. **Single payment only**
   - Pros: simpler
   - Cons: not feasible for large payments and weight-based adjustments
3. **Third-party escrow provider**
   - Pros: less financial responsibility
   - Cons: integration complexity and limited availability

## Notes

Even if legal constraints prevent holding funds, we can still use the ledger model to represent obligations and payout scheduling.
