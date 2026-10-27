## ADDED Requirements

### Requirement: Grouped existing destinations
The admin UI SHALL expose the existing 22 panel destinations and separate content destination through a shared registry, retaining canonical IDs and showing each destination once in the primary navigation.

#### Scenario: Full admin explores navigation
- **WHEN** a full admin opens the menu
- **THEN** dashboard and five task-oriented groups provide all existing destinations, and settings is not duplicated.

### Requirement: Permission-consistent destination search
The UI SHALL filter groups, destination search and recent shortcuts through the existing section authorization rules. Content management SHALL remain full-admin only. Search SHALL support current names, old labels, task keywords and normalized Persian/Arabic text.

#### Scenario: Restricted user searches for unavailable section
- **WHEN** a user permitted only products and bulk-price searches for settings or content
- **THEN** neither destination is offered and no new permission is granted.

#### Scenario: Operator searches an old label
- **WHEN** an authorized user searches for the old bulk-price label or the keyword قیمت
- **THEN** the existing bulk-price destination is available with its group context.

### Requirement: Reliable navigation state
The selected dashboard panel SHALL be reflected in validated URL state. Active navigation and breadcrumb SHALL match the visible permitted destination. Content management SHALL retain navigation continuity.

#### Scenario: Reload and browser history
- **WHEN** an authorized user reloads a panel URL or uses Back/Forward
- **THEN** the corresponding permitted section is restored without changing its business behavior.

#### Scenario: Invalid or unauthorized panel
- **WHEN** the URL identifies an unknown or unavailable destination
- **THEN** the UI falls back to a permitted destination rather than rendering the unavailable section.

### Requirement: Accessible mobile and keyboard navigation
The UI SHALL offer a searchable mobile drawer instead of requiring horizontal scrolling through all section buttons. Search and drawer SHALL support clear focus, Escape, focus return and keyboard selection.

#### Scenario: Mobile operator searches by purpose
- **WHEN** an authorized mobile user searches for کارخانه
- **THEN** the existing taxonomy destination is reachable and selection closes the drawer and identifies the current section.

#### Scenario: Keyboard operator cancels search
- **WHEN** the user opens destination search with Ctrl/Cmd+K and presses Escape
- **THEN** the search closes and focus returns to its trigger.
