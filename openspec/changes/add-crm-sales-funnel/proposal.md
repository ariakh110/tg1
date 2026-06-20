# Change: B2B steel sales funnel — stage pipeline, stage history, and funnel/KPI dashboard

## Why
The owner adopted an AI‑authored B2B steel sales playbook built around a six‑stage funnel (awareness → lead → nurturing → proposal → conversion → loyalty). The CRM today has a generic five‑value `stage` (lead/contacted/active/dormant/lost) and no way to *see the funnel* or measure it. This change turns that playbook into something operable: a funnel‑aligned stage pipeline, an automatic record of every stage transition (so cycle‑time and quote‑to‑close can actually be measured), and a «قیف فروش» dashboard that shows where deals sit, the conversion rate, sales/receivable/CLV from the ledger, and the time‑based KPIs the playbook calls for. It builds directly on the just‑added `Customer.stage/source`, `CustomerActivity`, and ledger — nothing here duplicates existing machinery.

## What Changes
- **Funnel stage vocabulary** — `Customer.stage` is redefined to the B2B funnel: `new` (سرنخ) → `nurturing` (پرورش/اعتمادسازی) → `proposal` (پیش‌فاکتور) → `negotiation` (مذاکره/قرارداد) → `won` (مشتری فعال) → `loyal` (وفادار), plus `lost` (ازدست‌رفته). New default is `new`. A data migration maps existing values (lead→new, contacted→nurturing, active→won, dormant→won, lost→lost).
- **Expanded lead sources** — `Customer.source` gains B2B channels from the playbook: `linkedin`, `exhibition` (نمایشگاه), `association` (انجمن/سندیکا), `b2b_platform` (فولاد۲۴/آهن‌آنلاین), `cold_call` (تماس سرد), `field_sales` (بازاریابی میدانی) — alongside the existing values.
- **Stage‑change history (reuses `CustomerActivity`, no new model)** — a new activity kind `stage` («تغییر مرحله») plus structured `stage_from`/`stage_to` fields. When `stage` changes via the API, the system auto‑logs one such activity (with the acting admin). This makes Sales Cycle Length and Quote→Close measurable over time.
- **Funnel/KPI endpoint & dashboard** — `GET /api/crm/customers/funnel/` returns per‑stage counts, conversion rate, total sales / outstanding receivable / CLV proxy (from the ledger), new customers this month, open follow‑ups, and the two time‑based KPIs (avg sales‑cycle days, quote→close ratio). A new admin tab «قیف فروش» (`SalesFunnelPanel`) renders the funnel bars + KPI cards.

Out of scope (deferred / strategy, not software here): Kanban drag board, proforma/quote generation, ABM automation, LinkedIn scraping, SMS newsletter, CAC (needs manual marketing‑cost input).

## Impact
- Affected specs: `customer-crm` (modified stage requirement; added funnel + stage‑history requirements).
- Backend (tg1): `customers/models.py` (STAGE_CHOICES/SOURCE_CHOICES, `CustomerActivity` kind `stage` + `stage_from`/`stage_to`), `customers/serializers.py`, `customers/views.py` (`perform_update` auto‑log + `funnel` action), `customers/admin.py`, migration `0003` (AlterField + data map + new fields).
- Frontend (kavehmetal): `app/lib/crmApi.js` (`fetchFunnel`), `app/components/admin/CustomerCrmPanel.js` (new STAGE/SOURCE options, render `stage` activity as a system note), new `app/components/admin/SalesFunnelPanel.js`, tab wiring in `AdminDashboardPage.js`.
- Migration `0003` runs on deploy; additive + a safe data remap; nothing in `sales`/`orders`/`assistant` changes.
