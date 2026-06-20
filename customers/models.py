from django.conf import settings
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone


class Customer(models.Model):
    """مشتریِ CRM — عمدتاً مشتریِ تلفنی/حضوریِ فروشِ فولاد.

    جدا از کاربرِ سایت است (که ممکن است اصلاً حساب نداشته باشد)، ولی در صورت وجود
    می‌توان به یک کاربرِ سایت لینکش کرد. شمارهٔ موبایل کلیدِ یکتاست تا بعداً تماسِ
    ورودی به همین مشتری وصل شود.
    """

    # مراحلِ قیفِ فروشِ B2B (به‌ترتیبِ پیشروی)
    STAGE_NEW = "new"
    STAGE_NURTURING = "nurturing"
    STAGE_PROPOSAL = "proposal"
    STAGE_NEGOTIATION = "negotiation"
    STAGE_WON = "won"
    STAGE_LOYAL = "loyal"
    STAGE_LOST = "lost"
    STAGE_CHOICES = [
        (STAGE_NEW, "سرنخ"),
        (STAGE_NURTURING, "پرورش/اعتمادسازی"),
        (STAGE_PROPOSAL, "پیش‌فاکتور"),
        (STAGE_NEGOTIATION, "مذاکره/قرارداد"),
        (STAGE_WON, "مشتری فعال"),
        (STAGE_LOYAL, "وفادار"),
        (STAGE_LOST, "ازدست‌رفته"),
    ]
    # مراحلی که «بسته‌شدهٔ موفق» محسوب می‌شوند (برای نرخ تبدیل/CLV)
    STAGE_CLOSED_WON = (STAGE_WON, STAGE_LOYAL)

    SOURCE_INCOMING_CALL = "incoming_call"
    SOURCE_REFERRAL = "referral"
    SOURCE_WEBSITE = "website"
    SOURCE_INSTAGRAM = "instagram"
    SOURCE_WALK_IN = "walk_in"
    SOURCE_ASSISTANT = "assistant"
    SOURCE_LINKEDIN = "linkedin"
    SOURCE_EXHIBITION = "exhibition"
    SOURCE_ASSOCIATION = "association"
    SOURCE_B2B_PLATFORM = "b2b_platform"
    SOURCE_COLD_CALL = "cold_call"
    SOURCE_FIELD_SALES = "field_sales"
    SOURCE_OTHER = "other"
    SOURCE_CHOICES = [
        (SOURCE_INCOMING_CALL, "تماس ورودی"),
        (SOURCE_REFERRAL, "معرفی"),
        (SOURCE_WEBSITE, "سایت"),
        (SOURCE_INSTAGRAM, "اینستاگرام"),
        (SOURCE_WALK_IN, "مراجعه حضوری"),
        (SOURCE_ASSISTANT, "دستیار"),
        (SOURCE_LINKEDIN, "لینکدین"),
        (SOURCE_EXHIBITION, "نمایشگاه"),
        (SOURCE_ASSOCIATION, "انجمن/سندیکا"),
        (SOURCE_B2B_PLATFORM, "پلتفرم B2B"),
        (SOURCE_COLD_CALL, "تماس سرد"),
        (SOURCE_FIELD_SALES, "بازاریابی میدانی"),
        (SOURCE_OTHER, "سایر"),
    ]

    name = models.CharField(max_length=160, verbose_name="نام")
    phone = models.CharField(max_length=32, unique=True, db_index=True, verbose_name="موبایل")
    company = models.CharField(max_length=200, blank=True, default="", verbose_name="شرکت")
    city = models.CharField(max_length=100, blank=True, default="", verbose_name="شهر")
    province = models.CharField(max_length=100, blank=True, default="", verbose_name="استان")
    note = models.TextField(blank=True, default="", verbose_name="یادداشت")
    extra_phones = models.JSONField(default=list, blank=True, verbose_name="شماره‌های دیگر")
    stage = models.CharField(
        max_length=12,
        choices=STAGE_CHOICES,
        default=STAGE_NEW,
        db_index=True,
        verbose_name="مرحله",
    )
    source = models.CharField(
        max_length=16,
        choices=SOURCE_CHOICES,
        default=SOURCE_OTHER,
        db_index=True,
        verbose_name="منبع",
    )

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


class CustomerActivity(models.Model):
    """یک تعاملِ ثبت‌شده با مشتری (تماس/پیام/جلسه/یادداشت) که می‌تواند یک پیگیریِ آینده هم زمان‌بندی کند.

    هر ردیف هم «چه اتفاقی افتاد» را نگه می‌دارد و هم می‌تواند «قدمِ بعدی کِی است» را. پیگیریِ باز
    یعنی `follow_up_at` پر است و `follow_up_done` هنوز False؛ داشبوردِ روزانه روی همین کوئری می‌نشیند.
    """

    KIND_CALL = "call"
    KIND_MESSAGE = "message"
    KIND_MEETING = "meeting"
    KIND_NOTE = "note"
    KIND_STAGE = "stage"
    KIND_CHOICES = [
        (KIND_CALL, "تماس"),
        (KIND_MESSAGE, "پیام"),
        (KIND_MEETING, "جلسه"),
        (KIND_NOTE, "یادداشت"),
        (KIND_STAGE, "تغییر مرحله"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="activities",
        verbose_name="مشتری",
    )
    kind = models.CharField(
        max_length=10,
        choices=KIND_CHOICES,
        default=KIND_CALL,
        db_index=True,
        verbose_name="نوع",
    )
    body = models.TextField(
        blank=True,
        default="",
        verbose_name="شرح",
        help_text="چه گفته شد / نتیجه چه بود.",
    )
    occurred_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name="زمان تعامل",
    )

    # پیگیریِ آینده (اختیاری) روی همین ردیف
    follow_up_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="پیگیری بعدی",
        help_text="تاریخِ قدمِ بعدی؛ خالی یعنی پیگیری‌ای زمان‌بندی نشده.",
    )
    follow_up_note = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="شرحِ پیگیری",
        help_text="مثلاً «دوباره زنگ بزن و قیمت نهایی را بده».",
    )
    follow_up_done = models.BooleanField(default=False, db_index=True, verbose_name="پیگیری انجام شد")
    follow_up_done_at = models.DateTimeField(null=True, blank=True, verbose_name="زمان انجام پیگیری")

    # فقط برای نوعِ «تغییر مرحله» پر می‌شوند (تاریخچهٔ قیف برای KPI)
    stage_from = models.CharField(max_length=12, blank=True, default="", verbose_name="مرحلهٔ قبلی")
    stage_to = models.CharField(max_length=12, blank=True, default="", db_index=True, verbose_name="مرحلهٔ جدید")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]
        verbose_name = "فعالیت مشتری"
        verbose_name_plural = "فعالیت‌های مشتری"
        indexes = [
            models.Index(fields=["customer", "occurred_at"]),
            models.Index(fields=["follow_up_done", "follow_up_at"]),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} - {self.customer.name}"

    @property
    def has_open_follow_up(self):
        return bool(self.follow_up_at) and not self.follow_up_done
