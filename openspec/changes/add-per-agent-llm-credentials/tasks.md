## 1. Backend (assistant + seo_assistant)
- [x] 1.1 Add `openai_api_key` field to `AssistantSettings` and `SeoAssistantSettings`
- [x] 1.2 `api_key` property prefers own key, falls back to `SiteSettings.openai_api_key` then env
- [x] 1.3 `AssistantSettings.openai_base_url` default → AvalAI; data migration flips the stale OpenAI default on the existing row
- [x] 1.4 Serializers: write-only `openai_api_key` (never in GET); empty value preserves the stored key
- [x] 1.5 `makemigrations assistant seo_assistant` + `manage.py check`

## 2. Frontend (kavehmetal)
- [x] 2.1 Sales `AssistantPanel` adds a masked per-agent key input next to base_url
- [x] 2.2 SEO `SeoAssistantPanel` adds a masked per-agent key input next to base_url

## 3. Verification
- [ ] 3.1 `openspec validate add-per-agent-llm-credentials --strict`
- [x] 3.2 Frontend `npm run build`
- [x] 3.3 `manage.py makemigrations` + `check`
- [ ] 3.4 Manual after deploy+migrate: each agent answers with its own key/base_url; sales assistant works on AvalAI; `openai_api_key` absent from GET
