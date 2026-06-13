# Change: Admin custom head & footer scripts (analytics/tag injection)

## Why
The store owner needs to drop in third-party snippets — Google Analytics, Microsoft Clarity, site-verification meta tags, chat widgets — without a code deploy. These belong in specific placements: tracking/verification in `<head>`, heavier or end-of-page widgets before `</body>`. Today only a fixed GTM container id is supported, which doesn't cover arbitrary snippets.

## What Changes
- **Settings model:** `SiteSettings` gains two free-text fields, `head_scripts` and `footer_scripts` (raw HTML/JS). Exposed in the public settings GET and editable via the admin PATCH (no length cap). The secret OpenAI key behavior is unchanged.
- **Admin panel:** the Settings panel gets an «اسکریپت‌های سفارشی» section with two textareas (Header / Footer), saved through the existing settings PATCH.
- **Frontend injection (placement-aware):** a `RawScripts` client component injects the saved markup into the correct location — `head_scripts` into `<head>`, `footer_scripts` at the end of `<body>`. Pasted `<script>` blocks are re-created as real script elements so they actually execute (innerHTML-inserted scripts do not run); `<meta>`/`<link>`/`<noscript>` are cloned as-is. Values are read server-side via `getServerSettings` so they render on first paint.

## Impact
- Affected specs: `site-settings`
- Backend (tg1): `core/models.py` (+2 fields), migration `0006`, `core/serializers.py`, `core/views.py` (PATCH).
- Frontend (kavehmetal): new `app/components/RawScripts.js`; edits to `app/lib/serverSettings.js`, `app/layout.js`, `app/components/SettingsProvider.js`, `app/components/admin/SettingsPanel.js`.
- The fields hold raw markup an admin authors; output is intentional injection by the site owner (same trust model as the existing GTM field).
