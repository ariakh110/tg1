# Change: CRM activity timeline, follow-ups, and daily dashboard

## Why
The CRM ledger (`add-customer-crm-ledger`) answers «who is this customer and how much do they owe?» but has no notion of the **sales process** itself. There is no record of *what was said* on the last call, no way to schedule «call back Thursday», and no morning view of «who must I follow up today». For a phone/in‑person steel sales desk this is exactly where deals are won or lost — a forgotten callback is a lost sale. This change adds the leanest layer that gives the owner control over the sales process: an interaction history per customer, scheduled follow‑ups with due dates, a sales stage and lead source, and a daily «follow‑ups due» dashboard so no lead falls through the cracks.

## What Changes
- **`Customer` gains `stage`** (سرنخ / در حال پیگیری / مشتری فعال / راکد / ازدست‌رفته) and **`source`** (تماس ورودی / معرفی / سایت / اینستاگرام / مراجعه حضوری / دستیار / سایر) — so the funnel and lead origin are visible, filterable, and editable.
- **New `CustomerActivity` model** — one row per touch: `kind` (تماس/پیام/جلسه/یادداشت), free‑text `body` (what happened / outcome), `occurred_at`, and an *optional scheduled follow‑up on the same row*: `follow_up_at`, `follow_up_note`, `follow_up_done` (+ `follow_up_done_at`), `created_by`. Logging a call and scheduling the next callback is a single action.
- **Admin CRM API additions** under `/api/crm/`: `activities` (CRUD, filter by customer, newest‑first timeline), `GET activities/follow_ups/` (open follow‑ups across all customers, bucketed سررسیده/امروز/این‌هفته with counts), `POST activities/<id>/complete/` (mark the follow‑up done). Customer payloads gain `stage`, `stage_display`, `source`, `source_display`, and annotated `next_follow_up_at` and `open_follow_up_count`.
- **Frontend**: customer detail gains an interaction timeline + a «ثبت فعالیت/پیگیری» form and an editable stage chip; a new admin tab «پیگیری‌ها» shows the daily follow‑up dashboard (سررسیده / امروز / این هفته) with one click to open the customer and «انجام شد».

Out of scope (later phases): assigning follow‑ups to specific salespeople, SMS/push reminders, recurring follow‑ups, a drag‑and‑drop Kanban board, and quote/proforma generation.

## Impact
- Affected specs: `customer-crm` (added requirements).
- Backend (tg1): `customers/models.py` (Customer `stage`/`source` + new `CustomerActivity`), `customers/serializers.py`, `customers/views.py`, `customers/urls.py`, `customers/admin.py`, migration `0002`.
- Frontend (kavehmetal): `app/lib/crmApi.js`, `app/components/admin/CustomerCrmPanel.js`, a new follow‑ups dashboard component, and tab wiring in `app/components/admin/AdminDashboardPage.js`.
- Migration `0002` runs on deploy; additive only; nothing in `sales`/`orders`/`assistant` changes. Same admin permission as the rest of the CRM (`IsAdminOrActiveAdminRole`).
