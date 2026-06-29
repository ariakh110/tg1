## 1. App scaffold
- [x] 1.1 Create `messaging` app (`__init__.py`, `apps.py`); register in `INSTALLED_APPS`
- [x] 1.2 Add `messaging` to `accounts/admin_sections.py` (`ADMIN_SECTIONS` + MARKETER role sections)
- [x] 1.3 Mount `path("api/messaging/", include("messaging.urls"))` in root urls

## 2. Models
- [x] 2.1 `MessagingSettings` singleton (sms_enabled, provider, kavenegar_api_key, sender, default/purchase templates, daily_send_cap, load()/save())
- [x] 2.2 `OutboundMessage` log (channel, provider, customer FK, recipient, purpose, template, body, status, provider_message_id, cost, error, created_by, timestamps, indexes)
- [x] 2.3 Migration `0001_initial`

## 3. Provider + service
- [x] 3.1 `providers/kavenegar.py` (urllib): `sms/send`, `verify/lookup`, `sms/status`; envelope + error parsing; `SendResult`
- [x] 3.2 `service.py`: `normalize_phone`, `send_sms` (dry-run when disabled), `send_to_customer` (+ CustomerActivity), `send_bulk` (daily cap), `notify_purchase_step` (step templates)

## 4. API
- [x] 4.1 Serializers (settings with write-only key + `api_key_configured`; outbound message)
- [x] 4.2 Views: settings GET/PATCH, send (single), send-bulk, notify-step, message log (read-only, filterable); all `admin_section="messaging"`
- [x] 4.3 `urls.py` + `admin.py`

## 4b. Inbound webhooks
- [x] 4b.1 `MessagingSettings.webhook_secret` (auto-generated in `load()`, read-only in serializer)
- [x] 4b.2 `kavenegar/status/<secret>/` — map Kavenegar status code → `OutboundMessage.status`
- [x] 4b.3 `kavenegar/incoming/<secret>/` — `service.log_incoming_sms` → `CustomerActivity` on matched customer

## 5. Verify
- [x] 5.1 Tests: dry-run skipped, single send logs activity, bulk segment, purchase-step purpose, key write-only, non-admin denied
- [x] 5.2 `python manage.py check` and `makemigrations --check --dry-run` clean; `openspec validate add-crm-sms-messaging --strict`
