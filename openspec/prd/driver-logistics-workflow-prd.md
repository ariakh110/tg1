# Driver Logistics Workflow PRD

## Summary

Kaveh Metal needs an operational load-dispatch workflow for direct store orders. The experience should behave like a focused B2B version of Snapp/Uber freight: admins publish a load offer with full shipment details, eligible drivers see the offer in their own workspace, drivers accept or decline, and accepted drivers get a tracked delivery assignment.

The first implementation targets direct `StoreOrder` shipments only.

## Goals

- Let admins publish load offers for direct orders after payment and loading prerequisites are complete.
- Show drivers complete shipment details before they accept.
- Enforce capacity planning: each driver/truck covers at most 25 tons.
- Require multiple drivers for loads above 25 tons.
- Let drivers accept/decline offers, update delivery status, and upload shipment documents.
- Preserve an auditable timeline for dispatch, offer responses, assignment status changes, and uploaded evidence.

## Non-Goals

- Real-time GPS tracking.
- Driver pricing, bidding, wallet, or payout settlement.
- Automatic route optimization.
- Marketplace order logistics.
- External SMS/push notification provider integration.

## Users

- Admin/dispatcher: prepares shipment details, publishes offers, monitors acceptances and assignments.
- Driver: reviews load details, accepts/declines, performs pickup and delivery, uploads proof.
- Buyer: benefits from accurate order status later; buyer-facing tracking can be a later phase.

## Core Rules

- A shipment can be published only for direct store orders.
- A shipment can be published only when loading blockers are clear:
  - payment fully confirmed,
  - remaining amount is zero,
  - risk is not blocked,
  - stock is verified,
  - proforma is confirmed,
  - loading permission is recorded.
- Total shipment weight is calculated from final item weights when present; otherwise estimated item weights.
- If total weight is more than 25,000 kg, required driver count is `ceil(total_weight_kg / 25,000)`.
- Each accepted driver assignment receives a planned weight no greater than 25,000 kg.
- A delivery request is `ASSIGNED` only after enough drivers have accepted.
- Extra acceptances after capacity is filled must be rejected.

## User Stories

### Admin Publishes A Load Offer

As an admin, I can create a delivery request for a direct order, set pickup/loading notes, vehicle requirements, dispatch deadline, and target drivers.

The offer sent to drivers includes:
- order id,
- product summary,
- total order amount,
- buyer contact and destination,
- loading point snapshots,
- estimated/final weight,
- required driver count,
- planned per-driver weight limit,
- vehicle requirement,
- pickup window or deadline,
- dispatcher notes.

### Driver Reviews And Responds

As a driver, I can open my driver dashboard, see available load offers, review all details, and accept or decline.

When I accept:
- the system creates my assignment,
- the offer becomes accepted,
- the request tracks accepted driver count,
- if enough drivers accepted, the request becomes assigned.

### Driver Updates Shipment Status

As a driver with an assignment, I can move through the shipment lifecycle:

`ASSIGNED -> ACCEPTED -> ARRIVED_FOR_LOADING -> LOADED -> IN_TRANSIT -> DELIVERED -> PROOF_SUBMITTED`

Status changes must be logged.

### Driver Uploads Documents

As a driver, I can upload:
- bill of lading,
- weighbridge receipt,
- delivery receipt,
- loading/unloading photo,
- other shipment evidence.

Files are visible only to admins and the assigned driver in this phase.

## Admin UX

Admin dashboard gets a "حمل و رانندگان" panel:
- list delivery requests and assignment status,
- create a request by order id,
- select all or selected active drivers,
- see required driver count and accepted count,
- see offers and assignments per request.

## Driver UX

Account workspace gets `/account/driver`:
- offer list with accept/decline actions,
- assignment list with status actions,
- document upload for each assignment.

## API Shape

- `GET /api/v1/admin/dashboard/delivery-requests/`
- `POST /api/v1/admin/dashboard/delivery-requests/`
- `GET /api/v1/store/driver/load-offers/`
- `POST /api/v1/store/driver/load-offers/{id}/respond/`
- `GET /api/v1/store/driver/assignments/`
- `POST /api/v1/store/driver/assignments/{id}/transition/`
- `POST /api/v1/store/driver/assignments/{id}/documents/`

## Success Metrics

- Admin can publish an offer only for loading-ready orders.
- A 25-ton-or-less order requires one accepted driver.
- A 25-to-50-ton order requires two accepted drivers.
- A 50-to-75-ton order requires three accepted drivers.
- Drivers only see their own offers and assignments.
- Assignment status and document uploads are auditable.

## Open Questions For Later Phases

- Should drivers bid prices or accept a fixed freight price?
- Should offers expire automatically?
- Should buyer-facing live tracking be added?
- Should driver documents require admin review before order completion?
