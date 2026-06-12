# Change: Admin-managed Google Tag Manager & OpenAI settings

## Why
Two integrations were env-only: there was no way to add a Google Tag Manager container, and the OpenAI SEO content generator read its key/model only from server env vars (`OPENAI_API_KEY`, `OPENAI_CONTENT_MODEL`), so changing them required a redeploy. The admin should manage both from the existing site-settings panel. The OpenAI key is a secret and must never be exposed publicly.

## What Changes
- Add three fields to the singleton `SiteSettings`: `google_tag_manager_id` (public), `openai_content_model` (public), and `openai_api_key` (secret).
- `GET /api/site-settings/` additionally returns `google_tag_manager_id`, `openai_content_model`, and a boolean `openai_configured` — but NEVER the raw `openai_api_key`.
- Admin `PATCH /api/site-settings/` accepts all three; `openai_api_key` is updated only when a non-empty value is sent (empty leaves it unchanged).
- Backend `blog/ai.py` reads the OpenAI key/model from `SiteSettings`, falling back to env.
- Frontend: `SettingsProvider` exposes `gtmId`/`openaiModel`/`openaiConfigured`; the admin Settings panel gains GTM + OpenAI (model + masked key) inputs; the root layout injects the GTM script server-side when a container ID is set.

## Impact
- Affected specs: `site-settings`
- Affected code (backend): `core/models.py`, `core/serializers.py`, `core/views.py`, `core/admin.py`, `blog/ai.py` + migration `core/0005_sitesettings_google_tag_manager_id_and_more`.
- Affected code (frontend, kavehmetal): `lib/serverSettings.js`, `layout.js`, `components/SettingsProvider.js`, `components/admin/SettingsPanel.js`.
