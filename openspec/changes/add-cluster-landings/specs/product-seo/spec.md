## ADDED Requirements

### Requirement: Admin-Managed Cluster Landings
Admins SHALL create keyword cluster landing pages (e.g., «ورق ST52») via the admin panel, each with a family, slug, title, tagline, intro, authored HTML body, optional product grade filter, SEO metadata, and an optional related expert containing a portrait, name, role, mobile number, and phone extension. Each active landing SHALL be served at `/category/<family>/<slug>` as a server-rendered page with its own metadata, a `BreadcrumbList`, the authored content, a product grid filtered by the landing's family (and grade when set), and its configured expert. Empty expert fields SHALL not render. Landings SHALL appear in the sitemap and be linked from their family category page. Content is human-authored, not auto-generated.

#### Scenario: Admin creates a landing
- **WHEN** an admin saves an active landing with family «sheet» and slug «st52»
- **THEN** `/category/sheet/st52` renders server-side with the landing's title, body, and matching products, and the URL is listed in the sitemap

#### Scenario: Inactive or unknown landing
- **WHEN** a landing is inactive, or the family/slug does not match an active landing
- **THEN** the page responds as not-found

#### Scenario: Discoverable from the family page
- **WHEN** a family has active landings
- **THEN** its `/category/<family>` page links to each landing

#### Scenario: Landing expert contact is optional
- **WHEN** an admin configures an expert for a landing with only some contact fields
- **THEN** the landing shows the available expert details and omits every empty contact field
