# Change: SEO specialist assistant (admin-only) grounded in an SEO knowledge base

## Why
The team needs an in-product **SEO specialist agent** (primarily for the Tirexa site, reusable for any site) that the site owner/admin can chat with to get grounded SEO guidance: technical audits, on-page recommendations (title/meta/headings/URLs), keyword & content strategy, local SEO, link building, Core Web Vitals/INP, and AI-search optimization (GEO/AEO, AI Overviews). Unlike the public sales assistant, this is an **internal admin tool** answering from a curated SEO knowledge base — not invented advice.

## What Changes
- **New `seo_assistant` Django app (admin-only).**
  - `SeoAssistantSettings` (singleton): enable flag, assistant name, SEO-expert persona, target-site context (e.g., Tirexa = Django+Next, Iran-IP/CDN crawlability blocker), LLM config (OpenAI-compatible `base_url` defaulting to **AvalAI** `https://api.avalai.ir/v1`, chat model, embedding model, temperature, context size, tool iterations). API key is read from `SiteSettings.openai_api_key` (one AvalAI key serves both OpenAI and Claude models).
  - `SeoKnowledge`: knowledge chunks ingested from the SEO knowledge base (base layer + 2026 layer), with `source`, `layer`, `title`, `body`, `tags`, plus an `embedding` vector for RAG (staleness tracked via content hash).
  - `SeoConversation` + `SeoMessage`: admin chat logging.
- **RAG + tool-calling service (`ai.py`, `tools.py`).** Embeds knowledge (AvalAI embeddings), retrieves top-K relevant chunks per query (cosine; keyword fallback when offline), builds a system prompt (SEO persona + target-site context + retrieved knowledge), runs an OpenAI-compatible chat loop with a tool: `fetch_page_seo` (fetch a live URL and extract title, meta description, canonical, robots meta, H1/H2, status code, word/link counts — so the agent can audit real pages). Raw `urllib` (no new pip dependency), mirroring `assistant/ai.py`.
- **Knowledge base bundled in-repo.** Markdown files copied to `seo_assistant/knowledge_base/` (`base/` + `2026/`) so the app is self-contained and deployable. A management command `ingest_seo_kb` parses them into `SeoKnowledge` (one chunk per `##`/`###` section) and rebuilds embeddings.
- **APIs (admin-only).** `POST /api/seo-assistant/admin/chat/`, `GET/PATCH admin/settings/`, admin CRUD for knowledge (+ `reembed`, + `ingest`), conversation viewing. No public endpoint.

## Impact
- Affected specs: `seo-assistant`
- Backend (tg1): new app `seo_assistant` (models, ai, tools, serializers, views, urls, admin, apps, migration `0001`, `management/commands/ingest_seo_kb.py`, bundled `knowledge_base/`); register in `INSTALLED_APPS` + root urls at `/api/seo-assistant/`. No change to existing models (reuses `SiteSettings.openai_api_key` and `accounts.permissions.IsAdminOrActiveAdminRole`).
- Frontend: out of scope for this change (admin can use it via the API / a later admin panel tab). The existing sales-assistant admin panel pattern can be reused to add a tab later.
- Requires an OpenAI-compatible endpoint (AvalAI) reachable from the server; disabled by default until enabled with a key. Knowledge source: the SEO knowledge base built from the UC Davis Google SEO Specialization + a 2025–2026 update layer.
