# موتور فروش CRM — برنامهٔ پیاده‌سازی

> **برای مجری:** برای اجرای این برنامه از `superpowers:executing-plans` استفاده کن. این برنامه با OpenSpec `add-site-native-crm-workspace` و SPEC صف فروش پیوند دارد.

**هدف:** صف فروش CRM را به نقطهٔ اصلی کار روزانه تبدیل کنیم؛ سرنخ‌ها و فرصت‌ها قابل پیگیری شوند، کارهای داخلی از رویدادهای مجاز ساخته شوند و پیام بیرونی فقط با تأیید دستی و رضایت کانال ارسال شود.

**معماری:** بک‌اند Django/DRF مالک مدل کار، follow-up، consent و اجرای idempotent اتوماسیون است. پنل Next.js از یک API صف، نمای CRM RTL، API موجود پیام‌رسانی و مسیرهای فعلی فرصت استفاده می‌کند. `Customer.stage` و `CrmOpportunity.stage` مستقل می‌مانند.

**فناوری:** Django، Django REST Framework، دیتابیس موجود پروژه، Next.js، React و Tailwind موجود.

**مشخصات:** `docs/engineering/bmad-output/specs/spec-crm-sales-engine/SPEC.md`؛ قرارداد UX در مخزن frontend؛ تغییر OpenSpec: `openspec/changes/add-site-native-crm-workspace`.

## محدودیت‌های سراسری

- کاربر فعلی یک اپراتور است؛ تخصیص تیمی و round-robin در این برش نیست.
- یادآوری فقط در صف و اعلان پنل است؛ SMS/Bale خودکار برای مشتری یا اپراتور فعال نمی‌شود.
- هر پیام مشتری نیازمند بررسی و اقدام صریح دستی است؛ وضعیت رضایت نامعلوم یا لغوشده اجازهٔ ارسال نمی‌دهد.
- قیف رابطهٔ مشتری و قیف هر فرصت مستقل‌اند.
- سفارش، پرداخت، محصول، انبار و لجستیک از مدل‌ها و سرویس‌های اصلی سایت خوانده/تغییر داده می‌شوند.
- محرک‌ها و اقدام‌های اتوماسیون whitelist شده، idempotent، قابل ممیزی و retryable هستند؛ کد دلخواه اجرا نمی‌شود.
- تغییرات UI از توکن‌ها و الگوهای فعلی فارسی/RTL استفاده می‌کنند و در عرض موبایل بدون اسکرول افقی می‌مانند.
- در این اجرا تست جدید اضافه یا تست اجرا نمی‌شود؛ این محدودیت از دستور سطح نشست است و برخواسته از بی‌نیازی محصول نیست.

## تمرکز بازبینی

- replay یک event سایت نباید task/follow-up یا تغییر مرحلهٔ تکراری بسازد.
- مشتری با چند فرصت باید هر فرصت و موعد خودش را ببیند؛ پایان یک فرصت نباید قیف مشتری را بازنویسی کند.
- task بدون مالک یا بدون موعد باید در صف استثنا بماند و از دید اپراتور پنهان نشود.
- شمارهٔ بدون consent یا با consent لغوشده نباید به SMS/Bale منفرد یا کمپین برسد.
- دسترسی CRM بدون مجوز messaging نباید امکان یا کنترل ارسال پیام نشان دهد؛ API نیز باید دسترسی را بررسی کند.

---

### کار ۱: مدل‌های کار، پیگیری، اتوماسیون و consent

**فایل‌ها:**
- تغییر: `customers/models.py`
- ایجاد migration جدید در `customers/migrations/`
- تغییر: `messaging/models.py` و migration جدید در `messaging/migrations/` فقط اگر consent مخاطب خام گروه برای حفظ کمپین‌های فعلی لازم شود.

**رابط‌ها:**
- `CrmFollowUp`: مشتری، فرصت اختیاری، مسئول، موعد، کانال، هدف، وضعیت، نتیجه، metadata یادآوری، `source_activity` یکتا و `idempotency_key` یکتا.
- `CrmTask`: مشتری/فرصت/سفارش اختیاری، مسئول، عنوان، توضیح، موعد nullable، وضعیت، نتیجه و `idempotency_key` یکتا.
- `CrmAutomationRun`: `event_key` یکتا، trigger محدود، وضعیت، تعداد تلاش، خطا، payload و زمان پردازش.
- `CrmContactChannel`: یک ردیف برای هر مشتری/کانال SMS یا Bale؛ consent برابر `unknown`, `granted` یا `revoked`، منشأ، زمان و ویرایشگر.
- `CustomerActivity`: فرصت اختیاری، جهت تعامل، نتیجه و کلید بیرونی پیام؛ سفارش/مالی همچنان از مدل اصلی خوانده می‌شود.
- حفظ ستون‌های قدیمی `CustomerActivity.follow_up_*`; migration کپی‌کنندهٔ پیگیری‌های باز با کلید `legacy-activity:<id>` و پیوند منبع.

- [ ] **گام ۱:** نام آخرین migration هر دو اپ را از فایل‌های موجود بخوان و ترتیب migration افزایشی را با وابستگی‌های موجود تثبیت کن.
- [ ] **گام ۲:** چهار مدل و constraintهای یکتایی/ایندکس موعد و وضعیت را در فایل‌های مدل بساز؛ هیچ دادهٔ سفارش/پرداختی را کپی نکن.
- [ ] **گام ۳:** migration افزایشی و data migration بساز که پیگیری‌های باز قدیمی را بدون حذف یا بازنویسی فعالیت‌ها به `CrmFollowUp` وصل کند.
- [ ] **گام ۴:** تعریف reverse migration را برای دادهٔ تازه‌ساخته‌شده روشن نگه دار؛ migration قدیمی را تغییر نده.
- [ ] **گام ۵:** نتیجهٔ migration و مدل‌ها را با بررسی ایستا و خواندن SQL/operations تولیدشده مرور کن؛ migration را روی پایگاه دادهٔ واقعی اجرا نکن.

### کار ۲: سرویس whitelist اتوماسیون و اتصال به رویدادهای CRM

**فایل‌ها:**
- ایجاد: `customers/automation.py`
- تغییر: `customers/services.py`
- تغییر: `customers/opportunities.py`
- تغییر: `customers/signals.py`
- تغییر: `customers/views.py` (`CustomerViewSet.perform_create` و `CrmOpportunityViewSet.perform_create`)
- تغییر: `messaging/events.py`
- تغییر: `assistant/purchase_inquiries.py` فقط برای عبور کلید idempotency موجود

**رابط‌ها:**
- `enqueue_automation_event(*, event_key, trigger, customer=None, opportunity=None, actor=None) -> CrmAutomationRun`
- `process_automation_run(run_or_id) -> CrmAutomationRun`
- triggerهای مجاز نسخهٔ اول: `customer.created` برای task تماس اولیه و `opportunity.stage_changed` برای task بازبینی مرحله.
- رویداد مشتری جدید task داخلی بدون SLA ساختگی می‌سازد و فوراً در `unscheduled/needs_action` دیده می‌شود؛ فرصت بدون `next_follow_up_at` نیز task «بدون موعد» می‌سازد. پیام بیرونی ساخته نمی‌شود.
- اجرای ناموفق status و خطا را نگه می‌دارد؛ retry همان `idempotency_key` را استفاده می‌کند.

- [ ] **گام ۱:** مسیرهای فعلی `upsert_lead`, `sync_store_order_opportunity`, `sync_assistant_inquiry_opportunity` و `transition_opportunity` را دنبال کن و کلید رویداد پایدار را از شناسهٔ منبع/تاریخچه بگیر.
- [ ] **گام ۲:** اجرای whitelist را در `customers/automation.py` بنویس؛ کارها را با `get_or_create` بر اساس event key بساز و اجرای تکراری را بی‌اثر نگه دار.
- [ ] **گام ۳:** اجرا را بعد از commit زمان‌بندی کن؛ خطای task نباید signup، سفارش، پرداخت یا انتقال مرحلهٔ منبع را rollback کند.
- [ ] **گام ۴:** مالک خودکار را فقط وقتی یک مدیر فعال یکتا قابل تشخیص است انتخاب کن؛ در غیر این صورت task بدون مالک را برای صف استثنا نگه دار.
- [ ] **گام ۵:** follow-upهای خودکار مرتبط با فرصت بسته‌شده را لغو کن و history کامل‌شده را حفظ کن.

### کار ۳: API صف، task و follow-up

**فایل‌ها:**
- تغییر: `customers/serializers.py`
- تغییر: `customers/views.py`
- تغییر: `customers/urls.py`
- ایجاد فایل pagination فقط اگر قرارداد صفحه‌بندی DRF موجود برای CRM کافی نباشد.

**رابط‌ها:**
- `GET /crm/work-queue/`: گروه‌های `overdue`, `today`, `upcoming`, `unscheduled`, `needs_action`, `automation_errors` و شمارنده‌های هر گروه.
- `GET/POST /crm/tasks/`, `POST /crm/tasks/{id}/complete/`, `POST /crm/tasks/{id}/snooze/`؛ snooze بدون `due_at` تازه رد شود.
- `GET/POST /crm/follow-ups/`, complete/snooze/cancel با نتیجه و موعد معتبر.
- `POST /crm/automation-runs/{id}/retry/` فقط برای خطاهای retryable.
- `PUT /crm/customers/{id}/contact-channels/` برای ثبت رضایت کانال، و نمایش read-only آن در پروفایل مشتری.
- `CustomerDetailSerializer` تاریخچهٔ activity، follow-up و opportunity را در یک پاسخ به هم پیوند می‌دهد.

- [ ] **گام ۱:** serializerهای read/write را با فیلدهای صریح و اعتبارسنجی status/due/result اضافه کن.
- [ ] **گام ۲:** viewsetها و retry خطا را با permission بخش `crm` محدود کن؛ هیچ endpoint عمومی برای عملیات CRM نساز.
- [ ] **گام ۳:** صف را در timezone محلی گروه‌بندی کن؛ overdue، امروز، آینده، بدون موعد و opportunity بدون اقدام را جدا برگردان.
- [ ] **گام ۴:** `CustomerActivity.follow_ups` را تا وقتی مصرف‌کنندهٔ فعلی استفاده می‌کند backward-compatible نگه دار و شمارنده‌های funnel را با رکوردهای migrated دوباره جمع بزن.
- [ ] **گام ۵:** `CustomerViewSet` را از فهرست بدون صفحه‌بندی به صفحه‌بندی ۵۰ ردیفی تبدیل کن؛ search و stage/source filter را سمت سرور نگه دار.

### کار ۴: صف فروش و اقدام‌های فرصت در پنل

**فایل‌ها:**
- ایجاد: `app/components/admin/CrmWorkQueuePanel.js`
- تغییر: `app/components/admin/AdminDashboardPage.js`
- تغییر: `app/lib/adminNavigation.mjs`
- تغییر: `app/components/admin/FollowUpsPanel.js`
- تغییر: `app/components/admin/SalesFunnelPanel.js`
- تغییر: `app/components/admin/CustomerCrmPanel.js`
- تغییر: `app/lib/crmApi.js`

**رابط‌ها:**
- `fetchCrmWorkQueue()`، `createCrmTask(payload)`، `completeCrmTask(id, result)`، `snoozeCrmTask(id, dueAt)`، و APIهای follow-up.
- `crm-sales` مقصد جدید CRM و ورودی پیش‌فرض صف کار است؛ میانبرهای قبلی CRM/پیگیری/قیف حفظ می‌شوند.
- صف به ترتیب عقب‌افتاده، امروز، سرنخ جدید، بدون اقدام بعدی و بدون موعد؛ ردیف به پرونده مشتری/فرصت باز می‌شود.
- فرصت دستی از پنل قابل ثبت است؛ فرصت دستی امکان انتقال مرحله دارد و فرصت متصل به StoreOrder/AssistantInquiry فقط با وضعیت منبع تغییر می‌کند.
- وضعیت‌های loading/empty/error/retry، کنترل صفحه‌کلید، اقدام لمسی، تماس مستقیم و فرم ثبت نتیجه/موعد.

- [ ] **گام ۱:** کلاینت‌های typed-by-convention در `crmApi.js` را به endpointهای کار اضافه کن و شکل خطاهای فعلی `readJson` را حفظ کن.
- [ ] **گام ۲:** مقصد `crm-sales` را در گروه مشتریان ثبت و پنل را بر اساس `activePanel` در داشبورد نمایش بده.
- [ ] **گام ۳:** صف گروه‌بندی‌شده را در کامپوننت مستقل بساز؛ برای snooze، موعد جدید اجباری و برای complete، نتیجهٔ اختیاری ثبت شود.
- [ ] **گام ۴:** مسیر بازکردن مشتری را به `CustomerCrmPanel` وصل کن و برای task مرتبط با فرصت، شناسهٔ فرصت/منبع را در ردیف نشان بده.
- [ ] **گام ۵:** در `SalesFunnelPanel` فهرست را از ۱۲ ردیف اخیر فراتر ببر و کنترل transition را فقط برای فرصت‌های دستی نشان بده؛ فرصت منبع سایت توضیح بده که مرحله از سفارش/استعلام می‌آید.
- [ ] **گام ۶:** فرم ساخت فرصت دستی را با customer، title، need، مبلغ اختیاری، اقدام بعدی و موعد به API موجود وصل کن.
- [ ] **گام ۷:** endpoint فهرست مشتریان را در `CustomerCrmPanel` صفحه‌به‌صفحه مصرف کن و search/stage/source را سمت سرور اعمال کن؛ انتخاب گروه فقط روی مشتری‌های صفحهٔ جاری اثر بگذارد و شمارندهٔ کل با صفحه اشتباه نشود.

### کار ۵: رضایت کانال و ارسال بیرونی صریح و دستی

**فایل‌ها:**
- تغییر: `messaging/views.py`
- تغییر: `messaging/service.py`
- تغییر: `app/components/admin/CustomerCrmPanel.js`
- تغییر: `app/components/admin/CrmCampaignComposer.js`
- تغییر: `app/lib/crmApi.js`
- تغییر: `app/lib/messagingApi.js`
- تغییر: `app/components/admin/AdminDashboardPage.js`

**رابط‌ها:**
- preview مخاطب تعداد مجاز و حذف‌شده به علت consent را جدا می‌دهد.
- پیام CRM-linked به channel رضایت `granted` نیاز دارد؛ `unknown/revoked` مسدود است. مخاطب خام گروه بدون Customer consent برای کمپین رد می‌شود.
- endpointهای single/bulk send به `confirmed: true` نیاز دارند؛ UI گیرنده/کانال/متن/تعداد را قبل از اقدام انسانی نشان می‌دهد.
- CRM بدون مجوز `messaging` دکمه/فرم کمپین را نشان نمی‌دهد؛ backend permission موجود حفظ می‌شود.

- [ ] **گام ۱:** helper مشترک consent را برای channel sms/bale بساز و preview و send از همان predicate استفاده کنند.
- [ ] **گام ۲:** `resolve_audience` را با channel هماهنگ کن؛ مشتریان بدون رضایت را به گیرندهٔ قابل‌ارسال اضافه نکن و علت/تعداد exclusion را در preview برگردان.
- [ ] **گام ۳:** single/bulk endpoint تأیید صریح را الزامی کند؛ پیام نامجاز را پیش از تماس با provider رد کن و `OutboundMessage` audit را برای ارسال‌های مجاز حفظ کن.
- [ ] **گام ۴:** وضعیت کانال را در پروندهٔ مشتری قابل مشاهده/ویرایش کن؛ ارسال تکی با گیرنده و کانال مشخص و `window.confirm` دستی اجرا شود.
- [ ] **گام ۵:** کمپین consent exclusion را قبل از confirm نشان دهد، پس از هر تغییر audience/channel preview را باطل کند و فقط گیرندگان مجاز را به endpoint بفرستد.
- [ ] **گام ۶:** `canAccessSection(user, "messaging")` را در UI برای کنترل کمپین مصرف کن؛ هیچ provider send واقعی از اجرای این برنامه انجام نشود.

### کار ۶: به‌روزرسانی OpenSpec و ثبت handoff

**فایل‌ها:**
- تغییر: `openspec/changes/add-site-native-crm-workspace/tasks.md`
- تغییر یا ایجاد handoff اختصاصی برای CRM؛ از بازنویسی handoff خرید/کاتالوگ خودداری شود.
- تغییر: `docs/engineering/reports/crm-sales-engine-implementation.fa.md`

- [ ] **گام ۱:** فقط taskهای OpenSpec که واقعاً تحویل شده‌اند را تیک بزن؛ taskهای sequence، custom fields، Excel و Bale را باز بگذار.
- [ ] **گام ۲:** گزارش فارسی را با فایل‌های واقعی، migrationها، endpointها، محدودیت‌های verification و تصمیم‌های اتوماسیون به‌روز کن.
- [ ] **گام ۳:** handoff CRM را با تصمیم‌های تأییدشده و وضعیت گیت پیاده‌سازی ثبت کن؛ فایل‌های محلی تغییرکردهٔ پیشین را دست‌نخورده بگذار.

## اجرای این برنامه

- این برنامه inline اجرا می‌شود؛ دسترسی subagent در این نشست ممنوع است و تقسیم پیاده‌سازی بین agentها انجام نمی‌شود.
- پیش از تغییر کد، وضعیت فایل‌ها و شاخهٔ فعال دوباره بررسی شود؛ شاخهٔ فعلی `dev-ariakhayer` است.
- هیچ تستی اضافه یا اجرا نشود مگر مالک جداگانه test/verification را درخواست کند. بررسی کد و گزارش محدودیت به‌جای ادعای تست ثبت شود.
