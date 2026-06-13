## ADDED Requirements

### Requirement: Custom Head and Footer Scripts
The site settings SHALL include two admin-editable raw-markup fields, head scripts and footer scripts, for injecting third-party snippets (e.g., analytics, tag managers, verification tags, chat widgets) without a code change. Both fields SHALL be returned by the public settings endpoint and SHALL be updatable only by an admin via the settings PATCH. The frontend SHALL inject the head-scripts markup into the document `<head>` and the footer-scripts markup at the end of the `<body>`, and pasted `<script>` elements SHALL actually execute. Empty fields SHALL inject nothing.

#### Scenario: Admin saves analytics snippets
- **WHEN** an admin pastes a `<script>` snippet into the head-scripts field and saves
- **THEN** the snippet is stored and returned by the settings endpoint, and on every page the script is injected into `<head>` and runs

#### Scenario: Footer placement
- **WHEN** an admin sets the footer-scripts field
- **THEN** that markup is injected at the end of the `<body>`, not in the `<head>`

#### Scenario: Empty fields
- **WHEN** a script field is empty
- **THEN** nothing is injected for that placement and the page renders unchanged

#### Scenario: Non-admin cannot edit
- **WHEN** a non-admin attempts to PATCH the script fields
- **THEN** the request is rejected and the stored scripts are unchanged
