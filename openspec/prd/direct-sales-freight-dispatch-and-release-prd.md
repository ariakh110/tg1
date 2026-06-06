# Direct Sales Freight Dispatch And Release PRD

## Summary

Direct sales orders need a logistics flow where dispatch starts before the physical weighbridge step, but release from the yard remains financially and operationally locked. Admins should publish freight requests with map-selected pickup and destination details, drivers or carriers should accept the offer, and final release should wait for final weight, full payment, and loading permission.

## Goals

- Let admins send a freight request from each direct sales order row without manually copying an order id.
- Allow freight dispatch before payment is fully settled and before final weight is known.
- Keep shipment release blocked until final weight, full payment, and loading permission are recorded.
- Support both drivers and carriers as freight recipients in v1.
- Preserve the existing 25,000 kg per-driver capacity rule and multi-driver split for heavier loads.
- Store pickup and destination coordinates using the current map provider abstraction so Neshan can be replaced later.

## Non-Goals

- Carrier fleet management or carrier-to-driver sub-assignment.
- Freight bidding, wallet, payout, or route-price calculation.
- Real-time GPS tracking.
- Direct integration with an external weighbridge system.

## Core Rules

- A freight request can be published for an active direct store order when:
  - the order is not terminal,
  - risk is not blocked,
  - price is not expired,
  - quote/proforma state is reliable enough for dispatch,
  - estimated or final shipment weight is available,
  - no active freight request already exists.
- A freight request does not require full payment, final item weight, stock verification, or loading permission.
- `FULFILLMENT_PENDING` means freight coordination has started.
- `READY_FOR_PICKUP`, `SHIPPED`, `DELIVERED`, `COMPLETED`, and driver transition to `IN_TRANSIT` require release blockers to be clear:
  - full payment confirmed,
  - remaining amount is zero,
  - final item weights recorded,
  - stock verified,
  - proforma confirmed,
  - loading permission recorded,
  - delivery capacity assigned for the order.
- For every 25,000 kg of total shipment weight, one accepted assignment is required.

## Admin UX

- The direct sales table shows a `درخواست باربری` action for each eligible order.
- The action opens a modal prefilled from the order:
  - order id and product summary,
  - vehicle type,
  - pickup province/city/address,
  - pickup coordinate selected from the map,
  - destination province/city/address,
  - destination coordinate selected from the map,
  - pickup window/deadline,
  - dispatcher notes,
  - automatic matching or selected recipients.
- Status changes show Persian blocker labels and never display raw API objects such as `{status:[...]}`.

## API Shape

- `StoreOrder` stores destination latitude and longitude.
- `StoreDeliveryRequest` stores pickup address plus a full destination snapshot and coordinates.
- Delivery request serializers expose pickup and destination fields.
- Delivery request creation accepts `recipient_type` and selected recipient ids while keeping the current driver fields backward-compatible.
- Carrier users use role `CARRIER` and can receive/accept/decline freight offers in v1 using the same offer model.

## Acceptance Criteria

- Admin can publish a freight request for a priced but unpaid direct order.
- The same unpaid order cannot be marked ready for pickup or shipped until final weight and payment blockers are cleared.
- Pickup and destination coordinates are saved on both the order and the delivery request snapshot.
- A load above 25 tons requires multiple accepted assignments.
- Drivers and carriers can both receive offers.
- Neshan renders through `InteractiveDeliveryMap`; changing the map provider does not require domain model changes.
