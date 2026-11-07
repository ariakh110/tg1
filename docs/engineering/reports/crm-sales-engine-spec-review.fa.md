# بازبینی انطباق با SPEC موتور فروش CRM

## نتیجه

**Pass برای scope برنامهٔ تأییدشدهٔ صف فروش CRM.** این نتیجه به معنی تکمیل change بزرگ‌تر `add-site-native-crm-workspace` نیست؛ قابلیت‌های خارج از برنامه در گزارش پیاده‌سازی و OpenSpec باز مانده‌اند.

## معیارهای SPEC و شواهد کد

| معیار | شواهد | نتیجه |
| --- | --- | --- |
| صف یکپارچهٔ کارهای عقب‌افتاده، امروز، آینده، بدون موعد، سرنخ تازه و فرصت بدون اقدام؛ بازکردن مشتری/فرصت | `customers/views.py:CrmWorkQueueView`; `CrmWorkQueuePanel.js` | مطابق؛ `new_leads` از `needs_action` جداست و پیگیری قدیمی با موعد در گروه زمانی می‌آید. |
| ثبت فعالیت روی فرصت و فرصت دستی؛ حفظ قیف مشتری و منبع وب‌سایت | `CustomerActivitySerializer`, `transition_opportunity`, `SalesFunnelPanel.js` | مطابق؛ فرصت منبع فقط از جریان منبع به مرحله می‌رود. |
| ساخت idempotent کار داخلی، ثبت خطا و retry؛ بدون موعد ساختگی | `customers/automation.py`; `customers/signals.py`; `customers/opportunities.py` | مطابق برای دو trigger whitelist شدهٔ `customer.created` و `opportunity.stage_changed`. |
| ارسال بیرونی فقط با اقدام صریح؛ نمایش نتیجه و رعایت رضایت کانال | `messaging/views.py`; `messaging/service.py`; `CustomerCrmPanel.js`; `CrmCampaignComposer.js` | مطابق؛ ارسال به CRM contact بدون رضایت کانال رد می‌شود و مخاطب کمپین در زمان ارسال دوباره محاسبه می‌شود. |
| تجربهٔ عملیاتی یک اپراتور و task بی‌موعد/بی‌مالک قابل مشاهده | `CrmWorkQueueView`; `CrmWorkQueuePanel.js` | مطابق؛ تخصیص مبهم مالک به `null` می‌انجامد و گروه صف قابل مشاهده است. |

## استثناها و مرز نتیجه

- مدل مستقل `CrmLead` و Lead inbox ساخته نشده‌اند؛ `Customer` موجود هویت سرنخ است. برنامهٔ این برش صریحاً این انتخاب را ثبت کرده بود.
- این بازبینی بر کد و قرارداد متمرکز است؛ تست رفتاری، build، browser QA یا اجرای migration انجام نشده است.
- قضاوت spec و پیاده‌سازی را همان مجری انجام داد؛ بازبین مستقل وجود نداشت.
- وضعیت checklist سراسری و قابلیت‌های باقیمانده در `openspec/changes/add-site-native-crm-workspace/tasks.md` مستقل از این pass باقی می‌ماند.
