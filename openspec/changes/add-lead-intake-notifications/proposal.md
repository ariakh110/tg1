# Change: Automatic lead intake from site events + admin notifications (Telegram + SMS)

## Why
The CRM only fills up when an admin types a customer in by hand. The three real ways a lead reaches the business today are invisible to the admin until they go digging:
- a visitor **registers on the site** (User + Profile) — nothing tells the admin,
- a buyer **places a direct-sales order** (`sales.StoreOrder`) — the admin only finds out by opening the direct-sales section,
- a visitor **gives their number in the sales chat** (`assistant.AssistantConversation`/`AssistantInquiry`) — the lead is saved on the conversation but **never reaches the CRM**.

The admin asked to (1) be notified the moment any of these happens, over **Telegram (free/instant) and SMS**, and (2) have each event create/update a CRM customer so the new CRM table shows where every lead came from. The `messaging` app already sends SMS and reserved a `telegram` channel — this change uses that backbone.

## What Changes
- **New lead-intake service `customers/services.py::upsert_lead()`** — single entry point that creates-or-updates a `Customer` keyed by normalized phone, fills only blank fields on an existing customer (never overwrites a stage/source the admin already set), links the website user when known, and optionally appends a `note` activity describing how the lead arrived.
- **`Customer.created_by`** (FK, nullable) records who entered a customer; null = created automatically by the system. The CRM API sets it on manual create and exposes a read-only `created_by_name`. Two precise sources are added: `store_purchase` (خرید از سایت) and `chat` (چت فروش); `website` is relabeled «ثبت‌نام سایت».
- **Telegram provider (`messaging/providers/telegram.py`) using raw `urllib`** (no new pip dep) — `sendMessage` for admin alerts. `MessagingSettings` gains `telegram_enabled`, write-only `telegram_bot_token`, `telegram_admin_chat_id` (comma-separated for multiple), an `admin_alert_phone` for SMS alerts, and per-event toggles `notify_on_signup` / `notify_on_order` / `notify_on_chat_lead`.
- **`messaging/service.py::notify_admin(title, lines)`** — fans an event out to every configured admin channel (Telegram to each chat id + SMS to the admin phone), logging each attempt as an `OutboundMessage(purpose=admin_alert)`. Dry-run safe: if nothing is configured it logs one `skipped` row and sends nothing.
- **`messaging/events.py`** — safe orchestration (`on_user_signup`, `on_order_submitted`, `on_chat_lead`) that does upsert + notify and never raises into the request path.
- **Event wiring:** registration (`accounts` RegisterAPIView + Google auth) calls `on_user_signup`; the buyer order/quote path (`sales.services.create_store_order`) calls `on_order_submitted` after commit (`transaction.on_commit`), distinguishing a priced order from a quote/استعلام request via `needs_quote`; the assistant `capture_lead` tool calls `on_chat_lead` and `register_inquiry` calls `on_chat_inquiry` (which notifies even before a phone is given).
- **`POST /api/messaging/test-alert/`** — admin-only button to send a test alert and verify the bot/number wiring.

## Impact
- Affected specs: `messaging` (admin notifications + Telegram channel), `customer-crm` (automatic lead intake + registrar).
- Backend (tg1): `customers` (model `created_by` + sources, `services.py`, serializer, view perform_create, migration `0005`); `messaging` (model fields + `admin_alert` purpose, `providers/telegram.py`, `service.notify_admin`, `events.py`, `signals.py`, `apps.ready`, serializer, `test-alert` view/url, migration `0002`, tests); one-line safe hooks in `accounts/views.py` and `assistant/tools.py`.
- Frontend (kavehmetal): `MessagingPanel` settings gains a Telegram + admin-alert section and a test button; CRM list already shows `source`/stage so leads now show their origin.
- **Disabled by default & non-breaking.** No alert is sent until the admin enables Telegram (token + chat id) and/or sets the admin SMS phone; until then events log `skipped`. Every hook is wrapped so a messaging failure can never break signup, checkout, or chat. WhatsApp remains deferred.
