## ADDED Requirements

### Requirement: Balanced Responsive Category Grid
The homepage SHALL derive its desktop category column count from the number of visible categories, with at most six columns, so rows are balanced. Tablet and mobile layouts SHALL retain readable three- and two-column limits.

#### Scenario: Ten categories are visible
- **WHEN** the homepage has ten visible category families on desktop
- **THEN** it renders two rows of five cards

#### Scenario: Categories are viewed on mobile
- **WHEN** the same category list is viewed at the mobile breakpoint
- **THEN** no row contains more than two cards and labels remain inside their cards

### Requirement: Continuous Right-to-Left Price Ticker
The live-price strip SHALL move continuously from right to left, with each new price entering from the right and each old price leaving from the left, without a visible jump when the animation repeats.

#### Scenario: Ticker animation loops
- **WHEN** one complete price sequence has moved through the header
- **THEN** the duplicate sequence occupies the identical position and motion continues without a reset gap or reverse movement

#### Scenario: Reduced motion is requested
- **WHEN** the browser reports `prefers-reduced-motion: reduce`
- **THEN** ticker animation is disabled while price text remains readable
