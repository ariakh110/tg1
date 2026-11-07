# تحویل: موتور فروش CRM

## هدف و وضعیت

پیاده‌سازی محلیِ برش صف فروش CRM طبق درخواست «پیاده سازی کن» تمام شد؛ بازبینی انطباق با SPEC و بازبینی کیفیت هر دو pass شدند. کار هنوز deploy یا روی پایگاه داده اعمال نشده است.

## تصمیم‌های پذیرفته‌شده

- فعلاً یک اپراتور CRM وجود دارد؛ تخصیص خودکار فقط در صورت تشخیص یک مالک فعال یکتا انجام می‌شود.
- task و یادآوری داخلی خودکار است؛ SMS و بله به مشتری دستی می‌ماند و برای task جدید موعد/SLA ساختگی ایجاد نمی‌شود.
- opportunity از `Customer` فعلی برای هویت سرنخ استفاده می‌کند؛ `CrmLead` مستقل در scope این برش نیست.
- handoff عمومی frontend و handoffهای خرید/کاتالوگ دست‌نخورده نگه داشته شدند.

## مرجع‌ها

- OpenSpec: `openspec/changes/add-site-native-crm-workspace/`
- مشخصات: `docs/engineering/bmad-output/specs/spec-crm-sales-engine/SPEC.md`
- برنامهٔ تأییدشده: `docs/superpowers/plans/2026-11-07-crm-sales-engine.md`
- گزارش: `docs/engineering/reports/crm-sales-engine-implementation.fa.md`
- UX: `../kavehmetal front/docs/engineering/bmad-output/planning-artifacts/ux-designs/ux-KavehMetal-crm-sales-engine-2026-11-07/`

## فایل‌های محصول

- Backend: `customers/models.py`, `customers/automation.py`, `customers/migrations/0009_crm_sales_engine.py`, `customers/opportunities.py`, `customers/signals.py`, `customers/serializers.py`, `customers/views.py`, `customers/urls.py`, `messaging/service.py`, `messaging/views.py`.
- Frontend: `app/components/admin/CrmWorkQueuePanel.js`, `CustomerCrmPanel.js`, `SalesFunnelPanel.js`, `CrmCampaignComposer.js`, `MessagingPanel.js`, `AdminDashboardPage.js`, `app/lib/crmApi.js`, `app/lib/adminNavigation.mjs`.
- OpenSpec checklist: `openspec/changes/add-site-native-crm-workspace/tasks.md`؛ taskهای 1.5 و 5.3 که این برش تکمیل کرد تیک خوردند. سایر قابلیت‌های وسیع‌تر باز ماندند.
- بازبینی انطباق: `docs/engineering/reports/crm-sales-engine-spec-review.fa.md`؛ بازبینی کیفیت: `docs/engineering/reports/crm-sales-engine-quality-review.fa.md`.

## بررسی‌های انجام‌شده

- Python compile و Django system check موفق شدند.
- بررسی migration گفت تغییری جا نمانده؛ PostgreSQL محلی در دسترس نبود و migration اعمال نشد.
- ESLint فایل‌های CRM به‌جز داشبورد: موفق. بررسی کل فایل‌های لمس‌شده پنج خطای lint در بخش‌های نامرتبط `AdminDashboardPage.js` گزارش کرد؛ جزئیات در گزارش پیاده‌سازی است.
- `git diff --check` خطای whitespace نداشت.
- تست، build، browser QA، ارسال provider و deploy انجام نشدند؛ بازبینی spec/کیفیت مستقل نبود.

## اقدام بعدی

پیش از rollout، migration را فقط در محیط پایگاه دادهٔ موردنظر اجرا و history/countهای داده را بررسی کن. هیچ پیام بیرونی یا deploy از این handoff مجاز نشده است.
