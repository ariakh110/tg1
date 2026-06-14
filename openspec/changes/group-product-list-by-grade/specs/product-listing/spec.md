## ADDED Requirements

### Requirement: Product List Grouped by Grade
The product price list SHALL group products by steel grade, rendering one titled section per grade (e.g., «لیست قیمت ST52»), with grade-less products under a «سایر گریدها» section. Each row SHALL still display its factory and delivery/seller, so grouping by grade does not hide that information.

#### Scenario: Multiple grades under one factory
- **WHEN** a category contains products of several grades from the same factory
- **THEN** the list shows a separate titled section per grade rather than one section per factory

#### Scenario: Grade-less products
- **WHEN** a product has no steel grade set
- **THEN** it appears under the «سایر گریدها» section
