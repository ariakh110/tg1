# Design notes

## Why a `StoreOrder` signal, not a call site
Buyer submission doesn't flow through one obvious function — orders reach `SUBMITTED` from several places. A `pre_save`/`post_save` pair on `StoreOrder` (tracking the previous status) fires `on_order_submitted` exactly once, on the transition **into** `SUBMITTED`, regardless of code path. The extra per-save query is negligible at order volume. Registration and chat, by contrast, have one clear call site each, so they're wired explicitly (and get the phone directly).

## Safety: events never break the request
Every hook (`accounts` signup, `assistant` tools) wraps the call in `try/except: pass`, and `messaging/events.py` itself swallows-and-logs. Providers (`kavenegar`, `telegram`) return a `SendResult` with an error string instead of raising. A misconfigured bot or a dead network can never 500 a signup, checkout, or chat reply.

## Dry-run by default
Nothing sends until configured. `notify_admin` with no Telegram and no admin phone logs a single `skipped` row so the event is still auditable. This mirrors the existing SMS dry-run and lets the whole pipeline be tested before a bot token exists.

## `upsert_lead` fill-blanks-only
A returning visitor or repeat buyer must not clobber the CRM record the admin has curated. `get_or_create` by normalized phone; on an existing row only blank fields (name/company/city/user) are filled and stage/source are left untouched. Source is set only at creation, so it reflects the *first* channel the lead arrived through.

## `created_by` semantics
`created_by` answers "who entered this customer": the admin on a manual create, `null` for system/automatic intake (the `source` already says which channel). It is read-only over the API; the serializer returns `created_by_name` for display.
