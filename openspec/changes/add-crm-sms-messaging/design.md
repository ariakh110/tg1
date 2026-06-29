## Context
The CRM (`customers` app) has customers with a unique `phone`, a ledger, and a `CustomerActivity` timeline that already includes a `message` kind. There is no real outbound messaging anywhere; `sales/services.py` only records a notification behind `SMS_PROVIDER_ENABLED` and never sends. The first provider is Kavenegar (REST, JSON, doc bundled in `openspec/sms-kavenegar-api-doc/`). The user has **no Kavenegar credentials yet**, so the system must be fully testable in dry-run and go live the moment a key is entered in the admin panel.

## Goals / Non-Goals
- Goals: send a single SMS to a CRM customer; send to a filtered segment; send purchase-step SMS for direct sales; a complete audit log; admin-managed credentials behind a master switch; an architecture that admits Telegram/WhatsApp later without a data-model rewrite.
- Non-Goals (this change): any frontend UI; Telegram/WhatsApp providers; automatic triggers from the `sales` StoreOrder state machine; inbound SMS / delivery webhooks; OTP login.

## Decisions
- **Raw `urllib`, not `requests`.** The codebase has no `requests` dependency and already calls external APIs via `urllib` (`seo_assistant/ai.py`, `assistant/ai.py`). Keep it consistent; no new pip dependency.
- **Singleton `MessagingSettings`** (pk pinned to 1), same pattern as `core.SiteSettings` and `seo_assistant.SeoAssistantSettings`. The Kavenegar API key is **write-only** in the serializer and never returned by GET; a derived `api_key_configured` boolean is exposed instead.
- **Master switch + dry-run.** Sending is gated by `sms_enabled AND api_key`. When off/unconfigured, the attempt is still logged as `OutboundMessage(status="skipped")` with no error, so the CRM send flow, activity logging, and segment selection are all testable today. This also makes accidental cost impossible before the operator opts in.
- **`channel` field + `providers/` package for extensibility.** `OutboundMessage.channel` defaults to `sms`; Telegram/WhatsApp become new channels + new provider modules later, reusing the same log and service entry points.
- **Two Kavenegar send modes.** `verify/lookup` (template-based) is the correct path for transactional/purchase-step messages — highest priority, never filtered, no sender line needed — but requires a template pre-approved in the panel. `sms/send` (free-text) is used for general CRM messages and needs a `sender` line. The service picks `lookup` when a template name is supplied, else `sms/send`.
- **Iranian phone normalization.** `+98XXXXXXXXXX` / `0098…` / `98…` / `9XXXXXXXXX` are normalized to `09XXXXXXXXX` before sending and logging, so the same customer maps to one recipient string.
- **Mount at `/api/messaging/`** (not under `/api/crm/`) because it also serves direct-sales/purchase-step notifications, not only CRM. Guarded by `IsAdminOrActiveAdminRole` with a new `messaging` admin section (granted to MARKETER, who handles CRM/sales).

## Risks / Trade-offs
- **Real SMS costs money and can be filtered.** → default `sms_enabled=False`, dry-run logging, and a `daily_send_cap`; transactional messages use `verify/lookup` to avoid the advertising filter.
- **Bulk blasts could be abused/duplicated.** → `send_bulk` runs sequentially, honors the daily cap, and logs each recipient separately; Kavenegar `localid` de-duplication can be added later.
- **Provider envelope quirks.** Kavenegar returns a `{"return": {...}, "entries": [...]}` envelope; non-200 `return.status` codes (e.g. 418 insufficient credit, 411 bad receptor) are surfaced into `OutboundMessage.error` instead of raising, so a bad send never 500s the request.

## Migration Plan
- New app `messaging` with migration `0001_initial` (two tables). Register in `INSTALLED_APPS`, root urls, and `accounts/admin_sections.py`. No changes to existing tables, so deploy is additive; `python manage.py migrate` only creates the new tables. Rollback = remove the app + its migration (no data depended on by other apps).

## Open Questions
- Auto-fire purchase-step SMS from `sales` StoreOrder transitions (vs. the manual `notify-step` endpoint shipped here) — deferred.
- Telegram requires collecting each customer's `chat_id` via a bot opt-in (deep link sent over SMS) — deferred to a Telegram phase.
- WhatsApp needs a third-party gateway (Kavenegar has none) — deferred.
