## ADDED Requirements

### Requirement: Structured Lead Extraction
The assistant SHALL convert a customer's free-text steel inquiry into a structured lead, extracting the available fields (product type, size/thickness, grade, factory/origin, quantity, city). When a concrete need is stated, the assistant SHALL record an inquiry, attempt to match it to a catalog product and snapshot that product's price, attach the conversation's captured contact, and mark the conversation as a lead. Admins SHALL review these structured inquiries and update their pipeline status; the extracted fields themselves are immutable from the admin API.

#### Scenario: Free-text inquiry becomes a structured lead
- **WHEN** a customer writes «۲۰ تن میلگرد ۱۴ اصفهان میخوام»
- **THEN** an inquiry is stored with product=میلگرد, size=14, factory=اصفهان, quantity=۲۰ تن, matched to a catalog product with its price when one exists, and visible in the admin inquiries list

#### Scenario: Operator works the lead
- **WHEN** an admin opens the inquiries tab
- **THEN** each inquiry shows its summary, matched product/price, captured contact, and a status the admin can move through (new → quoted → contacted → won/lost)
