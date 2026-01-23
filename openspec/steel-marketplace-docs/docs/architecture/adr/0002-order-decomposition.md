
# ADR-0002: Composite Order Decomposition Using Parent/Child Orders

- **Status:** Accepted
- **Date:** 2026-01-02

## Context

The platform supports three types of customer intent:

1) Buy goods (steel products)
2) Request services (cutting, shipping, QC)
3) Combined workflow: goods + one or more services, potentially sequential and dependent

We need a model that can:

- Represent a single “customer job” that includes multiple tasks and providers.
- Track status and payments per task (seller vs cutter vs driver vs inspector).
- Allow independent cancellation, dispute, and completion per task while still showing a unified view.

## Decision

We will represent the overall customer request as a **parent order** (`order_type=COMBO`) and represent each goods/service task as a **child order** (`order_type` in `BUY/CUT/SHIP/QC`) linked via `parent_order_id`.

Key rules:

- Child orders are first-class orders: each has its own offers, payments, status lifecycle, and assigned provider.
- The parent COMBO order aggregates progress:
  - percent complete,
  - “current stage” (derived),
  - overall financial summary (derived).
- Cancellation propagation:
  - Cancelling the parent cancels all *not-started* child orders automatically.
  - If a child order is already in progress, parent cancellation moves to “PARTIALLY_CANCELLED” and requires admin review.

## Consequences

### Positive

- Simple, scalable representation of multi-step workflows.
- Clear separation of responsibilities and payouts per provider.
- Easier reporting: each job/task is measurable and auditable.

### Negative

- Requires careful UX to avoid confusing users with many order records.
- Requires explicit dependency management (e.g., shipping starts after goods are ready).
- Parent/child cascade logic must be thoroughly tested.

## Alternatives considered

1. **Single order with embedded tasks JSON**
   - Pros: fewer records
   - Cons: hard to query, hard to enforce permissions per task, complicated payments
2. **Separate tables per order type**
   - Pros: cleaner schemas per type
   - Cons: complex querying and polymorphism; harder to build unified lists and dashboards
3. **Workflow engine (BPMN)**
   - Pros: powerful orchestration
   - Cons: too heavy for MVP; adds tooling and operational complexity

## Notes

We will keep the database schema flexible by using a shared `Order` table + `order_type`, and by placing type-specific fields in JSON or separate detail tables only when required by complexity.
