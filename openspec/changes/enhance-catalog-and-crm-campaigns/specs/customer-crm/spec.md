## ADDED Requirements

### Requirement: Customer Product Interests
An authorized CRM operator SHALL be able to assign zero or more active product categories as a customer's explicit consumption interests. The API SHALL return those interests in customer list/detail data without modifying order history.

#### Scenario: Operator records galvanized-sheet consumption
- **WHEN** an operator assigns the galvanized sheet category to a customer
- **THEN** that customer is included in future audiences targeting galvanized sheet consumers

#### Scenario: Interest is removed
- **WHEN** an operator removes a product interest
- **THEN** the explicit relation is removed while past purchases remain unchanged

### Requirement: Purchase-Derived Product Consumer Segment
The CRM SHALL also identify a customer as a consumer of a product category when the customer's linked website account has a qualifying order item in that category or one of its descendants.

#### Scenario: Customer bought a black-sheet product
- **WHEN** a linked customer has a non-cancelled website order containing a black-sheet product
- **THEN** a black-sheet consumer preview includes the customer even without an explicit interest

#### Scenario: Same customer matches two sources
- **WHEN** a customer has both an explicit interest and a matching purchase
- **THEN** the audience contains that customer only once
