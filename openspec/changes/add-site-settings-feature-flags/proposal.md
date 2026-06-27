# Change: Admin-controlled site settings — dynamic site name and section feature flags

## Why
The site name is hard-coded in ~78 places and there is no way for an admin to turn sections on/off at runtime. We need a single source of truth for the site name (editable from the admin panel) and feature flags so sections can be hidden until ready — starting with disabling the user marketplace (`/orders`).

## What Changes
- Add a singleton `SiteSettings` model (in the `core` app): `site_name` + per-section boolean flags (`marketplace_enabled` default **false**, `featured_loads_enabled`, `export_enabled`, `offers_enabled`, `blog_enabled` default true).
- Add `GET /api/site-settings/` (public) and `PATCH /api/site-settings/` (admin only) returning `{ site_name, sections }`.
- Frontend: a `SettingsProvider` that fetches settings; replace hard-coded "کاوکس" with the dynamic `site_name`; gate the five sections (hide entry points + guard routes) by their flags; add an admin **Settings** panel to edit the name and toggle sections.
- The user marketplace (`/orders`) is hidden by default and re-enabled from the admin panel.

## Impact
- Affected specs: `site-settings`
- Affected code (backend): `core/models.py`, `core/serializers.py`, `core/views.py`, `core/admin.py`, `tg1/urls.py` + migration `core/0002_sitesettings`.
- Affected code (frontend, kavehmetal): new `lib/siteSettingsApi.js`, `components/SettingsProvider.js`, `components/SectionDisabled.js`, admin `SettingsPanel`; edits to `app/layout.js`, nav/menus/homepage, gated route pages, and the ~21 files containing "کاوکس".
