# Design notes

## Decision 1 — One model for both history and reminders (not a separate Task model)
A `CustomerActivity` row carries both *what happened* (`kind`, `body`, `occurred_at`) and an *optional next step* (`follow_up_at`, `follow_up_note`, `follow_up_done`). This matches how a phone seller actually thinks — «I called, gave the price, call back Thursday» is one mental action, so it is one record and one form. A separate `Task`/`FollowUp` table would be more normalized but doubles the models, the endpoints, and the UI for no benefit at this scale (CRM is effectively greenfield: ~1 customer today). An open follow‑up is simply `follow_up_at IS NOT NULL AND follow_up_done = false`; the daily dashboard is one query over that.

When a follow‑up is completed, the row is marked done (`follow_up_done = true`, `follow_up_done_at = now`) and the seller typically logs a *new* activity for the call they just made — so the timeline stays a faithful, append‑only history.

## Decision 2 — Derive `next_follow_up_at` / `open_follow_up_count`, don't denormalize on Customer
The customer list shows a follow‑up badge and the funnel stage. Rather than storing a denormalized `next_follow_up_at` on `Customer` (which must be kept in sync on every activity save/delete), the customer queryset annotates `next_follow_up_at = Min(follow_up_at where not done)` and `open_follow_up_count`. At this data scale annotation is free and there is nothing to keep in sync. `stage` and `source` *are* stored fields because they are entered by a human, not derived.

## Decision 3 — Follow‑up buckets computed server‑side against the operator's day
`GET /crm/activities/follow_ups/` returns open follow‑ups split into `overdue` (before today), `today`, and `upcoming` (within the next 7 days), plus counts, ordered by `follow_up_at`. Bucketing on the server keeps the «امروز/سررسیده» semantics consistent and avoids each client re‑implementing date math. «این هفته» is a rolling 7‑day window from today, not a calendar week. Items further than 7 days out are omitted from the dashboard (they are still visible on the customer's timeline).

## Decision 4 — New admin tab for the dashboard, inline timeline for the detail
The daily «who do I call today» view is the thing the owner opens every morning, so it earns its own top‑level tab («پیگیری‌ها»). Logging an activity and scheduling the next step is contextual to one customer, so it lives inside the existing customer detail panel. This keeps the existing «مشتریان (CRM)» tab focused and adds one purpose‑built dashboard rather than burying it.

## Stage and source vocabularies (stable ASCII codes, Persian labels)
- `stage`: `lead` سرنخ · `contacted` در حال پیگیری · `active` مشتری فعال · `dormant` راکد · `lost` ازدست‌رفته. Default `lead`.
- `source`: `incoming_call` تماس ورودی · `referral` معرفی · `website` سایت · `instagram` اینستاگرام · `walk_in` مراجعه حضوری · `assistant` دستیار · `other` سایر. Default `other`.
- `CustomerActivity.kind`: `call` تماس · `message` پیام · `meeting` جلسه · `note` یادداشت. Default `call`.
