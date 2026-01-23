
# UI/UX Design Guidelines (Marketplace Web App)

These guidelines describe how the Next.js frontend should present the marketplace workflows for a B2B steel trading and services platform.

---

## 1) UX principles for B2B marketplaces

1. **Trust is the product.** Make verification, contracts, payment milestones, and evidence visible.
2. **Clarity beats density.** Users will manage high-value orders; reduce ambiguity.
3. **Make the next step obvious.** Every order page should answer: “What happens next? What do I need to do?”
4. **Progressive disclosure.** Show key details first; allow expanding for technical specs.
5. **Audit-friendly UI.** Display timeline of events: offers, payments, confirmations, delivery.

---

## 2) Information architecture

### 2.1 Top-level navigation

- Dashboard (role-aware)
- Marketplace (RFQs visible to the current role)
- Orders
- Messages (negotiation per order)
- Notifications
- Wallet/Payments (if shown)
- Profile & Verification (KYC)
- Admin (admin-only)

### 2.2 Role switching

Since a user can have multiple roles, allow a **role context switcher**:

- Buyer view
- Seller view
- Cutter view
- Driver view
- QC view
- Admin view (if allowed)

The role switcher must change:

- dashboard widgets
- default landing pages
- marketplace feed filters

---

## 3) Onboarding and verification (KYC)

### 3.1 Onboarding steps

- Create account (phone/email)
- Add organization info (optional for buyer, required for sellers/providers)
- Select roles
- Upload verification documents (for sellers/providers)
- Bank account / payout setup (for providers)
- Admin approval status

### 3.2 Trust signals in UI

- “Verified” badges for sellers/providers
- Display:
  - number of completed jobs
  - average rating
  - response time (future)
- Show warehouse verification status if applicable

---

## 4) Core user journeys

### 4.1 Buyer journey: Create a BUY request (RFQ)

Form UX patterns:

- Step-by-step wizard:
  1) Material type & spec (product type, grade, dimensions)
  2) Quantity: estimated weight (tons/kg) + tolerance
  3) Delivery location & timeframe
  4) Optional services needed (cutting, QC, transport)
  5) Summary review and submit

Important UI details:

- Provide “common templates” for frequent materials (e.g., rebar, sheets).
- Allow file attachments (spec sheets, drawings).
- Show expected timeline after posting.

### 4.2 Buyer journey: Offer comparison and selection

Offer list should show:

- seller/provider name + verification badge
- price and what it includes
- lead time and warehouse origin
- payment terms (deposit %, milestone schedule)
- ratings and reliability metrics

Comparison features:

- Sorting by price, lead time, rating
- “Compare” view for 2–3 offers side-by-side
- A clear CTA: “Select this offer”

After selecting an offer:

- Lock the offer and show a “Payment timeline” card:
  - deposit due
  - seller confirmation pending
  - next installment due dates

### 4.3 Buyer journey: Payments and milestones

Payment UX must be explicit:

- Show:
  - total agreed price
  - paid so far
  - escrow/held amount
  - remaining balance
  - next payment due date

For weight adjustment:

- show initial estimate vs actual weight
- show computed adjustment and require confirmation before paying final

### 4.4 Buyer journey: Delivery confirmation

Delivery page includes:

- shipment timeline (picked up, in transit, delivered)
- proof evidence (optional):
  - photos at pickup/delivery
  - weighbridge ticket upload
- “Confirm delivery” action with a confirmation modal:
  - warn about releasing escrow funds
  - ask for issues/dispute option

---

## 5) Provider workflows

### 5.1 Seller dashboard

Widgets:

- New BUY requests matching seller’s inventory/service area
- Offers submitted and their status
- Orders awaiting seller confirmation
- Orders ready for loading
- Payment status summary

Offer creation UX:

- Quick offer form:
  - price
  - warehouse selection
  - lead time
  - deposit requirement and terms
  - notes

Seller confirmation UX:

- When deposit is paid, the seller sees:
  - “Confirm availability” CTA
  - required evidence (optional): upload stock proof, certificates

### 5.2 Cutter dashboard

- Requests for cutting jobs
- Ability to quote and schedule
- Upload completion evidence:
  - photos
  - final cut sheet report (optional)
- Completion confirmation flow

### 5.3 Driver dashboard

- Available SHIP requests:
  - pickup location
  - dropoff location
  - weight
  - preferred time
- Accept job flow:
  - confirm availability window
  - confirm truck capacity/type
- In-transit updates:
  - “Picked up”
  - “Arrived at destination”
- Delivery proof:
  - delivery photo
  - buyer signature (optional)

### 5.4 QC dashboard

- QC requests feed
- Quote + schedule
- Inspection workflow:
  - checklist
  - upload report
  - mark report submitted

---

## 6) Combined order (COMBO) UI

The combined order detail page should display:

- Header: main order ID + overall status + progress percentage
- **Timeline** of child tasks:
  - Goods purchase (BUY)
  - Cutting (CUT)
  - Transport (SHIP)
  - QC (QC)
- Each child task has:
  - its own status
  - assigned provider
  - payments status
  - action buttons relevant to the buyer/provider

Provide an “Orchestrated next step” panel:

- If BUY is not selected: “Wait for offers / select an offer”
- If BUY is selected but deposit unpaid: “Pay deposit”
- If BUY confirmed and cutting needed: “Select cutter offer”
- If goods ready and shipping needed: “Assign driver”

---

## 7) Notifications UX

- Notification center with filters:
  - Orders
  - Payments
  - Offers
  - Verification/Admin
- Use in-app notifications for all events.
- For critical events also send SMS/email:
  - deposit due
  - payment overdue
  - order cancellation
  - delivery confirmation required

---

## 8) Messaging and negotiation

Negotiation is common in B2B. Provide:

- Order-scoped conversation threads
- Attachments (PDFs, photos)
- System messages for state changes (immutable)
- Option to “Make revised offer” if negotiation is allowed later (future feature)

MVP can provide simple Q&A messages without counter-offer mechanics.

---

## 9) Accessibility and internationalization

- WCAG AA baseline:
  - keyboard navigation
  - proper labels/ARIA
  - contrast and readable typography
- Clear numeric formatting:
  - currency formatting
  - weight units
- Prepare for multilingual support if needed:
  - translation keys
  - avoid hard-coded strings

---

## 10) Error states, empty states, and resilience

- Empty state examples:
  - “No offers yet” with tips and expected response time
  - “No matching orders” for providers with configuration prompts
- Error states:
  - permission denied: show friendly explanation
  - payment failed: show retry + support path
  - invalid transition: show “You can’t do that yet” and what to do next

---

## 11) Admin UI guidance

Admin console should allow:

- user verification workflows (approve/reject with notes)
- dispute handling:
  - view order timeline + payments ledger
  - apply manual resolution actions (refund, release payout)
- global settings:
  - platform fee rates
  - timeouts (deposit deadlines)
  - service categories
