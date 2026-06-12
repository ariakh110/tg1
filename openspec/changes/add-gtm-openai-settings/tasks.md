## 1. Backend (core + blog)
- [x] 1.1 Add `google_tag_manager_id`, `openai_api_key`, `openai_content_model` to `SiteSettings`
- [x] 1.2 Serializer: expose `google_tag_manager_id`, `openai_content_model`, `openai_configured`; never expose `openai_api_key`
- [x] 1.3 PATCH view: accept all three; update `openai_api_key` only when non-empty
- [x] 1.4 `blog/ai.py` reads key/model from `SiteSettings` (env fallback)
- [x] 1.5 Django admin shows the new fields; `makemigrations` (`0005`) + `check`

## 2. Frontend (kavehmetal)
- [x] 2.1 `SettingsProvider` exposes `gtmId`, `openaiModel`, `openaiConfigured`
- [x] 2.2 `lib/serverSettings.js` `getServerSettings()` returns `{ siteName, gtmId }`
- [x] 2.3 Root `layout.js` injects GTM (script + noscript) server-side when `gtmId` set
- [x] 2.4 Admin `SettingsPanel` adds GTM + OpenAI (model + masked key) inputs

## 3. Verification
- [x] 3.1 `openspec validate add-gtm-openai-settings --strict`
- [x] 3.2 `npx eslint` on changed frontend files
- [x] 3.3 `manage.py makemigrations` + `check`
- [ ] 3.4 Manual after deploy: admin sets GTM/OpenAI; GTM script appears; `openai_api_key` absent from GET
