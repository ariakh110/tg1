## 1. Provider + settings
- [x] 1.1 `providers/safir.py` (urllib POST send_message; `to_safir_phone`; `SendResult`; error-code labels)
- [x] 1.2 `MessagingSettings`: `safir_enabled`, write-only `safir_access_key`, `safir_bot_id`, `safir_configured`; migration `0005`
- [x] 1.3 `OutboundMessage` channel `bale`
- [x] 1.4 Serializer exposes Safir fields (key write-only, `safir_key_configured`, `safir_configured`)

## 2. Service + API
- [x] 2.1 `service.send_bale` (dry-run when unconfigured, logs `bale` channel + «بله» activity)
- [x] 2.2 `send_to_customer`/`send_bulk` gain `channel`; `_log_activity` channel label
- [x] 2.3 `send` + `send-bulk` views accept `channel`

## 3. Frontend
- [x] 3.1 `MessagingPanel` Safir settings section (enable, access key, bot id)
- [x] 3.2 Send tab channel toggle (پیامک/بله)

## 4. Verification
- [x] 4.1 Tests (4): phone conversion, dry-run, configured send (98 format), API channel routing
- [x] 4.2 `manage.py check` + `test messaging` green (32); frontend ESLint clean
