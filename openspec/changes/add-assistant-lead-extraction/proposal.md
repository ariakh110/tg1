# Change: Structured lead extraction from free-text inquiries

## Why
Steel customers write inquiries in natural language («۲۰ تن میلگرد ۱۴ اصفهان میخوام»). Today that becomes a chat message with no structure, so the operator must re-read and re-key it. As the first step of the AI-first sales evolution (on the existing Django/Next stack — no rebuild), the assistant should turn such inquiries into structured, catalog-matched leads the operator can act on.

## What Changes
- **New `AssistantInquiry` model** (in the existing `assistant` app): product, size, grade, factory, quantity, city, note, raw_text; optional `matched_product` + `matched_price`; captured contact (name/phone from the conversation); and a pipeline `status` (new/quoted/contacted/won/lost).
- **New `register_inquiry` tool** for the assistant: extracts the structured fields from the customer's text, tries to match a catalog product (reusing `search_products`) and snapshot its price, stores the inquiry, and marks the conversation as a lead. The system prompt instructs the model to call it whenever the customer states a concrete need.
- **Admin:** read + status/contact update API (`/assistant/admin/inquiries/`), an «استعلام‌ها (سرنخ)» tab in the assistant panel (table with matched product, price, contact, status dropdown), and Django admin.

## Impact
- Affected specs: `ai-sales-assistant`
- Backend (tg1): `assistant/models.py` (+`AssistantInquiry`, migration `0002`), `assistant/tools.py` (`register_inquiry` + schema + dispatch), `assistant/ai.py` (prompt), `assistant/serializers.py`, `assistant/views.py`, `assistant/urls.py`, `assistant/admin.py`.
- Frontend (kavehmetal): `app/lib/assistantApi.js`, `app/components/admin/AssistantPanel.js` (inquiries tab).
- Migration `0002` runs on deploy. No rebuild; reuses the existing assistant/catalog/pricing.
