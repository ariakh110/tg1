## ADDED Requirements

### Requirement: Configurable Roll Weight
The weight of a roll in roll (coil) sales SHALL be configurable per product via the product's unit weight («وزن واحد» / `weight_kg_per_unit`, in kilograms). When set, that value SHALL be used as the weight of each roll for pricing and the estimated invoice; when not set, the system SHALL fall back to the standard default (22.5 ton for thickness ≥ 3mm, otherwise 20 ton). The admin product form SHALL provide a roll-weight input for رول (coil) products, where leaving it empty keeps the default.

#### Scenario: Configured roll weight is used
- **WHEN** a coil product has its unit weight set (e.g., 18000 kg) and a buyer orders one roll
- **THEN** the order uses 18 ton as the roll weight, the estimated weight is 18000 kg, and the selection is marked as using the configured weight

#### Scenario: Falls back to standard default
- **WHEN** a coil product has no unit weight set
- **THEN** the roll weight is 22.5 ton for thickness ≥ 3mm, otherwise 20 ton

#### Scenario: Admin can set it for rolls only
- **WHEN** an admin edits a sheet product whose process is رول (coil)
- **THEN** the product form shows a «وزن هر رول (kg)» input that saves to the product's unit weight, and this input is not shown for non-roll products
