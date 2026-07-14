## Context
Product taxonomy is editable at runtime, but cluster landings were originally built around six known steel families. The taxonomy now supports custom product kinds and new root categories, so a compiled allowlist is no longer valid.

## Goals / Non-Goals
- Goals: make active root categories immediately selectable in the landing editor; make their public landing routes render; preserve legacy landing editability; keep sitemap discovery aligned.
- Non-Goals: change the `Landing` database model, create landings automatically, or allow child categories to act as URL families.

## Decisions
- `ProductCategory` remains the source of truth. A landing family option is an active root category with a non-empty `code`.
- The admin client follows paginated category responses instead of assuming the first page contains every root.
- Public server routes resolve a family by exact active root category code. The six legacy families remain fallback metadata only, so temporary taxonomy lookup failures do not break already-known routes.
- A saved active landing is sufficient for the nested landing route. Taxonomy lookup supplies the display name but is not allowed to hide an otherwise valid existing landing.
- Sitemap family hubs are the union of active taxonomy roots, legacy families, and active landing families, with duplicate codes removed.

## Risks / Trade-offs
- A category code change can orphan existing landing URLs because `Landing.family` is a string. Operators should treat root codes as stable URL identifiers.
- Root categories without products can be selected for authored landing preparation; public product sections remain empty until products are assigned.

## Migration Plan
No database migration is required. Deploy the frontend archive after the documented checks pass.

