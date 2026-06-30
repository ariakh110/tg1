# Change: Aggressive contact capture in the sales chat (name + surname + mobile)

## Why
The sales chat already has a `capture_lead` tool, but it only asks for contact info «وقتی مشتری تمایل داشت» — so most conversations end with no phone number and the lead is unreachable. The business wants the assistant to get the customer's full name and mobile **by any means**, either through persistent persuasion or by withholding the exact price until contact is given.

## What Changes
- **`AssistantSettings.lead_capture_mode`** (off / soft / strict, default `soft`) controls how hard the assistant pushes for «نام و نام‌خانوادگی + موبایل»:
  - **off** — only if the customer volunteers (previous behavior).
  - **soft (ترغیبی)** — the system prompt instructs the assistant to ask early and benefit-frame it, and to re-ask politely with a different angle if dodged (persuasion, persistent but not abusive).
  - **strict (اجباری)** — additionally the assistant must not reveal an exact price/quote until the lead is captured, and the price tool is gated server-side.
- **Prompt injection (`ai.py::_lead_capture_block`).** A mode-specific block is added to the system prompt, including a «قبلاً ثبت شده» note when the conversation already has a phone so the bot stops asking.
- **Server-side price gate.** In `strict` mode, `execute_tool("get_price_quote", …)` returns a `gated` result (telling the model to capture the lead first) until the conversation has a phone — belt-and-suspenders beyond the prompt.
- **Stronger `capture_lead`.** Requires both a name and a valid Iranian mobile, normalizes the phone to `09XXXXXXXXX`, and the tool now requires `name` (full name) in its schema.

## Impact
- Affected specs: `ai-sales-assistant` (lead capture intensity).
- Backend (tg1): `assistant` — `AssistantSettings.lead_capture_mode` + migration `0004`, `ai.py` prompt block + threading the mode/conversation through `run_chat`, `tools.py` price gate + phone/name validation, serializer field, new `tests.py` (10 tests). Reuses `customers.services.normalize_phone`.
- Frontend (kavehmetal): `AssistantPanel` gains a mode selector.
- **Default `soft`** — strong persuasion without withholding prices (low risk for the live site); the admin switches to `strict` in the panel for full gating. Builds on the chat→CRM lead intake already in place.
