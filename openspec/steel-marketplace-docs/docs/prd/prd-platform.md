
# PRD — Steel Marketplace Platform (Buying, Selling & Industrial Services)

- **Product:** Online marketplace for steel products and related industrial services
- **Target users:** B2B (companies, workshops, logistics providers)
- **Backend:** Django + Django REST Framework
- **Frontend:** Next.js
- **Doc owner:** Product/Engineering
- **Date:** 2026-01-02
- **Status:** Draft (ready for implementation)

---

## 1) Summary

This platform enables buyers to:

1) Create purchase requests for steel materials (e.g., sheet, beam, rebar),
2) Receive competing offers from verified sellers,
3) Select an offer and execute a secure transaction using escrow-like payments,
4) Optionally request service orders (cutting, transport, QC) either standalone or as a combined workflow.

The platform also enables sellers and service providers (cutters, drivers, QC experts) to discover opportunities, bid/accept work, and get paid after successful completion.

---

## 2) Problem statement

Steel procurement and associated industrial services are often handled via:

- phone calls and fragmented messaging,
- low trust and high fraud risk (stock not available, quality mismatches),
- unclear payment commitments (large sums, multiple installments),
- logistics coordination problems (pickup/delivery timing),
- poor audit trails and dispute resolution.

The industry needs a **trusted, transparent workflow** to match demand with supply and execute transactions safely and efficiently.

---

## 3) Goals

### Business goals

- Increase transaction volume by improving trust and reducing friction.
- Create a scalable marketplace for multiple service categories beyond goods.

### User goals

- Buyers:
  - get competitive pricing quickly (RFQ model),
  - ensure stock availability and quality,
  - pay safely using milestones,
  - coordinate logistics and services from a single place.
- Sellers/providers:
  - access qualified leads,
  - reduce payment risk,
  - show credibility via verification and ratings.

### Platform goals

- Provide clear status tracking and audit trails for each order.
- Enforce strong permissions and safe financial workflows.

---

## 4) Success metrics (KPIs)

### Marketplace activity

- # of RFQs created per week
- RFQ → offer rate (percentage of RFQs receiving ≥ 1 offer)
- RFQ → selected offer rate
- Avg time to first offer and to selection

### Transaction completion

- Conversion to completed orders
- Cancellation rate by stage (pre-deposit vs post-deposit vs post-confirmation)

### Financial reliability

- Payment success rate (deposit, installment, final)
- Dispute rate and dispute resolution time
- Refund/adjustment frequency and time

### User satisfaction

- Ratings average per role category
- Net Promoter Score (future)

---

## 5) Personas & roles

### Buyer
- Construction companies, factories, project managers.
- Needs fast quoting, reliable delivery, correct specs.

### Seller
- Steel suppliers, warehouse operators.
- Wants quality leads and reliable payments.

### Cutter (Fabricator)
- Workshops providing cutting services.
- Needs clear job specs, drawings, scheduling, and payout.

### Driver / Logistics provider
- Independent truckers or transport companies.
- Needs pickup/delivery details, weight, and payment security.

### QC Inspector
- Quality inspectors and labs.
- Needs access to job details and a clear reporting workflow.

### Admin
- Approves users (KYC), handles disputes, manages fees and policies.

---

## 6) Scope

### MVP scope (Phase 1)

**User & verification**
- Account registration/login
- Multi-role selection
- KYC submission and admin verification for sellers/providers
- Basic profile with ratings placeholder

**Goods RFQ (BUY)**
- Buyer creates BUY request with:
  - product type + specifications (free text + structured fields)
  - estimated weight/quantity
  - delivery city + time window
- Sellers can view matching BUY RFQs
- Sellers submit offers (price + terms)
- Buyer compares and selects an offer

**Payments**
- Deposit payment required after offer selection
- Payment records stored with gateway reference
- Escrow-like holding (logical hold via ledger)
- Seller must confirm availability after deposit
- Installment payments (basic scheduling)
- Final weight adjustment and final payment before release

**Delivery (SHIP)**
- Buyer can create a shipping order linked to the BUY order (optional)
- Drivers can accept/offer for shipping
- Buyer confirms delivery

**Service RFQs (CUT, QC)**
- Create service RFQ
- Providers submit offers
- Buyer selects and pays
- Provider completes and buyer confirms

**Status tracking**
- Full order lifecycle status with history timeline
- Notifications for key events

**Reviews**
- Buyer can rate seller/provider after completion

### Post-MVP scope (Phase 2+)

- Automatic matching for drivers (Uber-style dispatch)
- Real-time GPS tracking
- Full seller inventory listings and browsing
- Partial fulfillment (multiple sellers per RFQ)
- Negotiation with counter-offers (structured)
- Multi-leg logistics (seller → cutter → buyer)
- Advanced analytics dashboards
- Fraud detection scoring

---

## 7) Core workflows

## 7.1 Goods Purchase Workflow (BUY)

1. Buyer posts BUY RFQ.
2. Platform notifies relevant sellers (by product type + geography).
3. Sellers submit offers.
4. Buyer selects one offer.
5. Buyer pays deposit.
6. Seller confirms stock availability.
7. Buyer pays remaining installments (schedule).
8. Seller prepares for loading.
9. Actual weight is recorded.
10. Final settlement is computed and paid.
11. Goods are released for transport.
12. Delivery occurs and buyer confirms.
13. Review can be submitted.

### Key constraints

- Seller cannot confirm delivery.
- Buyer cannot finalize without payment.
- Seller cannot access competitor offers.

## 7.2 Service Workflow (CUT, SHIP, QC)

Pattern:

1. Buyer posts service request with details.
2. Providers submit offers (or accept at fixed price).
3. Buyer selects provider.
4. Payment is collected (upfront or deposit).
5. Provider performs service.
6. Buyer confirms completion (or report submitted).
7. Provider payout is released.
8. Review can be submitted.

## 7.3 Combined Workflow (COMBO)

- Buyer creates a COMBO parent order that includes:
  - BUY child order
  - optional CUT child
  - optional QC child
  - optional SHIP child
- Child orders progress independently, but UI presents unified timeline.

Dependencies (MVP simplified):
- CUT starts after BUY is CONFIRMED.
- SHIP starts after BUY is READY_FOR_LOADING (or CUT completed).

---

## 8) Functional requirements

### 8.1 User & role management

- A user can hold multiple roles simultaneously.
- KYC requirements for:
  - sellers
  - cutters
  - drivers
  - QC experts
- Admin must approve verification.
- Role-based dashboards.

### 8.2 Orders

Fields required (minimum):

- `order_type`
- `buyer_id`
- `status`
- location fields (city, address)
- spec fields (varies by order_type)
- `parent_order_id` (optional)
- assigned provider id (optional)
- timestamps

### 8.3 Offers

- Provider can create an offer only if:
  - provider has required role
  - provider is verified
  - order is open
- Buyer can view all offers; providers can view only their own offer.
- Buyer can select exactly one offer (MVP).

### 8.4 Payments

- Support payment types:
  - deposit
  - installment
  - final adjustment
  - service fee payments
- Track:
  - amount
  - status
  - due dates (installments)
  - gateway transaction references
- Escrow: funds are held logically until milestones.

### 8.5 Weight adjustment

- Store:
  - estimated weight
  - actual weight
  - unit price (if applicable)
- System computes adjustment:
  - additional payment due or refund/credit
- Final payment required before “finalized” state.

### 8.6 Notifications

- Notify:
  - sellers/providers for new RFQs
  - buyer for new offers
  - buyer/seller for payment status changes
  - buyer for delivery confirmation requirement
  - admin for disputes or repeated failures

### 8.7 Reviews

- Reviews are linked to completed orders.
- Only participants can review each other.
- Role-specific review type.

### 8.8 Admin tools

- Verify users (approve/reject)
- View order timelines + payments
- Override/cancel orders in exceptional situations
- Resolve disputes (refund/release payout)

---

## 9) Non-functional requirements

### Security

- JWT auth, strong permissions
- Audit trail for financial and status actions
- Rate limiting on auth endpoints

### Reliability

- Payment operations must be transactional and idempotent
- Background jobs must be retry-safe
- Clear error messages and consistent API responses

### Performance

- Optimize order lists with indexes and select_related/prefetch_related
- Paginate all list endpoints

### Availability

- Target 99.5% uptime (post-MVP)
- Graceful degradation if external services fail (e.g., notifications provider outage)

---

## 10) Analytics events (suggested)

- `rfq_created`
- `offer_submitted`
- `offer_selected`
- `deposit_initiated`, `deposit_paid`
- `seller_confirmed`
- `installment_paid`
- `weight_recorded`
- `final_payment_paid`
- `shipment_assigned`
- `delivered_confirmed`
- `review_submitted`
- `order_cancelled` (include reason and stage)

---

## 11) Rollout plan

1. **Internal alpha** with a few verified sellers and buyers in one region.
2. Add service providers for cutting and logistics.
3. Expand geography and categories.
4. Introduce automation and dispatch improvements.

---

## 12) Risks and mitigations

- **Fraud / non-availability:** seller confirmation after deposit + penalties.
- **Payment disputes:** escrow ledger + audit + admin dispute workflows.
- **Logistics delays:** clear scheduling and status tracking; optional SLA.
- **User adoption:** onboarding assistance, verified badges, transparent fees.

---

## 13) Out of scope (explicit)

- Lending/credit scoring
- Cheque payment enforcement
- International shipping/customs
- Multi-seller partial fulfillment (MVP)

---

## 14) Open questions

- Exact legal constraints for escrow behavior in the target country.
- Payment gateway capabilities (split payout, delayed settlement).
- Required verification documents per role.
- How to represent material specs: fully structured vs semi-structured fields.
- Geographic matching rules: city-only vs radius-based GPS.
