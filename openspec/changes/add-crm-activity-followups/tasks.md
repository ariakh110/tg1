## 1. Backend (tg1)
- [x] 1.1 `Customer`: add `stage` (choices, default `lead`, db_index) and `source` (choices, default `other`, db_index)
- [x] 1.2 New `CustomerActivity` model: `customer` FK (`related_name="activities"`), `kind` (call/message/meeting/note), `body`, `occurred_at` (default now), `follow_up_at` (null, db_index), `follow_up_note`, `follow_up_done` (default False, db_index), `follow_up_done_at`, `created_by`, timestamps; `ordering = ["-occurred_at", "-id"]`; index on `(customer, occurred_at)` and `(follow_up_done, follow_up_at)`
- [x] 1.3 `makemigrations customers` → `0002`
- [x] 1.4 Serializers: `CustomerActivitySerializer` (kind_display, follow-up fields, customer_name/phone); extend `CustomerSerializer` with `stage`/`stage_display`/`source`/`source_display` + annotated read-only `next_follow_up_at` and `open_follow_up_count`; include `activities` in `CustomerDetailSerializer`
- [x] 1.5 `CustomerViewSet`: annotate queryset with `next_follow_up_at` (Min of open follow-ups) and `open_follow_up_count`; allow `stage`/`source`/`is_active` filter
- [x] 1.6 `CustomerActivityViewSet` (`IsAdminOrActiveAdminRole`): CRUD, filter by `customer`/`kind`/`follow_up_done`, `perform_create` sets `created_by`; `@action follow_ups` (GET → `{overdue, today, upcoming, counts}` bucketed by `follow_up_at`); `@action(detail=True) complete` (POST → set `follow_up_done=True`, `follow_up_done_at=now`)
- [x] 1.7 Register `activities` route in `customers/urls.py`
- [x] 1.8 Django admin: register `CustomerActivity` (list_display kind/customer/occurred_at/follow_up_at/follow_up_done) + inline on the customer page; add `stage`/`source` to `Customer` admin list/filter
- [x] 1.9 `manage.py makemigrations --check --dry-run --settings=tg1.settings_test` and `manage.py check` clean

## 2. Frontend (kavehmetal)
- [x] 2.1 `crmApi`: `fetchActivities(customerId)`, `createActivity(payload)`, `updateActivity(id, payload)`, `deleteActivity(id)`, `completeFollowUp(id)`, `fetchFollowUps()`
- [x] 2.2 `CustomerCrmPanel` customer detail: interaction timeline + «ثبت فعالیت/پیگیری» form (kind select, body, optional follow-up date + note, quick «فردا/۳ روز/هفتهٔ بعد»); editable `stage` chip; show `source`; source select on new-customer form
- [x] 2.3 New «پیگیری‌ها» dashboard component (`FollowUpsPanel`): سررسیده / امروز / این هفته lists with counts, customer name+phone, «انجام شد» button, click → open customer in CRM tab
- [x] 2.4 Wire new tab (id `crm-followups`, label «پیگیری‌ها») into `AdminDashboardPage` tab list + panel switch + focus-customer handoff from dashboard to CRM tab

## 3. Verification
- [x] 3.1 `manage.py test customers --settings=tg1.settings_test` (7 tests: stage default, payload annotations, access control, timeline, follow_ups buckets, complete keeps history, complete rejects no-follow-up); `npx eslint` clean on changed files
- [x] 3.2 `openspec validate add-crm-activity-followups --strict`
- [ ] 3.3 After deploy: log a call with a follow-up dated tomorrow → it appears under «امروز» the next day, «سررسیده» the day after; «انجام شد» removes it from the dashboard but keeps it on the timeline; changing stage persists
