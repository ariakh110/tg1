# Design notes

## Decision 1 — Reuse `CustomerActivity` for stage history (no `StageChange` model)
Stage transitions are logged as a `CustomerActivity` with `kind="stage"` and two structured fields `stage_from` / `stage_to` (populated only for this kind). This keeps a single, unified customer timeline (a stage move shows up in history naturally next to calls/notes) and avoids a second table + second query for KPIs. The structured fields — rather than parsing the human‑readable `body` — make the KPI queries exact. Consistent with the earlier «one model for history + reminders» decision.

## Decision 2 — Auto-log on `perform_update`, capture the old value before save
`CustomerViewSet.perform_update` reads `serializer.instance.stage` (the pre‑save value), saves, then if the stage changed creates the `stage` activity with `created_by = request.user`. Stage edits made directly in Django admin are intentionally **not** logged (the owner works from the panel; covering admin would need model signals and risks double‑logging). The auto‑logged activity has no `follow_up_at`, so it never pollutes the follow‑ups dashboard.

## Decision 3 — KPIs: snapshot from cheap sources, time‑based from history
One `funnel` action returns everything in a single round‑trip (same pattern as the existing `follow_ups` action):
- **Funnel counts**: `Customer.objects.values("stage").annotate(Count)`.
- **Conversion rate**: `won+loyal` ÷ all customers (snapshot).
- **Ledger KPIs**: total sales = Σ purchases; outstanding = Σ positive balances; CLV proxy = total sales ÷ (won+loyal count). Reuses `CustomerTransaction` aggregation already used by `balance`.
- **Sales Cycle Length**: avg over customers that have a `stage_to="won"` activity of `(that activity's occurred_at − customer.created_at)`, in days.
- **Quote→Close**: customers that ever reached `stage_to="won"` ÷ customers that ever reached `stage_to="proposal"`.
Until enough history accrues, the time‑based KPIs return `null` and the UI shows «—».

## Decision 4 — Stage vocabulary mapping (data migration)
Old → new: `lead→new`, `contacted→nurturing`, `active→won`, `dormant→won`, `lost→lost`. The default changes `lead→new`. The data migration is reversible‑safe enough for this scale (~1 row); the reverse is a no‑op (old codes are gone).

## Final vocabularies (stable ASCII codes, Persian labels)
- `stage` (funnel order): `new` سرنخ · `nurturing` پرورش/اعتمادسازی · `proposal` پیش‌فاکتور · `negotiation` مذاکره/قرارداد · `won` مشتری فعال · `loyal` وفادار · `lost` ازدست‌رفته.
- `source` (added): `linkedin` لینکدین · `exhibition` نمایشگاه · `association` انجمن/سندیکا · `b2b_platform` پلتفرم B2B · `cold_call` تماس سرد · `field_sales` بازاریابی میدانی (kept: incoming_call, referral, website, instagram, walk_in, assistant, other).
- `CustomerActivity.kind` adds: `stage` تغییر مرحله.
