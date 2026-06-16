## 1. Backend (tg1)
- [x] 1.1 `seo_assistant` app: `SeoAssistantSettings`, `SeoKnowledge`, `SeoConversation`, `SeoMessage` + migration `0001`
- [x] 1.2 `ai.py`: embeddings, `ensure_embeddings`, cosine RAG `retrieve` (keyword fallback), `run_chat` tool loop (AvalAI OpenAI-compatible)
- [x] 1.3 `tools.py`: `fetch_page_seo` (title/meta/canonical/robots/H1-H2/status/word+link counts) + tool schema
- [x] 1.4 serializers + admin-only views (chat, settings GET/PATCH, knowledge CRUD + reembed + ingest, conversations) + urls + admin
- [x] 1.5 bundle KB markdown into `seo_assistant/knowledge_base/{base,2026}/`; `management/commands/ingest_seo_kb.py` parses sections → `SeoKnowledge` + reembed
- [x] 1.6 register app in INSTALLED_APPS + `/api/seo-assistant/`; `makemigrations`/`migrate`; `manage.py check`

## 2. Verification
- [x] 2.1 `ingest_seo_kb` loads chunks from bundled KB (no key needed); count > 0 (172 chunks)
- [x] 2.2 smoke test: retrieval returns relevant SEO knowledge via keyword fallback without an LLM key
- [x] 2.3 `openspec validate add-seo-assistant --strict`
- [ ] 2.4 After deploy: set AvalAI key + base_url, choose chat/embedding model, enable assistant, run `ingest_seo_kb`, rebuild embeddings; admin chat answers SEO questions from the knowledge base and can audit a live URL via `fetch_page_seo`
