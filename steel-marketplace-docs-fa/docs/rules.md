# قوانین مهندسی و استانداردهای توسعه (Backend)

این سند برای توسعه‌دهندگان Backend (Django / DRF) نوشته شده است تا کیفیت، امنیت و نگهداری‌پذیری سیستم تضمین شود.

---

## 1) اصول کلی

1. **منطق دامنه را در View/Serializer نریزید.** View فقط هماهنگ‌کننده باشد؛ منطق business در Service Layer.
2. **هر عملیات حساس مالی یا تغییر وضعیت سفارش باید اتمیک باشد** (`transaction.atomic`).
3. **Idempotency** برای endpointهای callback/webhook الزامی است.
4. **امنیت پیش‌فرض است**: حداقل دسترسی، عدم نشت اطلاعات، لاگ قابل ممیزی.

---

## 2) استاندارد کدنویسی Python

### 2.1) فرمت و کیفیت کد

- `black` برای فرمت
- `isort` برای مرتب‌سازی import
- `flake8` یا `ruff` برای lint
- پیشنهاد: `mypy` برای تایپ‌چک در لایه سرویس‌ها (اختیاری اما مفید)

### 2.2) Naming

- کلاس‌ها: `PascalCase`
- توابع/متدها/متغیرها: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- فایل‌ها و پوشه‌ها: `snake_case`

### 2.3) ساختار پوشه‌ها (پیشنهادی)

```
backend/
  apps/
    orders/
      api/ (views, serializers, urls)
      services/ (use-cases)
      models.py
      selectors.py (query functions)
      domain.py (domain helpers)
      tests/
```

> الگو: **Services + Selectors**  
> - Selectors: فقط query و read-model  
> - Services: write/use-case + transaction + side effects

---

## 3) استانداردهای DRF

### 3.1) ViewSet vs APIView

- برای منابع CRUD و فهرست: `ModelViewSet`
- برای اکشن‌های دامنه (accept-offer, confirm-inventory): `@action` روی ViewSet یا APIView اختصاصی
- اکشن‌های دامنه نباید CRUD را مخلوط کنند.

### 3.2) Serializer

- Serializer باید:
  - validate سطح ورودی را انجام دهد
  - mapping به DTO/service payload را انجام دهد
- **نباید** انتقال وضعیت یا عملیات مالی را انجام دهد.

### 3.3) Permission

- از Permission کلاس‌های DRF استفاده کنید.
- Object-level permission اجباری است:
  - فقط خریدار و مجری انتخاب‌شده و admin باید جزئیات سفارش را ببینند.
  - فروشندگان نباید پیشنهادهای رقیب را ببینند.
- Policy پیشنهادی:
  - `IsAuthenticated`
  - `HasRole(Seller/Buyer/...)`
  - `IsOrderParticipant` (buyer یا assigned_provider یا admin)

### 3.4) Pagination / Filtering

- pagination پیش‌فرض برای list endpointها
- فیلترهای استاندارد:
  - `type`, `status`, `city`, `date_from`, `date_to`
- sorting با `ordering` و whitelist

---

## 4) خطاها و پاسخ‌ها (Error Handling)

### 4.1) فرمت خطا (پیشنهادی)

- از سبک RFC7807 (Problem Details) یا فرمت استاندارد زیر استفاده کنید:

```json
{
  "error": {
    "code": "ORDER_INVALID_STATUS",
    "message": "این انتقال وضعیت مجاز نیست.",
    "details": { "current_status": "OPEN", "event": "confirm_inventory" }
  }
}
```

### 4.2) کدهای وضعیت HTTP

- 200/201: موفق
- 400: خطای اعتبارسنجی
- 401: بدون احراز هویت
- 403: عدم مجوز
- 404: پیدا نشد
- 409: تضاد (مثلاً وضعیت نامعتبر یا race condition)
- 422: ورودی معتبر نیست برای این عملیات (اختیاری)
- 500: خطای داخلی

---

## 5) تراکنش‌ها و یکپارچگی داده

### 5.1) Transaction Boundaries

در سرویس‌ها:

- انتخاب پیشنهاد (accept offer)
- ثبت پرداخت موفق
- آزادسازی وجه (payout)
- تغییر وضعیت‌های کلیدی (ready/loading/delivered)
- لغو سفارش با refund

همه باید در `transaction.atomic` باشند.

### 5.2) Concurrency

- برای جلوگیری از انتخاب همزمان دو پیشنهاد:
  - از `select_for_update()` روی Order استفاده کنید
  - یا constraint سطح DB برای یک `chosen_offer`

### 5.3) Idempotency

- callback پرداخت ممکن است چند بار ارسال شود.
- برای پردازش:
  - از `gateway_ref` به عنوان کلید یکتا استفاده کنید
  - اگر قبلاً پردازش شده، همان نتیجه را برگردانید

---

## 6) تست (Testing Strategy)

### 6.1) سطح تست‌ها

- Unit test برای سرویس‌ها (use-caseها)
- API test برای endpointهای حیاتی
- Integration test برای سناریوهای پرداخت و تغییر وضعیت

### 6.2) سناریوهای بحرانی که باید تست شوند

- BUY RFQ → Offer → Accept → Deposit Paid → Confirm Inventory
- SELL Listing → Offer → Accept → Deposit Paid → Confirm Inventory
- Installments + timeout
- Final weight adjustment
- SHIP order acceptance و delivery confirm
- QC report submission
- Cancel with refund rules
- Permission: seller cannot see competitor offers

---

## 7) امنیت

### 7.1) احراز هویت

- JWT (Access + Refresh)
- نرخ محدودسازی برای login/OTP
- سیاست قفل موقت در صورت تلاش‌های زیاد

### 7.2) محافظت داده

- داده‌های حساس (KYC docs) در object storage با URL امضا شده
- عدم ذخیره اطلاعات کارت بانکی
- logها نباید شامل token یا اطلاعات بانکی باشند

### 7.3) KYC

- نقش‌های Seller/Cutter/Driver/QC فقط پس از تأیید admin فعال شوند.
- مجوز دیدن سفارش‌ها برای این نقش‌ها منوط به verified بودن است.

---

## 8) لاگ و مانیتورینگ

- log ساخت‌یافته (JSON)
- هر تغییر وضعیت Order یک `OrderStatusHistory` بسازد.
- هر payout/refund یک رکورد ledger بسازد.
- خطاهای production به Sentry (یا مشابه) ارسال شود.

---

## 9) استانداردهای Git / PR

### 9.1) Branching

- `main` پایدار
- `develop` (اختیاری)
- feature branches: `feat/<topic>`
- bugfix branches: `fix/<topic>`

### 9.2) Commit message

الگوی پیشنهادی:

- `feat: add offer acceptance flow`
- `fix: prevent double payment callback`
- `refactor: move order transitions to service layer`

### 9.3) Code Review Checklist

- [ ] آیا منطق دامنه در service layer است؟
- [ ] آیا permissionها درست اعمال شده؟
- [ ] آیا عملیات مالی اتمیک است؟
- [ ] آیا endpoint idempotent است؟
- [ ] آیا تست برای مسیرهای بحرانی اضافه شده؟
- [ ] آیا migration و indexها درست هستند؟
- [ ] آیا لاگ‌های حساس نشت ندارند؟

---

## 10) API Versioning

- مسیرها با نسخه: `/api/v1/...`
- تغییرات breaking در نسخه جدید (v2)
- برای تغییرات جزئی از feature flags و backward-compatible fields استفاده شود.
