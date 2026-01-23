
# API Design Guidelines (REST)

These guidelines define how we design and implement REST APIs for the Steel Marketplace platform.

They apply to all endpoints under `/api/v1/`.

---

## 1) Core principles

- **Consistency** beats “cleverness”. Predictable APIs are easier to use and maintain.
- **Resource-first design**: model things as nouns (`orders`, `offers`, `payments`) rather than verbs.
- **Explicit workflows**: business transitions are represented as dedicated action endpoints.
- **Least privilege**: authorization rules are part of the API contract.
- **Backward compatibility**: breaking changes require a new API version.

---

## 2) Resource modeling

### 2.1 Canonical resources

- `users`
- `roles`
- `warehouses`
- `product-types`
- `orders`
- `offers`
- `payments`
- `reviews`
- `notifications`

### 2.2 Order as a unified concept

Orders use a single resource `orders` with `order_type`:

- `BUY` (goods RFQ)
- `CUT` (cutting service RFQ)
- `SHIP` (transport job)
- `QC` (inspection service)
- `COMBO` (parent container order)

Child orders reference `parent_order_id`. A UI client can display a combined workflow using `GET /orders/{id}` and `GET /orders?parent_order_id=...`.

---

## 3) Naming conventions

- Use **kebab-case** for URL paths: `/product-types`
- Use **snake_case** for JSON fields: `order_type`, `created_at`
- Use stable identifiers:
  - Prefer UUIDs for external IDs.
  - If using numeric IDs internally, return them but avoid encoding meaning into them.

---

## 4) HTTP methods

- `GET` — read-only
- `POST` — create or invoke an action that changes state
- `PATCH` — partial update
- `PUT` — full replacement (rarely used in this project)
- `DELETE` — delete (avoid for business objects; prefer soft-delete)

Rules:

- Never change state via `GET`.
- Business transitions should be explicit:
  - `POST /orders/{id}/choose-offer`
  - `POST /orders/{id}/confirm-availability`
  - `POST /orders/{id}/record-weight`
  - `POST /orders/{id}/confirm-delivery`
  - `POST /orders/{id}/cancel`

---

## 5) Status codes

Use standard codes:

- `200 OK` — successful read or action
- `201 Created` — resource created
- `202 Accepted` — async job accepted (rare, for long-running operations)
- `204 No Content` — successful delete/no payload
- `400 Bad Request` — validation error / bad input
- `401 Unauthorized` — missing/invalid token
- `403 Forbidden` — valid auth but not allowed
- `404 Not Found` — resource not found (avoid leaking existence in sensitive contexts)
- `409 Conflict` — state conflict (e.g., invalid transition, already selected offer)
- `422 Unprocessable Entity` — optional for semantic validation errors (we mostly use 400)
- `429 Too Many Requests` — rate limiting
- `500/502/503` — server errors

---

## 6) Pagination

All list endpoints must be paginated.

Recommended parameters:

- `page` (1-based)
- `page_size` (bounded, e.g. max 100)

Response shape:

```json
{
  "count": 120,
  "next": "/api/v1/orders?page=3",
  "previous": "/api/v1/orders?page=1",
  "results": [...]
}
```

---

## 7) Filtering & sorting

Support query parameters where needed:

- Orders:
  - `type=BUY|CUT|SHIP|QC|COMBO`
  - `status=POSTED|...`
  - `city_id=...` or `origin_city_id=...`
  - `created_after`, `created_before`
  - `parent_order_id`
- Offers:
  - `order_id`
  - `created_after`, `created_before`

Sorting:

- Use `ordering` parameter:
  - `ordering=created_at` or `ordering=-created_at`
- Only allow ordering by indexed fields.

---

## 8) Authentication & authorization

### 8.1 Authentication

- Bearer JWT tokens:
  - `Authorization: Bearer <token>`

### 8.2 Role-based authorization (RBAC)

- A user may have multiple roles.
- Endpoints must enforce:
  - Only sellers can submit offers to BUY orders.
  - Only cutters can submit offers to CUT orders.
  - Only drivers can accept/offer on SHIP orders.
  - Only QC experts can offer on QC orders.
  - Only buyer (requester) can choose an offer.

### 8.3 Object-level authorization

- Buyer can access their own orders and related offers/payments.
- Providers can access orders they are assigned to.
- Providers can access open “marketplace feed” orders that match their role + geography.
- Providers cannot see competitors' offers.

---

## 9) Error format

All errors must follow:

```json
{
  "error": {
    "code": "SOME_ERROR_CODE",
    "message": "Human readable message",
    "details": { "optional": "context" }
  }
}
```

- `code` is stable.
- `message` is safe for display.
- `details` must not leak sensitive information.

---

## 10) Idempotency

Idempotency is required for:

- payment verification callbacks
- critical transitions where double-submission is likely

Recommended:

- Support `Idempotency-Key` header for payment initiation endpoints.
- Use unique constraints to prevent duplicates.

---

## 11) File uploads

Use pre-signed uploads to object storage where possible.

- For cutting drawings, QC reports, certificates:
  - `POST /uploads/presign`
  - client uploads directly to storage
  - server stores file metadata + reference

Validate:

- file type (MIME)
- maximum size
- malware scanning (future)

---

## 12) State transitions as first-class actions

Represent transitions explicitly:

- `choose_offer`: buyer selects provider offer
- `confirm_availability`: seller confirms inventory (BUY)
- `record_weight`: seller or authorized actor records actual weight
- `confirm_delivery`: buyer confirms delivery
- `cancel`: user cancels (with reason), subject to policy

Every action:

- validates permissions
- validates current status
- records status history event
- triggers notifications

---

## 13) API versioning and compatibility

Rules:

- Do not break response fields (remove/rename) in v1.
- Additive changes are ok:
  - adding new optional fields
  - adding new endpoints
- For breaking changes:
  - create `/api/v2/...`
  - maintain v1 until clients migrate

---

## 14) Documentation

- All endpoints must be reflected in `openapi/openapi.yaml`.
- Add examples for request/response bodies for critical flows (orders, payments).
- Update docs in the same PR as the API change.
