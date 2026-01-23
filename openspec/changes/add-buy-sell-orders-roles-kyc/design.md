## Context
The current codebase has product catalog and seller listing models, but no transactional order system. We need BUY/SELL order flows with offers and controlled state transitions, plus expanded roles and KYC gating.

## Goals / Non-Goals
- Goals:
  - Add BUY/SELL orders and offers with a service-layer state machine.
  - Add KYC requests and expanded roles (multi-role).
  - Expose new versioned endpoints under `/api/v1` without breaking existing endpoints.
- Non-Goals:
  - CUT/SHIP/QC orders in this phase.
  - External payment gateway integration (stub only if needed).

## Decisions
- Decision: Create a new `orders` domain (models, services, API) with Order and `OrderOffer` (do not reuse `products.Offer`).
- Decision: Keep existing product catalog and seller models intact; integrate by referencing `products.Product` where needed.
- Decision: Introduce a role association model (`UserRole`) to support multiple roles; keep legacy `Profile.role` temporarily for backward compatibility.
- Decision: Add KYCRequest model with status and document metadata; gate professional roles until approved.
- Decision: Use clear naming (`OrderOffer`) and `/api/v1` routes to avoid confusion with existing listing offers.

## Risks / Trade-offs
- Risk: Two different Offer concepts (product listing vs order offer). Mitigation: clear naming in code (`OrderOffer`) and separate API namespace.
- Risk: Data migration for existing users/roles. Mitigation: keep legacy field and populate new roles on migration.

## Migration Plan
- Add new tables for roles, KYC, orders.
- Backfill roles from existing `Profile.role` into `UserRole` on migration.
- Keep legacy endpoints intact; add `/api/v1` routes for new flows.

## Open Questions
- For SELL orders, should buyers be required to be verified before submitting offers?
