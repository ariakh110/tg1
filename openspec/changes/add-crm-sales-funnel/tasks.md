## 1. Backend (tg1)
- [x] 1.1 `Customer.STAGE_CHOICES` → funnel (`new`/`nurturing`/`proposal`/`negotiation`/`won`/`loyal`/`lost`), default `new`; expand `SOURCE_CHOICES` with `linkedin`/`exhibition`/`association`/`b2b_platform`/`cold_call`/`field_sales`
- [x] 1.2 `CustomerActivity`: add kind `stage` («تغییر مرحله») + `stage_from`/`stage_to` CharFields (blank)
- [x] 1.3 `CustomerActivitySerializer`: expose `stage_from`/`stage_to`
- [x] 1.4 `CustomerViewSet.perform_update`: if `stage` changed, auto-create a `kind="stage"` activity (`stage_from`/`stage_to`, `created_by`, body «مرحله: قبلی ← جدید»)
- [x] 1.5 `CustomerViewSet` `@action(detail=False) funnel` (GET): per-stage counts, conversion rate, ledger KPIs (total sales / outstanding / CLV proxy), new-this-month, open follow-ups, sales-cycle-days, quote→close ratio
- [x] 1.6 `makemigrations customers` → `0003` (AlterField stage/source + new activity fields) **and** `0004` data migration mapping old stage codes (lead→new, contacted→nurturing, active→won, dormant→won, lost→lost)
- [x] 1.7 `manage.py makemigrations --check --dry-run --settings=tg1.settings_test` + `manage.py check` clean; `migrate` on dev DB

## 2. Frontend (kavehmetal)
- [x] 2.1 `crmApi`: `fetchFunnel()`
- [x] 2.2 `CustomerCrmPanel`: replace `STAGE_OPTIONS`/`STAGE_TONE` with funnel stages; extend `SOURCE_OPTIONS`; render `kind="stage"` activities as a compact system note (not a full card)
- [x] 2.3 New `SalesFunnelPanel.js`: funnel bars (count per stage) + KPI cards (conversion, total sales, outstanding, CLV, new-this-month, open follow-ups, sales-cycle-days, quote→close); clean empty state
- [x] 2.4 Wire tab (id `crm-funnel`, label «قیف فروش», icon `Filter`) into `AdminDashboardPage`

## 3. Verification
- [x] 3.1 `manage.py test customers --settings=tg1.settings_test` (13 tests pass): stage-change auto-logs with stage_from/to; same-stage save does not log; funnel counts/conversion correct; cycle-length & quote→close from history; ledger KPIs correct; non-admin denied funnel
- [x] 3.2 `npm run lint` (eslint clean) + `npm run build` (compiled successfully, types OK)
- [x] 3.3 `openspec validate add-crm-sales-funnel --strict`
- [ ] 3.4 After deploy: change a customer's stage → timeline shows the transition and the funnel dashboard reflects the new distribution; record a purchase → total sales/CLV update
