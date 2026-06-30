# Change: Bale Safir channel — message customers in Bale by phone number

## Why
SMS (Kavenegar) is the only way to reach a customer on their phone today, and each SMS costs money. Bale's **Safir** service sends a real Bale message to a customer by mobile number — the customer does not need to have started the bot, only to have a Bale account — which is cheaper and richer for customers who use Bale. The admin asked to connect it.

## What Changes
- **Safir provider (`messaging/providers/safir.py`) using raw `urllib`** — POST `https://safir.bale.ai/api/v3/send_message` with the org `api-access-key` header and `{bot_id, phone_number, message_data:{message:{text}}}`. Parses the `error_data`/`message_id` envelope into a `SendResult`; never raises. Includes `to_safir_phone` (normalized `09…` → required `989…` form).
- **Settings (`MessagingSettings`):** `safir_enabled`, write-only `safir_access_key`, `safir_bot_id`, and a `safir_configured` flag. Mirrors the other provider settings; the key is never returned by GET.
- **Channel-aware sending (`service.py`).** `send_bale(recipient, message, …)` mirrors `send_sms` (dry-run `skipped` when Safir is off/unconfigured, logs an `OutboundMessage` with the new `bale` channel, appends a «بله …» activity to the customer timeline). `send_to_customer` and `send_bulk` gain a `channel` argument that routes to SMS or Bale.
- **APIs.** `POST /api/messaging/send/` and `/send-bulk/` accept a `channel` (`sms` default, or `bale`).
- **OutboundMessage** gains a `bale` channel value.

## Impact
- Affected specs: `messaging` (Bale Safir channel).
- Backend (tg1): `messaging` — `providers/safir.py`, settings fields + `bale` channel + migration `0005`, `send_bale` + channel routing in `service.py`, `channel` param in send views, serializer fields, tests (4).
- Frontend (kavehmetal): `MessagingPanel` Safir settings section + a channel toggle (پیامک/بله) in the send tab.
- **Off by default & dry-run.** Nothing sends until the admin enables Safir and enters the access key + bot id; until then Bale sends log as `skipped`. No new dependency. OTP and multimedia/file sends are supported by Safir but out of scope here (text + inline-button capable later).
