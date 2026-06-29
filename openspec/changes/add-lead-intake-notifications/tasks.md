## 1. Lead intake (customers)
- [x] 1.1 Add `Customer.created_by` (nullable FK) + sources `store_purchase`, `chat`; relabel `website`
- [x] 1.2 `customers/services.py::upsert_lead()` (normalize phone, get_or_create, fill-blanks-only, optional note activity)
- [x] 1.3 `CustomerViewSet.perform_create` sets `created_by`; serializer exposes read-only `created_by_name`
- [x] 1.4 Migration `0005_customer_created_by_alter_customer_source`

## 2. Admin notification channels (messaging)
- [x] 2.1 `MessagingSettings`: `telegram_enabled`, write-only `telegram_bot_token`, `telegram_admin_chat_id`, `admin_alert_phone`, `notify_on_signup/order/chat_lead`; `telegram_configured` + `telegram_chat_ids`
- [x] 2.2 `OutboundMessage` purpose `admin_alert`
- [x] 2.3 `providers/telegram.py` (urllib `sendMessage`, `SendResult`, never raises)
- [x] 2.4 `service.notify_admin(title, lines)` — fan out to Telegram + SMS, dry-run `skipped` when none configured
- [x] 2.5 Serializer exposes new fields (token write-only, `telegram_token_configured`, `telegram_configured`)
- [x] 2.6 Migration `0002` (messaging)

## 3. Event orchestration + wiring
- [x] 3.1 `messaging/events.py`: `on_user_signup`, `on_order_submitted`, `on_chat_lead` (safe, upsert + notify)
- [x] 3.2 `messaging/signals.py` + `apps.ready` — `StoreOrder` transition into `SUBMITTED` → `on_order_submitted`
- [x] 3.3 `accounts/views.py` RegisterAPIView + Google auth → `on_user_signup` (safe)
- [x] 3.4 `assistant/tools.py` `capture_lead` + `register_inquiry` → `on_chat_lead` (safe)

## 4. API + test alert
- [x] 4.1 `POST /api/messaging/test-alert/` (admin-only) → `notify_admin` + per-channel summary

## 5. Frontend
- [x] 5.1 `MessagingPanel` settings: Telegram (token/chat id) + admin SMS phone + per-event toggles + test button
- [x] 5.2 `messagingApi.testAdminAlert()`

## 6. Verification
- [x] 6.1 Tests: `upsert_lead` idempotency/blank-phone, `notify_admin` dry-run + Telegram fan-out, signup/order intake
- [x] 6.2 `manage.py check`, `migrate`, `test customers messaging` green; frontend ESLint clean
