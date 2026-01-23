
# ADR-0001: Use Django REST Framework (DRF) for the Backend API

- **Status:** Accepted
- **Date:** 2026-01-02
- **Deciders:** Engineering + Product

## Context

The platform requires a robust backend to support:

- Multi-role users (buyer/seller/service providers/admin)
- RFQ/offer workflows and complex order status transitions
- Payment orchestration with escrow-like behavior
- Fine-grained authorization (role-based + object-level)
- A stable API contract for Next.js and future mobile clients
- Strong reliability and data consistency guarantees for high-value transactions

The team is using Python, and needs rapid development, strong community support, and proven patterns.

## Decision

We will implement the backend as a **Django monolith** and expose APIs using **Django REST Framework**.

Key implementation notes:

- Use a **custom User model** from day 1 (email/phone login flexibility).
- Use DRF **ViewSets + Routers** for standard CRUD, with explicit custom actions for business transitions (e.g., `choose_offer`, `confirm_availability`, `record_weight`, `confirm_delivery`).
- Enforce **permissions** at both role and object levels.
- Use **PostgreSQL** as the primary datastore.
- Use Celery for asynchronous side effects (notifications, timeout handling).

## Consequences

### Positive

- Mature ecosystem and batteries-included admin tools for KYC and dispute handling.
- DRF provides serializers, validation, permissions, throttling, pagination, and schema generation.
- Django ORM + Postgres supports transactional updates needed for payments and state transitions.
- Easier onboarding for Python developers.

### Negative

- A monolith can grow complex if boundaries are not enforced (needs app/module discipline).
- DRF custom actions can become messy if business logic is not kept out of views.
- Real-time features (live tracking) require additional tools (Django Channels) if needed later.

## Alternatives considered

1. **FastAPI**
   - Pros: high performance, type hints
   - Cons: less integrated admin/KYC tooling, more “build your own” for auth & admin
2. **Node.js (NestJS)**
   - Pros: consistent TS across frontend and backend
   - Cons: team is Python-oriented; payments and workflows benefit from Django’s admin & ORM maturity
3. **Microservices from day 1**
   - Pros: scalability/isolation
   - Cons: too much operational complexity for MVP; premature separation increases failure modes

## Notes

To prevent “fat views”, we will adopt a service-layer architecture (domain services + state machine) and treat DRF viewsets as a thin adapter layer.
