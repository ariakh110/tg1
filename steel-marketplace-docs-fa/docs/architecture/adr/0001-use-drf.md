# ADR-0001: استفاده از Django REST Framework برای API

- **وضعیت:** پذیرفته‌شده (Accepted)
- **تاریخ:** 2026-01-02
- **تصمیم‌گیرندگان:** تیم فنی (Backend)

## زمینه (Context)

پلتفرم نیازمند یک API امن، توسعه‌پذیر و قابل نگهداری است که بتواند:

- نقش‌ها و دسترسی‌های پیچیده (Buyer/Seller/Service Providers/Admin) را مدیریت کند.
- گردش‌کار سفارش‌ها و پرداخت‌های مرحله‌ای را با یکپارچگی داده بالا اجرا کند.
- توسعه سریع MVP را ممکن کند، اما در عین حال به رشد آینده هم پاسخ دهد.

تیم Backend از پایتون استفاده می‌کند و تجربه عملی با Django دارد.

## تصمیم (Decision)

برای Backend، **Django + Django REST Framework (DRF)** به‌عنوان فریم‌ورک اصلی انتخاب می‌شود.

- پایگاه‌داده اصلی: **PostgreSQL**
- کش/بروکر: **Redis**
- پردازش‌های غیرهمزمان و زمان‌بندی: **Celery + Celery Beat**

## دلایل (Rationale)

- DRF اکوسیستم بالغ برای:
  - Serializer/Validation
  - Auth/JWT integration
  - Permission و Object-level permission
  - Pagination/Filtering
- Django ORM و Transaction Management برای سناریوهای مالی و state transitions مناسب است.
- سرعت توسعه برای MVP بالاست و جذب نیرو آسان‌تر است.

## پیامدها (Consequences)

### مثبت
- کاهش زمان توسعه MVP
- اکوسیستم کامل برای امنیت، مدیریت کاربران، admin panel
- سازگاری خوب با معماری مونولیت ماژولار

### منفی / ریسک‌ها
- اگر منطق دامنه داخل View/Serializer پخش شود، بدهی فنی بالا می‌رود.
  - **راه‌حل:** اعمال Service Layer و الگوی use-case.
- مقیاس‌پذیری در حد «یک سرویس بزرگ» است؛ برای رشد زیاد ممکن است نیاز به جداسازی ماژول‌ها باشد.
  - **راه‌حل:** مرزبندی appها و قرارداد داخلی.

## گزینه‌های بررسی‌شده (Alternatives)

- FastAPI + SQLAlchemy: سریع و سبک، اما تیم تجربه کمتر و admin tooling محدودتر
- Node.js/NestJS: مناسب، اما با stack انتخابی تیم هم‌راستا نیست
- Microservices از ابتدا: پیچیدگی عملیاتی بالا، مناسب MVP نیست

## ارجاع‌ها (Links)

- سند معماری: `docs/architecture/architecture.md`
