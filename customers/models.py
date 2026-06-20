from django.conf import settings
from django.db import models
from django.db.models import Q, Sum


class Customer(models.Model):
    """مشتریِ CRM — عمدتاً مشتریِ تلفنی/حضوریِ فروشِ فولاد.

    جدا از کاربرِ سایت است (که ممکن است اصلاً حساب نداشته باشد)، ولی در صورت وجود
    می‌توان به یک کاربرِ سایت لینکش کرد. شمارهٔ موبایل کلیدِ یکتاست تا بعداً تماسِ
    ورودی به همین مشتری وصل شود.
    """

    name = models.CharField(max_length=160, verbose_name="نام")
    phone = models.CharField(max_length=32, unique=True, db_index=True, verbose_name="موبایل")
    company = models.CharField(max_length=200, blank=True, default="", verbose_name="شرکت")
    city = models.CharField(max_length=100, blank=True, default="", verbose_name="شهر")
    province = models.CharField(max_length=100, blank=True, default="", verbose_name="استان")
    note = models.TextField(blank=True, default="", verbose_name="یادداشت")
    extra_phones = models.JSONField(default=list, blank=True, verbose_name="شماره‌های دیگر")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crm_customer",
        verbose_name="کاربر سایت (اختیاری)",
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "مشتری"
        verbose_name_plural = "مشتریان"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["company"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.phone})"

    @property
    def balance(self):
        """مانده (بدهی) به تومان = جمعِ خریدها − جمعِ پرداخت‌ها + جمعِ تعدیل‌ها.

        مثبت یعنی مشتری به ما بدهکار است.
        """
        agg = self.transactions.aggregate(
            purchase=Sum("amount", filter=Q(kind=CustomerTransaction.KIND_PURCHASE)),
            payment=Sum("amount", filter=Q(kind=CustomerTransaction.KIND_PAYMENT)),
            adjustment=Sum("amount", filter=Q(kind=CustomerTransaction.KIND_ADJUSTMENT)),
        )
        purchase = agg["purchase"] or 0
        payment = agg["payment"] or 0
        adjustment = agg["adjustment"] or 0
        return purchase - payment + adjustment


class CustomerTransaction(models.Model):
    """دفترِ حساب مشتری: خرید (بدهکار)، پرداخت (بستانکار)، یا تعدیل/مانده اولیه."""

    KIND_PURCHASE = "purchase"
    KIND_PAYMENT = "payment"
    KIND_ADJUSTMENT = "adjustment"
    KIND_CHOICES = [
        (KIND_PURCHASE, "خرید"),
        (KIND_PAYMENT, "پرداخت"),
        (KIND_ADJUSTMENT, "تعدیل/مانده اولیه"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="مشتری",
    )
    kind = models.CharField(
        max_length=12,
        choices=KIND_CHOICES,
        default=KIND_PURCHASE,
        db_index=True,
        verbose_name="نوع",
    )
    amount = models.BigIntegerField(
        verbose_name="مبلغ (تومان)",
        help_text="برای خرید/پرداخت مثبت؛ تعدیل می‌تواند منفی باشد.",
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="شرح",
        help_text="مثلاً «۲۰ تن میلگرد ۱۴ ذوب».",
    )
    occurred_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="تاریخ واقعی",
        help_text="تاریخِ واقعیِ خرید/پرداخت؛ خالی یعنی همین حالا.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        verbose_name = "تراکنش مشتری"
        verbose_name_plural = "تراکنش‌های مشتری"
        indexes = [
            models.Index(fields=["customer", "kind"]),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.amount:,} - {self.customer.name}"
