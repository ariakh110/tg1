## MODIFIED Requirements

### Requirement: Admin-Managed Cluster Landings
Admins SHALL create keyword cluster landing pages through the admin panel. The family selector SHALL be populated from active root product categories with stable codes, including categories created after the frontend was built. Each active landing SHALL be served at `/category/<family>/<slug>` with server-rendered metadata, authored content, and products filtered by its family and optional grade. Public family hubs and sitemap entries SHALL support taxonomy-defined family codes rather than a fixed frontend allowlist.

#### Scenario: New taxonomy root appears in landing editor
- **WHEN** an admin creates an active root product category with code `raw-materials`
- **THEN** `raw-materials` appears as a selectable family when creating a landing without a frontend code change

#### Scenario: Landing for a new family renders publicly
- **WHEN** an active landing is saved with family `raw-materials` and a valid slug
- **THEN** `/category/raw-materials/<slug>` renders and the family is discoverable through the sitemap

#### Scenario: Child and inactive categories are excluded
- **WHEN** the landing editor loads taxonomy options
- **THEN** inactive categories, child categories, and categories without a code are not offered as landing families

#### Scenario: Existing legacy landing remains editable
- **WHEN** an existing landing references a family that is no longer in the active taxonomy options
- **THEN** the editor retains that current family value while editing instead of silently replacing it

