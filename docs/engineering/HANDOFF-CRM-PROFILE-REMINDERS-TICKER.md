# پروندهٔ مشتری، یادآوری بله و نوار قیمت

## تغییرات ۲۷ نوامبر ۲۰۲۶

- موبایل هنگام ثبت تماس، نام، سمت و نقش در تصمیم خرید را همراه پیش‌نویس ذخیره می‌کند. سرنخ جدید یا پرونده‌ای که نامش فقط شمارهٔ موبایل است می‌تواند با همان فرم تکمیل شود. تغییر مشخصات مشتری نام‌دار از «ویرایش اطلاعات» انجام می‌شود. سایت و موبایل یک رکورد مشترک دارند.
- `PATCH /api/v1/crm/mobile/customers/<id>/` به کارشناس فروش فقط برای مشتری خودش مجوز می‌دهد. `PATCH /api/crm/customers/<id>/profile/` برای نقش‌های مجاز پنل سایت است. هر مسیر نام، شرکت، سمت و تصمیم‌گیرندگی را می‌پذیرد.
- زمان‌بند موجود `tirexa-inquiry-notices.timer` فرمانی را اجرا می‌کند که اکنون کارها و پیگیری‌های سررسیدشده را هم بررسی می‌کند. هر اجرا حداکثر سه یادآوری CRM را پردازش می‌کند. برای کار دارای مسئول، همان فرد مقصد است. برای کار بدون مسئول، مسئول مشتری و سپس ثبت‌کننده بررسی می‌شوند. مقصد باید حساب فعال با اتصال خصوصی بله باشد. ادعای ارسال برای هر کار، سررسید و گیرنده یکتاست.
- نوار سایت از `/api/products-summary/ticker/` آخرین ۱۶ محصول فعال قیمت‌دار را می‌گیرد و آن‌ها را بر اساس کارخانه، نوع/زیرنوع و اندازهٔ عددی نمایش می‌دهد.

## انتشار

ابتدا بک‌اند را با migration `customers.0012_crm_customer_profile_and_due_reminder` منتشر کنید. سپس فرانت‌اند و APK جدید را به کار بگیرید. زمان‌بند فعال قبلی همین فرمان را اجرا می‌کند. مدیر و فروشنده باید گفت‌وگوی خصوصی با همان ربات را شروع کنند و مدیر کامل شناسهٔ هر نفر را در «پیامک ← کاربران مجاز ربات بله» به حساب سایت همان نفر متصل کند.

تا این تحویل، تغییرات محلی هستند. رسید واقعی بله روی سرور بررسی نشده است.


## بررسی محلی

- ۳۱ تست مرتبط با پروندهٔ CRM، یادآوری خصوصی، بازار، اعلان استعلام و ربات بله موفق شدند. ارسال بله در تست‌ها شبیه‌سازی شد.
- ۸ خطای تست کمپین و پیامک در نسخهٔ قبلی مخزن هم بازتولید شد.
- Django check و بررسی سازگاری migration، ESLint فایل‌های تغییرکرده و ترتیب عددی نوار در دادهٔ نمونه موفق شدند. Flutter analyze بدون خطا تمام شد.


## Production receipt and future deployments

On 2026-11-27, the r2 release verified both archives, backed up PostgreSQL and backend source, applied customers.0012 and built the frontend. The live homepage returned HTTP 502 after activation because the staged directory belonged to www-data and the frontend service runs as tirexa-front. Correcting the directory ownership and restarting the frontend restored HTTP 200. External requests to the homepage and price ticker API also returned HTTP 200 after recovery. The database and backend backup are under /srv/tirexa/release-backups/crm-profile-20261127.boIPPz.

The corrected r3 deployment helper reads the systemd service user and group. The frontend release retains the previous directory until the local HTTPS homepage returns HTTP 200. The deployment fixture verifies that HTTP 502 restores the previous frontend. This r3 package is for future use. The production release has already been recovered.

## WinSCP and PuTTY for r3

Upload the three files from C:/Users/aria/deploy/crm-profile-reminders-ticker-20261127-r3 to /home/deploy/kavehmetal-release/ in binary mode:

- crm-profile-20261127-r3-backend.tar.gz
- crm-profile-20261127-r3-frontend.tar.gz
- deploy-crm-profile-20261127-r3.sh

```bash
cd /home/deploy/kavehmetal-release && sudo systemd-run --unit=tirexa-crm-profile-deploy-20261127-r3 --collect /bin/bash "$PWD/deploy-crm-profile-20261127-r3.sh" && sudo journalctl -u tirexa-crm-profile-deploy-20261127-r3 -n 40 -f
```

The release prints "CRM profile 20261127 r3: verifying package" and finishes successfully with CRM_PROFILE_DEPLOY_EXIT=0. Ctrl+C exits the log view. The service continues if the terminal disconnects.
