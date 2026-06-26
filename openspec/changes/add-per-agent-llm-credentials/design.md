## Context
Each assistant already had its own singleton settings (`AssistantSettings`, `SeoAssistantSettings`) with per-agent `openai_base_url`, `chat_model`, `embedding_model`, `temperature`. The only shared piece was the API key, exposed through an `api_key` property that always read `SiteSettings.openai_api_key`. Combined with the sales assistant's OpenAI-default base_url, an Iran-hosted deploy on an AvalAI key failed for the sales agent.

## Decision
- Keep the `api_key` property as the single read path used by `ai.py` (no call-site changes). Change its body to: own key → SiteSettings key → env. This is backward compatible: setups that only filled the global key keep working.
- Store the per-agent key as a plain `CharField` (consistent with `SiteSettings.openai_api_key`), exposed write-only so the secret never leaves the server. Empty submissions are ignored to avoid accidental wipes; clearing a key is an admin-DB action.
- Make AvalAI the default base_url for both agents and migrate the existing sales row off the stale OpenAI default via `RunPython`, gated on equality with the old default so a deliberate value is never overwritten.

## Risks / Trade-offs
- A blank key in the form cannot clear an existing per-agent key (preserve-on-empty). Acceptable: clearing is rare and possible via Django admin.
- The data migration only helps the untouched default; admins who set a custom base_url are left as-is by design.
