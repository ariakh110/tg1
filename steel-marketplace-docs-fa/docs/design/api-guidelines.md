# راهنمای طراحی API (REST) برای پلتفرم بازارگاه آهن‌آلات

این سند استانداردهای طراحی API را برای Backend (DRF) مشخص می‌کند تا قرارداد بین Backend و Frontend شفاف و پایدار باشد.

---

## 1) اصول کلی

- API **Resource-oriented** باشد (orders, offers, payments, warehouses, ...).
- endpointها **قابل حدس** و **یکنواخت** باشند.
- قرارداد پاسخ/خطا **یکسان** در کل سیستم.
- نسخه‌بندی از ابتدا: `/api/v1/...`

---

## 2) نام‌گذاری و ساختار مسیرها

### 2.1) قواعد

- همه مسیرها **plural**:
  - ✅ `/orders`
  - ❌ `/order`
- از kebab-case در URL استفاده نکنید؛ پیشنهاد: **kebab یا snake**؟  
  در DRF معمولاً snake_case در query و JSON و URL ساده است، اما استاندارد رایج URL: kebab-case.  
  برای هماهنگی با DRF و کاهش friction، پیشنهاد: **snake_case** در query params و JSON، و **plural nouns** در path.

### 2.2) نمونه‌ها

- `/api/v1/orders`
- `/api/v1/orders/{order_id}`
- `/api/v1/orders/{order_id}/offers`
- `/api/v1/offers/{offer_id}/accept`
- `/api/v1/orders/{order_id}/payments`

> اکشن‌های دامنه (مثل accept/confirm) بهتر است به صورت زیر باشند:
> - `POST /offers/{id}/accept`
> - `POST /orders/{id}/confirm-inventory`
> - `POST /orders/{id}/confirm-delivery`

---

## 3) مدل‌سازی منابع (Resource Modeling)

### 3.1) Order

Order یک منبع مرکزی است و فیلد `type` مشخص می‌کند که BUY/SELL/CUT/SHIP/QC/COMBO است.

- BUY: مشخصات کالا + مقصد + زمان
- SELL: اعلام فروش/بار توسط فروشنده + انتخاب خریدار
- CUT: مشخصات برش + فایل نقشه
- SHIP: مبدا/مقصد + وزن/حجم + زمان
- QC: محل بازرسی + معیارها
- COMBO: کانتینر + child orders

### 3.2) Offer

Offer به یک Order وصل است. در BUY فقط خریدار همه offers را می‌بیند و در SELL فقط فروشنده.
سایر نقش‌ها فقط offer خودشان را می‌بینند.

### 3.3) Payment

Payment به یک Order وصل است و نوع پرداخت را مشخص می‌کند (DEPOSIT/INSTALLMENT/FINAL).

---

## 4) فیلتر، مرتب‌سازی و Pagination

### 4.1) Pagination

- همه list endpointها باید pagination داشته باشند.
- فرمت پیشنهادی:

```json
{
  "count": 123,
  "next": "https://.../api/v1/orders?page=3",
  "previous": "https://.../api/v1/orders?page=1",
  "results": [ ... ]
}
```

### 4.2) Filtering

- query params استاندارد:
  - `type=BUY`
  - `type=SELL`
  - `status=OPEN`
  - `city=tehran`
  - `created_from=2026-01-01`
  - `created_to=2026-01-31`

### 4.3) Sorting

- `ordering=created_at` یا `ordering=-created_at`
- فقط روی فیلدهای whitelist شده اجازه دهید.

---

## 5) Authentication و Authorization

### 5.1) Auth

- JWT Bearer:
  - `Authorization: Bearer <token>`

### 5.2) RBAC

- Role-based permissions:
  - Seller: پیشنهاد روی BUYها + مدیریت سفارش‌های SELL خودش
  - Buyer: سفارش‌های خودش + مشاهده SELLها و ارسال پیشنهاد خرید
  - Admin دسترسی کامل
- Object-level:
  - Order details فقط برای participantها

---

## 6) Error Responses

### 6.1) قالب خطا

```json
{
  "error": {
    "code": "PAYMENT_INVALID_STATE",
    "message": "پرداخت در وضعیت فعلی قابل انجام نیست.",
    "details": {
      "order_id": "…",
      "status": "OPEN"
    }
  }
}
```

### 6.2) Validation Errors

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "ورودی نامعتبر است.",
    "details": {
      "quantity": ["این فیلد الزامی است."]
    }
  }
}
```

---

## 7) Status Transitions و اکشن‌ها

- به جای PATCH مستقیم روی `status` (که می‌تواند سوءاستفاده شود)، بهتر است از اکشن‌های دامنه استفاده شود:
  - `POST /offers/{id}/accept`
  - `POST /orders/{id}/confirm-inventory`
  - `POST /orders/{id}/mark-ready-for-loading`
  - `POST /orders/{id}/final-weight`
  - `POST /orders/{id}/confirm-delivery`

این کار:
- امنیت را بالا می‌برد (role + precondition)
- side effectها را استاندارد می‌کند (log/notification/payment checks)

---

## 8) Idempotency

- برای endpointهای مهم (ایجاد پرداخت، callback پرداخت) header `Idempotency-Key` را پشتیبانی کنید.
- اگر یک درخواست با همان کلید قبلاً موفق ثبت شده، همان نتیجه برگردانده شود.

---

## 9) File Uploads

- برای نقشه برش و گزارش QC:
  - endpoint برای دریافت `upload_url` (pre-signed) پیشنهاد می‌شود.
  - یا upload مستقیم multipart با محدودیت سایز.

---

## 10) Rate Limiting

- login/OTP: سخت‌گیرانه
- create order/offer: متوسط
- list endpoints: cache + محدودیت منطقی

---

## 11) Webhooks (اختیاری)

- پرداخت: gateway callback/webhook
- در آینده: webhook برای مشتریان سازمانی (مثلاً اطلاع از تغییر وضعیت سفارش)
