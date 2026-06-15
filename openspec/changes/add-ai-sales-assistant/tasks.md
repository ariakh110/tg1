## 1. Backend (tg1)
- [x] 1.1 `assistant` app: `AssistantSettings`, `AssistantKnowledge`, `AssistantConversation`, `AssistantMessage` + migration
- [x] 1.2 `ai.py`: embeddings, `ensure_embeddings`, cosine RAG `retrieve` (keyword fallback), `run_chat` tool loop
- [x] 1.3 `tools.py`: `search_products`, `get_price_quote` (roll-weight aware), `capture_lead` + tool schemas
- [x] 1.4 serializers + views (public chat/config, admin knowledge/settings/conversations + reembed) + urls + admin
- [x] 1.5 register app in INSTALLED_APPS + `/api/assistant/`; `makemigrations`/`migrate`; `manage.py check`
- [x] 1.6 smoke test: retrieval returns relevant knowledge (keyword fallback without key)

## 2. Frontend (kavehmetal)
- [x] 2.1 `assistantApi` (chat/config + admin CRUD/settings/conversations/reembed)
- [x] 2.2 floating chat widget in AppShell (self-hides when disabled; session persistence)
- [x] 2.3 admin «دستیار فروش» panel (settings + knowledge CRUD + reembed + conversations) wired into dashboard

## 3. Verification
- [x] 3.1 `npx eslint`; `npm run build` compiles
- [x] 3.2 `openspec validate add-ai-sales-assistant --strict`
- [ ] 3.3 After deploy: set OpenAI key + base_url, enable assistant, add a training, rebuild embeddings; widget answers from knowledge + catalog, quotes a price, and captures a lead visible in the admin
