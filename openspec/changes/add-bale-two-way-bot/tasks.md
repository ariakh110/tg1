## 1. Provider + settings
- [x] 1.1 `providers/telegram.py`: generic `_call`; `send_message(reply_markup)`, `answer_callback_query`, `set_webhook`, `get_webhook_info`
- [x] 1.2 `MessagingSettings`: `bale_webhook_enabled`, `bale_admin_user_ids`, `site_base_url`; `bale_admin_ids` + `is_admin_sender()`; migration `0004`
- [x] 1.3 Serializer exposes the new fields

## 2. Bot brain
- [x] 2.1 `messaging/bale_bot.py::handle_update` — routes `message` / `callback_query`, inert unless enabled, never raises
- [x] 2.2 Inline buttons `_lead_buttons` + `_apply_callback` (called / follow-up tomorrow / won) with admin gating
- [x] 2.3 Admin commands `/امروز` `/سرنخ` `/بدهکاران` (+ English aliases, `/start`/`/help`)
- [x] 2.4 Price bot via `assistant.tools.search_products` with product links from `site_base_url`
- [x] 2.5 `build_daily_digest()` shared by `/امروز` and the digest command

## 3. Endpoints + wiring
- [x] 3.1 `BaleWebhookView` (public, secret) + `BaleSetWebhookView` (admin) + urls
- [x] 3.2 `notify_admin` attaches action buttons when customer present and bot enabled
- [x] 3.3 `management/commands/bale_daily_digest.py`

## 4. Frontend
- [x] 4.1 `MessagingPanel` two-way-bot section (enable, admin user ids, site url, connect button)
- [x] 4.2 `messagingApi.setBaleWebhook`

## 5. Verification
- [x] 5.1 Tests: webhook secret guard, won-callback stage change, non-admin denied, price-bot reply, today command, digest builder
- [x] 5.2 `manage.py check` + `test messaging` green (28); frontend ESLint clean
- [ ] 5.3 (ops) admin sets a cron for `bale_daily_digest` on the server
