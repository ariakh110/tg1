"""سرویسِ ورودِ سرنخ (lead intake) برای CRM.

نقطهٔ یگانه برای «ساختن/به‌روزرسانیِ یک مشتری از روی یک رویداد» (ثبت‌نام، خرید، چت).
شمارهٔ موبایلِ نرمال‌شده کلیدِ یکتاست؛ اگر مشتری از قبل باشد، فقط فیلدهای خالی پر می‌شوند
(نام/شرکت/شهر/کاربر) و مرحله/منبعِ موجود دست‌نخورده می‌ماند تا تاریخچهٔ قیف خراب نشود.
"""
import re

from .models import Customer, CustomerActivity


def normalize_phone(raw):
    """نرمال‌سازیِ شمارهٔ ایران به شکلِ 09XXXXXXXXX (همان منطقِ سرویسِ پیام‌رسانی)."""
    digits = re.sub(r"\D", "", str(raw or ""))
    if digits.startswith("0098"):
        digits = digits[4:]
    elif digits.startswith("98") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    return digits


def upsert_lead(
    phone,
    *,
    name="",
    company="",
    city="",
    note="",
    source=Customer.SOURCE_OTHER,
    user=None,
    created_by=None,
    activity_body="",
):
    """مشتری را بر اساسِ شماره می‌سازد یا به‌روزرسانی می‌کند و (در صورتِ متن) یک یادداشت روی تایم‌لاین ثبت می‌کند.

    خروجی: tuple ``(customer, created)``؛ اگر شماره نامعتبر باشد ``(None, False)``.
    منبع/مرحلهٔ یک مشتریِ موجود هرگز بازنویسی نمی‌شود؛ فقط فیلدهای خالی تکمیل می‌شوند.
    """
    normalized = normalize_phone(phone)
    if not normalized or len(normalized) < 10:
        return None, False

    name = (name or "").strip()[:160]
    company = (company or "").strip()[:200]
    city = (city or "").strip()[:100]

    customer, created = Customer.objects.get_or_create(
        phone=normalized,
        defaults={
            "name": name or "مشتری جدید",
            "company": company,
            "city": city,
            "note": (note or "").strip(),
            "source": source,
            "stage": Customer.STAGE_NEW,
            "user": user,
            "created_by": created_by if getattr(created_by, "is_authenticated", False) else None,
        },
    )

    if not created:
        # فقط جاهای خالی را پر کن؛ چیزی را که ادمین قبلاً تنظیم کرده دست نزن.
        dirty = []
        if name and (not customer.name or customer.name == "مشتری جدید"):
            customer.name = name
            dirty.append("name")
        if company and not customer.company:
            customer.company = company
            dirty.append("company")
        if city and not customer.city:
            customer.city = city
            dirty.append("city")
        if user and not customer.user_id:
            customer.user = user
            dirty.append("user")
        if dirty:
            customer.save(update_fields=dirty + ["updated_at"])

    if activity_body:
        CustomerActivity.objects.create(
            customer=customer,
            kind=CustomerActivity.KIND_NOTE,
            body=activity_body[:2000],
            created_by=created_by if getattr(created_by, "is_authenticated", False) else None,
        )

    return customer, created
