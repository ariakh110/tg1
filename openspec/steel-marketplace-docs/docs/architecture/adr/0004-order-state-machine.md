
# ADR-0004: Enforce Order Lifecycles with an Explicit State Machine

- **Status:** Accepted
- **Date:** 2026-01-02

## Context

Order flows are multi-step and depend on:

- payments,
- provider confirmations,
- physical events (loading, weighing, delivery),
- cancellations and timeouts.

Without strict transition rules, the system can enter inconsistent states (e.g., delivery confirmed without final payment).

We also need:

- consistent UI state rendering,
- predictable notification triggers,
- a clear audit trail.

## Decision

We will implement an explicit **state machine** for each order type (`BUY`, `CUT`, `SHIP`, `QC`, `COMBO`):

- A single function `transition(order, event, actor, payload)` validates:
  - allowed transitions,
  - actor permissions,
  - required preconditions (e.g., deposit exists and is paid),
  - side effects (emit domain events).
- Side effects (notifications, scheduling, payout release) are triggered by **domain events**, not by ad-hoc code in viewsets.
- Status changes are recorded in an immutable **OrderStatusHistory** table.

## Consequences

### Positive

- Prevents invalid transitions and reduces production incidents.
- Centralizes workflow logic and makes it testable.
- Provides a clean integration point for timeouts (Celery) and automation.

### Negative

- Requires discipline: all status updates must go through the state machine.
- Adds upfront complexity in the domain layer.

## Alternatives considered

1. “Just update status fields” inside view logic
   - Simple but error-prone and hard to maintain
2. Use a third-party workflow engine
   - Powerful but too heavy for MVP

## Notes

We will start with a small set of statuses (MVP), and extend as needed. Avoid over-modeling from day one.
