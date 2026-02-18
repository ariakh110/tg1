# PRD ? Order Requests Feed (Buy/Sell) v1.1

- **Product:** Marketplace Requests (RFQ / Sell Listings)
- **Target users:** B2B buyers, sellers, warehouse managers
- **Backend:** Django + Django REST Framework
- **Frontend:** Next.js
- **Doc owner:** Product/Engineering
- **Date:** 2026-02-01
- **Status:** Draft (for implementation)

---

## 1) Summary

This feature enables authenticated users to publish **trade requests** on a central feed:

- Buyers publish **BUY requests (RFQ)** for steel materials.
- Sellers publish **SELL requests (inventory listings)** for available stock.

Key difference: **SELL requests must be verified** by a warehouse manager (or warehouse system) before they become visible in the public feed, to prevent fake inventory.

---

## 2) Problem statement

The market lacks a **single, trusted board** that shows both demand and real, verified supply. Current flows are fragmented and prone to fake inventory, leading to wasted time and low trust.

---

## 3) Goals

### Business goals
- Increase marketplace trust and activity by showing verified supply.
- Reduce wasted effort caused by non-existent inventory.

### User goals
- **Buyers:** discover offers quickly and publish RFQs.
- **Sellers:** publish stock listings that are verified and trusted.
- **Warehouse managers:** validate stock without using a full WMS.

---

## 4) Success metrics (KPIs)

- **Approval ratio:** approved SELL requests / total SELL requests.
- **Feed activity:** daily active users viewing the feed.
- **Listing lifetime:** average duration a request remains active.
- **RFQ response rate:** percent of BUY requests that receive at least one offer.

---

## 5) Personas & roles

- **Trader (Buyer/Seller):** creates BUY or SELL requests.
- **Warehouse Manager:** verifies SELL requests and uploads/approves inventory evidence.
- **Admin:** monitors, audits, resolves disputes.

---

## 6) Scope

### MVP scope (Phase 1)

**Request management**
- Create, read, update, deactivate (soft-delete) requests.
- Maintain status history for each request.

**Warehouse verification**
- SELL requests start in `PENDING_WAREHOUSE`.
- Warehouse manager reviews and approves/rejects.
- Approved SELL requests appear in feed.

**Feed**
- Authenticated users can view the feed.
- Filter by request type (BUY/SELL), category, status.

### Out of scope
- Full WMS (only verification workflow is required).
- Public feed for anonymous users.

---

## 7) Core workflows

### 7.1 BUY request flow
1. Buyer creates a BUY request.
2. Request is immediately **ACTIVE** and visible in feed.
3. Sellers can respond with offers (in order subsystem).

### 7.2 SELL request flow
1. Seller creates a SELL request.
2. Status becomes **PENDING_WAREHOUSE**.
3. Warehouse manager reviews documents / stock evidence.
4. Status becomes **APPROVED** or **REJECTED**.
5. Approved SELL requests become visible in feed.

### 7.3 Deactivation flow (Soft delete)
1. User disables a request.
2. Status changes to **DEACTIVATED**.
3. Request no longer appears in feed.

---

## 8) Functional requirements

**FR-1:** Users must be able to create requests with:
- product type / category
- quantity and unit
- target price or price range
- loading and delivery locations

**FR-2:** Deactivation must be a **soft-delete**; the record remains in DB and status becomes `DEACTIVATED`.

**FR-3:** SELL requests are **not visible** in feed until warehouse approval.

**FR-4:** Warehouse manager must have a dashboard to review and approve/reject SELL requests.

**FR-5:** Feed should show only:
- `is_active = true`
- SELL requests with status = `APPROVED`
- BUY requests that are active

**FR-6:** Users must view their request history with current status and timeline.

**FR-7:** Any material edit to a SELL request after approval resets status to `PENDING_WAREHOUSE`.

---

## 9) Non-functional requirements

### Security
- Feed access requires JWT.
- Warehouse verification endpoint requires role + permission.

### Observability
- All status transitions must be written to `AuditLog` with actor ID.

### Performance
- Index on `(status, type, created_at)` for feed queries.
- Pagination for all list endpoints.

---

## 10) Integration & API hints

- **GET /api/v1/marketplace/feed/** ? approved requests for public feed
- **POST /api/v1/my/requests/** ? create BUY or SELL request
- **PATCH /api/v1/my/requests/{id}/** ? update / deactivate
- **POST /api/v1/warehouse/verify/{request_id}/** ? approve/reject SELL request

---

## 11) Analytics events

- `request_created`
- `request_deactivated`
- `warehouse_approved`
- `warehouse_rejected`
- `request_viewed`

---

## 12) Risks & mitigations

- **Risk:** old requests clutter the feed ? add TTL or expiration date.
- **Risk:** approved SELL requests are edited later ? reset to `PENDING_WAREHOUSE` on major edits.

---

## 13) Open questions

- Is physical inspection required or are documents sufficient for warehouse approval?
- Should warehouse approval expire after N days if stock isn?t sold?

---

## 14) Acceptance criteria

- User can deactivate their request; it disappears from feed.
- SELL requests are hidden until warehouse approval.
- User history shows all requests (including deactivated) with correct status.

---

## Architectural notes

- **State management:** use a ChoiceField with `DRAFT`, `PENDING_WAREHOUSE`, `APPROVED`, `REJECTED`, `DEACTIVATED`, `COMPLETED`.
- **Soft delete:** implement a custom manager that defaults to `is_active=True`.
- **Notifications:** on warehouse approval/rejection, notify the request owner.
