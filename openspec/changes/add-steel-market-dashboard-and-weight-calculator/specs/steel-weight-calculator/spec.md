## ADDED Requirements

### Requirement: Multi-Section Steel Weight Calculation
The system SHALL calculate theoretical weight for rebar, sheet, circular pipe, rectangular or square hollow section, angle, channel, and I-beam using shape-specific dimensions or a published standard linear weight.

#### Scenario: Visitor calculates rebar weight
- **WHEN** a visitor enters a 14 mm diameter, 12 metre length, and quantity of one
- **THEN** the calculator returns the theoretical per-metre and total weight using the `d²/162` formula

#### Scenario: Visitor calculates a hollow section
- **WHEN** the wall thickness leaves a positive internal width and height
- **THEN** the calculator returns weight from the steel cross-sectional area and selected density

#### Scenario: Visitor enters impossible geometry
- **WHEN** a wall thickness, diameter, width, height, or length makes the section physically invalid
- **THEN** the calculator explains the invalid field and does not display a misleading result

### Requirement: Standard And Custom Linear Weights
The system SHALL provide versioned standard kg/m choices for channel and I-beam sections and SHALL allow a custom kg/m value for an unlisted manufacturer section.

#### Scenario: Standard beam size is selected
- **WHEN** a visitor selects a bundled beam size and standard
- **THEN** the calculator uses and displays that table's kg/m value and standard name

#### Scenario: Factory certificate differs
- **WHEN** a visitor supplies a custom kg/m from a factory certificate
- **THEN** the calculator uses the custom value and labels the result as certificate-based

### Requirement: Useful Weight Results
The system SHALL show weight per metre or unit, total kilograms, total tonnes, the applied formula or standard, and an optional estimated total value from a visitor-entered price per kilogram.

#### Scenario: Price estimate is requested
- **WHEN** the visitor enters a positive price per kilogram after a valid weight calculation
- **THEN** the calculator displays the estimated total value with Persian number formatting
- **AND** labels it an estimate rather than a binding quote

#### Scenario: Price is omitted
- **WHEN** the visitor calculates weight without entering a price
- **THEN** weight results remain complete and the page offers a route to current products or price inquiry

### Requirement: Calculation Disclosure And Accessibility
The system SHALL label formula results as theoretical, state the default steel density, warn about manufacturing tolerance, and keep all calculations usable by keyboard and on mobile screens.

#### Scenario: Result is displayed
- **WHEN** any valid calculation completes
- **THEN** the result identifies the density or standard used and advises using certified or weighbridge weight for settlement

#### Scenario: Visitor uses a mobile device
- **WHEN** the calculator viewport is narrow
- **THEN** inputs, result summary, and actions remain readable without horizontal page scrolling
