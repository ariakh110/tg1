
# Engineering Rules (Backend: Django + DRF)

This document defines the engineering standards for the backend team. Treat this as the **source of truth** for how we write, review, and ship code.

---

## 1) Principles

1. **Correctness over cleverness.** Especially for payments, state transitions, and permissions.
2. **Thin controllers.** DRF views should orchestrate; business logic lives in domain/services.
3. **Explicit workflows.** Order states and transitions must be validated by the state machine.
4. **Security by default.** Least privilege, strict input validation, and safe error handling.
5. **Auditability.** Important actions must be traceable (who did what, when).

---

## 2) Repository conventions

### 2.1 Directory structure (recommended)

- `apps/`
  - `users/`, `orders/`, `offers/`, `payments/`, `notifications/`, `reviews/`, `audit/`, ...
- `config/`
  - Django settings, URL routing, WSGI/ASGI
- `tests/`
  - unit + integration tests

### 2.2 Environment config

- Use `.env` (local) and environment variables (staging/prod).
- Never commit secrets to git.
- Use separate credentials per environment.

---

## 3) Python & Django style

### 3.1 Formatting and linting

We enforce:

- `black` for formatting
- `isort` for imports
- `ruff` (or flake8) for lint rules
- `mypy` (recommended) for type checking

Rules:

- No manual formatting debates: **black wins**.
- Keep line length at 88 (black default) unless configured otherwise.

### 3.2 Naming

- Modules: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_CASE`

### 3.3 Type hints

- Add type hints for public functions in services and integrations.
- Use `TypedDict` or dataclasses for structured payloads.

### 3.4 Avoid anti-patterns

- Do not place complex business logic in serializers or viewsets.
- Avoid signals for business-critical workflows (signals are hard to trace/test). Prefer explicit service calls.

---

## 4) Django REST Framework rules

### 4.1 API design constraints

- Endpoints must be documented in OpenAPI (`openapi/openapi.yaml`).
- Use nouns for resources: `/orders`, `/offers`, `/payments`.
- Use explicit action endpoints only for domain transitions:
  - `/orders/{id}/choose-offer/`
  - `/orders/{id}/confirm-availability/`
  - `/orders/{id}/record-weight/`
  - `/orders/{id}/confirm-delivery/`
- Never change state with a `GET`. State changes must be `POST` or `PATCH`.

### 4.2 ViewSets vs APIViews

- Prefer `ModelViewSet` for standard CRUD.
- Prefer `APIView` for complex endpoints with non-standard shapes.
- Custom actions must be small and delegate to services.

### 4.3 Serializers

Rules:

- Keep serializers focused on validation and representation.
- Use separate serializers for:
  - Create/Update
  - Detail view
  - List view
- Never expose internal fields unless necessary (e.g., escrow ledger internals).

### 4.4 Permissions

- Implement RBAC + object-level permissions.
- No endpoint should rely only on frontend to hide data.
- For offers:
  - Sellers/providers can see only their own offers.
  - Buyer can see all offers for their order.
- For orders:
  - Buyer can see their own orders.
  - Provider can see orders they are assigned to, or orders visible in their “marketplace feed” (by role/geo).
- Admin endpoints are separated and protected.

### 4.5 Pagination, filtering, ordering

- Use cursor or page-number pagination consistently.
- Support filtering:
  - `type`, `status`, `city`, `created_at` ranges.
- Do not allow ordering by unindexed fields in large tables.

### 4.6 Versioning

- URL versioning is recommended:
  - `/api/v1/...`
- Breaking changes must create a new version or be additive only (avoid breaking clients).

---

## 5) Error handling standard

### 5.1 Response format

All non-2xx errors must follow:

```json
{
  "error": {
    "code": "ORDER_INVALID_TRANSITION",
    "message": "Cannot transition BUY order from DEPOSIT_PAID to FINALIZED.",
    "details": {
      "order_id": "ord_123",
      "from_status": "DEPOSIT_PAID",
      "to_status": "FINALIZED",
      "required": ["SELLER_CONFIRMED", "INSTALLMENTS_PAID"]
    }
  }
}
```

Rules:

- `code` is stable and machine-readable.
- `message` is human readable.
- `details` is optional; do not leak sensitive data.

### 5.2 Exceptions

- Use custom exceptions for domain errors:
  - `InvalidTransitionError`
  - `PermissionDeniedError`
  - `PaymentVerificationError`
- Map exceptions to the standard error response in a global exception handler.

---

## 6) Data consistency & transactions

### 6.1 Use atomic transactions

Any operation that:

- changes order status,
- creates/updates payment records,
- selects offers,
- triggers payouts,

must run inside `transaction.atomic()`.

### 6.2 Concurrency

- Use database constraints to enforce uniqueness where needed (e.g., one selected offer per order).
- Use `select_for_update()` for critical updates (offer selection, payment finalization) to prevent race conditions.

---

## 7) Payments & escrow rules

### 7.1 Idempotency

- Payment gateway callbacks can be retried.
- Store gateway transaction references and enforce uniqueness.
- Payment verification endpoints must be idempotent:
  - repeated calls should not create duplicate ledger entries.

### 7.2 Ledger

- Record all money movements as append-only ledger entries.
- Never “edit history”; create compensating entries if needed.

### 7.3 Payout release

- Payouts are released only when milestones are reached:
  - goods: delivered + no dispute (or explicit confirmation)
  - services: completion confirmation / report submission

---

## 8) Background jobs (Celery)

Use Celery for:

- sending notifications (SMS/email/push)
- scheduling expirations (e.g., deposit not paid in time)
- verifying gateway payments asynchronously
- generating periodic reports

Rules:

- Tasks must be **idempotent**.
- Tasks must tolerate retries.
- Use dead-letter handling (logging + admin alert) for repeated failures.

---

## 9) Logging & audit

### 9.1 Logging

- Use structured logs (JSON) in staging/prod.
- Log key events:
  - order created
  - offer submitted/selected
  - status transitions
  - payment initiated/verified
  - payout released
  - cancellation/dispute events

### 9.2 Audit trail

- Maintain `OrderStatusHistory` (immutable).
- Maintain `PaymentEventHistory` or ledger.

---

## 10) Testing strategy

### 10.1 Required test layers

- **Unit tests** for:
  - state machine transitions
  - payment/ledger computations
  - permissions
- **Integration tests** for:
  - endpoints with authentication
  - gateway callback simulation
- **Contract tests** (recommended):
  - ensure API responses conform to OpenAPI schemas

### 10.2 Tools

- `pytest` + `pytest-django`
- `factory_boy` for fixtures
- `freezegun` for time-based logic
- `responses` (or similar) for mocking external HTTP calls

### 10.3 Coverage

- Payments & transitions must be ≥ 90% coverage.
- For other modules, ≥ 70% is acceptable initially.

---

## 11) Security rules

- Use HTTPS everywhere.
- Store passwords using Django’s hashing only.
- Use JWT with short-lived access tokens and refresh tokens.
- Protect against:
  - Insecure direct object references (IDOR)
  - Missing authorization checks
  - Mass assignment vulnerabilities (serializer `fields` must be explicit)
- Validate file uploads:
  - size limits
  - content type checks
  - store in object storage; never serve directly from Django without controls
- Rate limit auth endpoints.

---

## 12) Code review checklist

Every PR must answer:

- Does this change introduce any **new state transitions**? Are they enforced by the state machine?
- Are permissions correct (RBAC + object-level)?
- Are payment flows idempotent?
- Are database queries efficient (avoid N+1)? Use `select_related/prefetch_related`.
- Are tests included for critical logic?
- Is logging/audit adequate for the new behavior?
- Is the OpenAPI spec updated if endpoints or payloads changed?

---

## 13) Definition of Done

A feature is done when:

- Implementation merged to main
- Tests pass in CI
- OpenAPI updated (if API changes)
- Migration applied (if schema changes)
- Observability: logs and metrics for critical events
- Security review for new endpoints
