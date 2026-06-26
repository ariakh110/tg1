# Change: Per-agent LLM credentials (sales & SEO assistants)

## Why
Both AI agents resolved their API key from a single shared field (`SiteSettings.openai_api_key`) via an `api_key` property, so all agents were forced onto one provider account. Worse, the sales assistant (`AssistantSettings`) defaulted `openai_base_url` to `https://api.openai.com/v1` — unreachable from an Iran-hosted server and invalid for an AvalAI key — while the SEO assistant defaulted to `https://api.avalai.ir/v1`. The result: agents wired to AvalAI silently failed. The admin needs each agent to carry its own key (with the global key as fallback) and sane AvalAI-first defaults.

## What Changes
- Add a secret `openai_api_key` field to `AssistantSettings` and `SeoAssistantSettings`.
- The `api_key` property on each prefers its own key and falls back to `SiteSettings.openai_api_key` (then the `OPENAI_API_KEY` env var) — so existing single-key setups keep working.
- `AssistantSettings.openai_base_url` default changes to `https://api.avalai.ir/v1`; a data migration flips the existing row from the stale OpenAI default so the sales assistant works after migrate without manual edits.
- Settings serializers accept a write-only `openai_api_key` (NEVER returned by GET); an empty value leaves the stored key unchanged; `api_key_configured` still reports whether a usable key exists.
- Admin panels (sales + SEO) gain a masked per-agent key input next to base_url.

## Impact
- Affected specs: `agent-llm-credentials`
- Affected code (backend, tg1): `assistant/models.py`, `assistant/serializers.py`, `seo_assistant/models.py`, `seo_assistant/serializers.py` + migrations `assistant/0003_*`, `seo_assistant/0002_*`.
- Affected code (frontend, kavehmetal): `components/admin/AssistantPanel.js`, `components/admin/SeoAssistantPanel.js`.
