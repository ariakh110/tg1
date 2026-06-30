# Change: Two-way Bale bot — inline CRM actions, admin commands, customer price bot

## Why
The Bale integration so far is one-way (the backend pushes notifications to the admin/group). The admin asked the bot to also *do things*: act on a lead straight from the group message, answer admin questions on demand, give customers live prices, and post a daily summary. Bale's Bot API is Telegram-shaped and supports webhooks, inline buttons (`callback_query`), and reply messages — and `tapi.bale.ai` is reachable from the Iran server, so a webhook into our own Django backend works with no extra infrastructure (no n8n, no foreign relay).

## What Changes
- **Bale webhook receiver (`messaging/bale_bot.py` + `BaleWebhookView`).** A public, secret-guarded endpoint `POST /api/messaging/bale/webhook/<secret>/` (reusing `MessagingSettings.webhook_secret`) parses each Bale `Update` and routes `message` / `callback_query`. It always returns 200 and never lets an error escape. An admin-only `POST /api/messaging/bale/set-webhook/` registers the webhook URL with Bale (`setWebhook`) and reports `getWebhookInfo`.
- **Telegram/Bale provider gains bot methods.** A generic `_call(token, method, params, base_url)` plus `send_message(reply_markup=…)` (inline keyboards), `answer_callback_query`, `set_webhook`, `get_webhook_info` — still raw `urllib`, still never raising.
- **Inline action buttons on lead/order notifications.** When the two-way bot is enabled and the notification concerns a customer, `notify_admin` attaches three buttons — «✅ تماس گرفتم» / «⏰ پیگیری فردا» / «🤝 مشتری شد» — whose `callback_data` carries the customer id. Clicking updates the CRM directly (adds a call activity, schedules a next-day follow-up, or moves the customer to «مشتری فعال» with a stage-change activity), so the team works the lead from the group without opening the panel.
- **Authorization.** CRM-modifying callbacks and admin commands are gated by `MessagingSettings.is_admin_sender(chat_id, from_id)`: allowed when the update comes from a configured destination (the admin group / private chat) or from a listed admin user id (`bale_admin_user_ids`). The read-only price bot is open to everyone.
- **Admin commands.** `/امروز` (today's new leads + overdue/today follow-ups + debtor count), `/سرنخ 0912…` (customer card: stage, source, balance, last activity), `/بدهکاران` (top debtors). English aliases (`/today`, `/lead`, `/debtors`) and `/start`/`/help` are supported.
- **Customer price bot.** Any free-text message (e.g. «میلگرد ۱۴») runs the existing assistant catalog search and replies with up to three matches — title, price (or «نیازمندِ استعلام»), and a product link built from `site_base_url`.
- **Daily digest.** A `bale_daily_digest` management command sends the same summary to the admin channels; meant to be run by cron on the server.
- **New settings:** `bale_webhook_enabled`, `bale_admin_user_ids`, `site_base_url`, surfaced in the admin پیامک panel with a «اتصالِ ربات» button.

## Impact
- Affected specs: `messaging` (two-way bot capability).
- Backend (tg1): `messaging` — `bale_bot.py`, provider bot methods, `notify_admin` buttons, `BaleWebhookView`/`BaleSetWebhookView` + urls, settings fields + migration `0004`, `management/commands/bale_daily_digest.py`, serializer, tests. Reuses `customers` (CRM) and `assistant.tools` (catalog search) read-only.
- Frontend (kavehmetal): `MessagingPanel` gains a two-way-bot section (enable, admin user ids, site URL, connect button); `messagingApi.setBaleWebhook`.
- **Off by default & safe.** Buttons appear and the webhook acts only when `bale_webhook_enabled` is on; every handler is wrapped so a bad update can't 500. Works through the same `telegram_api_base` (Bale) already configured — no new dependency or service. Cron for the digest is set up by the admin on the server.
