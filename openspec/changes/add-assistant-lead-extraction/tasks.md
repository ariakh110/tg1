## 1. Backend (tg1)
- [x] 1.1 `AssistantInquiry` model (+ `summary`) + migration `0002`
- [x] 1.2 `register_inquiry` tool: extract fields, match catalog product + price, store, flag conversation as lead
- [x] 1.3 tool schema + dispatch in `execute_tool`; system prompt instructs calling it on concrete needs
- [x] 1.4 serializer + admin inquiries viewset (GET/PATCH status) + url + Django admin
- [x] 1.5 `makemigrations` + `manage.py check`

## 2. Frontend (kavehmetal)
- [x] 2.1 `assistantApi`: fetch/update inquiries
- [x] 2.2 «استعلام‌ها (سرنخ)» tab in AssistantPanel (matched product, price, contact, status)

## 3. Verification
- [x] 3.1 `npx eslint`; `npm run build` compiles
- [x] 3.2 `openspec validate add-assistant-lead-extraction --strict`
- [ ] 3.3 After deploy: write «۲۰ تن میلگرد ۱۴ اصفهان» in chat → a structured inquiry appears in the admin tab with the matched product/price
