# Change: AI sales assistant (industrial steel) with admin-managed training

## Why
The store needs a professional, always-on sales assistant on the website that understands industrial steel products, guides buyers to the right product/price, and captures leads — and that the store owner can keep teaching with their own sales knowledge. Existing «استعلام/تماس» flows are passive; an assistant converts visitors and answers domain questions 24/7.

## What Changes
- **New `assistant` Django app.**
  - `AssistantSettings` (singleton): enable flag, persona, sales workflow, greeting, LLM config (OpenAI-compatible `base_url`, chat model, embedding model, temperature, context size), lead-capture flag, handoff phone. API key is read from `SiteSettings.openai_api_key`.
  - `AssistantKnowledge` (admin-managed training): kind = Q&A or article, topic, tags, content, plus an `embedding` vector for RAG (with staleness tracking via content hash).
  - `AssistantConversation` + `AssistantMessage`: chat logging, captured lead (name/phone/interest), status (open/lead/closed).
- **RAG + tool-calling service (`ai.py`, `tools.py`).** Embeds knowledge (OpenAI embeddings), retrieves top-K relevant chunks per query (cosine; keyword fallback when offline), builds a system prompt (persona + workflow + knowledge), and runs an OpenAI-compatible chat loop with tools: `search_products`, `get_price_quote` (uses real catalog + roll-weight logic), `capture_lead`. Raw `urllib` (no new pip dependency).
- **APIs.** Public `POST /assistant/chat/` and `GET /assistant/config/`; admin CRUD for knowledge (+ `reembed`), settings GET/PATCH, and conversation/lead viewing.
- **Frontend.** Floating chat widget on public pages (self-hides when disabled), and an admin «دستیار فروش» panel with three tabs: settings/persona/workflow, knowledge/training CRUD (+ rebuild embeddings), conversations & leads.

## Impact
- Affected specs: `ai-sales-assistant`
- Backend (tg1): new app `assistant` (models, ai, tools, serializers, views, urls, admin, migration `0001`); register in `INSTALLED_APPS` + root urls. No change to existing models.
- Frontend (kavehmetal): `app/lib/assistantApi.js`, `app/components/assistant/SalesAssistant.js`, `app/components/admin/AssistantPanel.js`; wired into `AppShell.js` + `AdminDashboardPage.js`.
- Requires an OpenAI-compatible endpoint reachable from the server (configurable `base_url`); disabled by default until enabled with a key.
