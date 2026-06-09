## Context
The site name was hard-coded across the Next.js frontend, and section visibility was static. Admin wants runtime control. The backend (`core` app) already hosts a public `ContactAPIView`; SimpleJWT identifies admins (`is_staff`).

## Goals / Non-Goals
- Goals: one editable site name; admin on/off flags for marketplace, featured-loads, export, offers, blog; marketplace off by default.
- Non-Goals: user-management controls (registration toggle, maintenance mode) — deferred; the admin already has a users/roles panel.

## Decisions
- **Singleton model** `SiteSettings` (forces `pk=1` in `save()`, `load()` get_or_creates) — simplest for a single global config row.
- **API shape** `{ site_name, sections: { marketplace, featured_loads, export, offers, blog } }`. GET is `AllowAny`; PATCH requires `IsAdminUser`. PATCH is partial: only provided keys change.
- **Frontend provider** seeds initial state with build-time defaults (name = `siteConfig.SITE_NAME`; all sections on except marketplace) so server and first client render match (no hydration mismatch / flash), then updates from the API after mount.
- **Gating in two layers**: hide entry points (nav items, homepage tiles/banners, sale-hall cards) when a flag is off, AND guard the route page itself with a shared `SectionDisabled` "coming soon" component for direct-URL access.
- **Name replacement**: hard-coded "کاوه متال" is kept in source as the literal default; at render the displayed value is the dynamic `siteName` (the default equals it, so nothing visually changes until an admin edits it).

## Risks / Trade-offs
- Brief default-then-updated paint if the admin has changed the name — acceptable; default matches the historical brand.
- Many touch points for the name (21 files) — mechanical; provider default removes correctness risk.

## Migration Plan
`makemigrations core` + `migrate` (single additive table, no data migration). Rollback = remove flag reads (frontend tolerates missing settings via defaults).

## Open Questions
- None blocking. SSR `<metadata>` title stays static for now (can be made dynamic later).
