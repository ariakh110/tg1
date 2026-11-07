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
    SOURCE_STORE_PURCHASE = "store_purchase"
    SOURCE_CHAT = "chat"
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
        (SOURCE_WEBSITE, "ثبت‌نام سایت"),
        (SOURCE_STORE_PURCHASE, "خرید از سایت"),
        (SOURCE_CHAT, "چت فروش"),
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
    product_interests = models.ManyToManyField(
        "products.ProductCategory",
        blank=True,
        related_name="crm_consumers",
        verbose_name="دسته‌های محصول مصرفی",
    )
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
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="ثبت‌کننده",
        help_text="کاربری که این مشتری را ثبت کرده؛ خالی یعنی به‌صورتِ خودکار (سیستم) ساخته شده.",
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
    opportunity = models.ForeignKey(
        "CrmOpportunity",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activities",
        verbose_name="فرصت فروش",
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
    direction = models.CharField(
        max_length=10,
        choices=[("inbound", "دریافتی"), ("outbound", "ارسالی"), ("internal", "داخلی")],
        default="internal",
        db_index=True,
        verbose_name="جهت تعامل",
    )
    result = models.CharField(max_length=120, blank=True, default="", verbose_name="نتیجه")
    external_message_key = models.CharField(
        max_length=180,
        blank=True,
        default="",
        db_index=True,
        verbose_name="شناسه پیام بیرونی",
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


class CrmOpportunity(models.Model):
    """A sales need/deal tracked independently from the customer's lifecycle stage."""

    STAGE_NEW_INQUIRY = "new_inquiry"
    STAGE_QUALIFIED = "qualified"
    STAGE_PRICING = "pricing"
    STAGE_QUOTE_SENT = "quote_sent"
    STAGE_PAYMENT_PENDING = "payment_pending"
    STAGE_FULFILLMENT = "fulfillment"
    STAGE_WON = "won"
    STAGE_LOST = "lost"
    STAGE_CHOICES = [
        (STAGE_NEW_INQUIRY, "استعلام جدید"),
        (STAGE_QUALIFIED, "نیاز تکمیل‌شده"),
        (STAGE_PRICING, "قیمت‌گذاری و موجودی"),
        (STAGE_QUOTE_SENT, "پیشنهاد ارسال‌شده"),
        (STAGE_PAYMENT_PENDING, "در انتظار پرداخت"),
        (STAGE_FULFILLMENT, "اجرا، بارگیری و حمل"),
        (STAGE_WON, "فروش موفق"),
        (STAGE_LOST, "ازدست‌رفته"),
    ]
    OPEN_STAGES = (
        STAGE_NEW_INQUIRY,
        STAGE_QUALIFIED,
        STAGE_PRICING,
        STAGE_QUOTE_SENT,
        STAGE_PAYMENT_PENDING,
        STAGE_FULFILLMENT,
    )
    CLOSED_STAGES = (STAGE_WON, STAGE_LOST)
    DEFAULT_PROBABILITY = {
        STAGE_NEW_INQUIRY: 10,
        STAGE_QUALIFIED: 25,
        STAGE_PRICING: 40,
        STAGE_QUOTE_SENT: 55,
        STAGE_PAYMENT_PENDING: 75,
        STAGE_FULFILLMENT: 90,
        STAGE_WON: 100,
        STAGE_LOST: 0,
    }

    SOURCE_MANUAL = "manual"
    SOURCE_ASSISTANT_INQUIRY = "assistant_inquiry"
    SOURCE_STORE_ORDER = "store_order"
    SOURCE_BALE = "bale"
    SOURCE_CHOICES = [
        (SOURCE_MANUAL, "ثبت دستی"),
        (SOURCE_ASSISTANT_INQUIRY, "استعلام دستیار سایت"),
        (SOURCE_STORE_ORDER, "سفارش مستقیم سایت"),
        (SOURCE_BALE, "ربات بله"),
    ]

    customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="opportunities",
        verbose_name="مشتری",
    )
    title = models.CharField(max_length=240, verbose_name="عنوان فرصت")
    stage = models.CharField(
        max_length=24,
        choices=STAGE_CHOICES,
        default=STAGE_NEW_INQUIRY,
        db_index=True,
        verbose_name="مرحله فرصت",
    )
    source_type = models.CharField(
        max_length=24,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
        db_index=True,
        verbose_name="منبع فرصت",
    )
    source_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        verbose_name="شناسه رکورد منبع",
    )
    source_status = models.CharField(max_length=32, blank=True, default="", verbose_name="وضعیت منبع")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crm_owned_opportunities",
        verbose_name="مسئول فروش",
    )
    expected_value_irr = models.BigIntegerField(default=0, verbose_name="ارزش مورد انتظار (ریال)")
    probability = models.PositiveSmallIntegerField(default=10, verbose_name="احتمال موفقیت")
    need_details = models.TextField(blank=True, default="", verbose_name="شرح نیاز")
    next_action = models.CharField(max_length=255, blank=True, default="", verbose_name="اقدام بعدی")
    next_follow_up_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="پیگیری بعدی")
    lost_reason = models.CharField(max_length=255, blank=True, default="", verbose_name="دلیل شکست")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="اطلاعات منبع")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crm_created_opportunities",
        verbose_name="ثبت‌کننده",
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name="فعال")
    closed_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="زمان بسته‌شدن")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        verbose_name = "فرصت فروش"
        verbose_name_plural = "فرصت‌های فروش"
        indexes = [
            models.Index(fields=["source_type", "source_id"]),
            models.Index(fields=["stage", "updated_at"]),
            models.Index(fields=["owner", "stage"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "source_id"],
                condition=~Q(source_id=""),
                name="customers_unique_opportunity_source",
            ),
            models.CheckConstraint(
                check=Q(probability__gte=0, probability__lte=100),
                name="customers_opportunity_probability_0_100",
            ),
        ]

    def __str__(self):
        return f"{self.title} - {self.get_stage_display()}"


class CrmFollowUp(models.Model):
    """A durable, assignable customer follow-up, optionally linked to its timeline activity."""

    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "در انتظار"),
        (STATUS_COMPLETED, "انجام‌شده"),
        (STATUS_CANCELLED, "لغوشده"),
    ]
    CHANNEL_CALL = "call"
    CHANNEL_SMS = "sms"
    CHANNEL_BALE = "bale"
    CHANNEL_MEETING = "meeting"
    CHANNEL_OTHER = "other"
    CHANNEL_CHOICES = [
        (CHANNEL_CALL, "تماس"),
        (CHANNEL_SMS, "پیامک"),
        (CHANNEL_BALE, "بله"),
        (CHANNEL_MEETING, "جلسه"),
        (CHANNEL_OTHER, "سایر"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="crm_follow_ups")
    opportunity = models.ForeignKey(
        CrmOpportunity, null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_follow_ups"
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_follow_ups"
    )
    source_activity = models.OneToOneField(
        CustomerActivity,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crm_follow_up",
    )
    title = models.CharField(max_length=255, blank=True, default="", verbose_name="اقدام بعدی")
    channel = models.CharField(max_length=12, choices=CHANNEL_CHOICES, default=CHANNEL_CALL)
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    result = models.TextField(blank=True, default="")
    reminder_metadata = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=180, unique=True, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_at", "created_at", "id"]
        indexes = [models.Index(fields=["status", "due_at"]), models.Index(fields=["owner", "status", "due_at"])]
        verbose_name = "پیگیری CRM"
        verbose_name_plural = "پیگیری‌های CRM"


class CrmTask(models.Model):
    """Internal CRM work. Tasks never send an external message."""

    STATUS_OPEN = "open"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_OPEN, "باز"),
        (STATUS_COMPLETED, "انجام‌شده"),
        (STATUS_CANCELLED, "لغوشده"),
    ]

    customer = models.ForeignKey(
        Customer, null=True, blank=True, on_delete=models.CASCADE, related_name="crm_tasks"
    )
    opportunity = models.ForeignKey(
        CrmOpportunity, null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_tasks"
    )
    source_order_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_tasks"
    )
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True, default="")
    trigger = models.CharField(max_length=40, blank=True, default="", db_index=True)
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)
    result = models.TextField(blank=True, default="")
    idempotency_key = models.CharField(max_length=180, unique=True, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["due_at", "created_at", "id"]
        indexes = [models.Index(fields=["status", "due_at"]), models.Index(fields=["owner", "status", "due_at"])]
        verbose_name = "کار CRM"
        verbose_name_plural = "کارهای CRM"


class CrmAutomationRun(models.Model):
    """Durable audit and retry record for the small CRM automation whitelist."""

    TRIGGER_CUSTOMER_CREATED = "customer.created"
    TRIGGER_OPPORTUNITY_STAGE_CHANGED = "opportunity.stage_changed"
    TRIGGER_CHOICES = [
        (TRIGGER_CUSTOMER_CREATED, "سرنخ جدید"),
        (TRIGGER_OPPORTUNITY_STAGE_CHANGED, "تغییر مرحله فرصت"),
    ]
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "در انتظار"),
        (STATUS_PROCESSING, "در حال اجرا"),
        (STATUS_SUCCEEDED, "انجام‌شده"),
        (STATUS_FAILED, "ناموفق"),
    ]

    event_key = models.CharField(max_length=180, unique=True)
    trigger = models.CharField(max_length=40, choices=TRIGGER_CHOICES, db_index=True)
    customer = models.ForeignKey(
        Customer, null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_automation_runs"
    )
    opportunity = models.ForeignKey(
        CrmOpportunity, null=True, blank=True, on_delete=models.SET_NULL, related_name="crm_automation_runs"
    )
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status", "updated_at"])]
        verbose_name = "اجرای اتوماسیون CRM"
        verbose_name_plural = "اجراهای اتوماسیون CRM"


class CrmContactChannel(models.Model):
    """Per-customer channel consent. Unknown or revoked consent never authorizes outbound messaging."""

    CHANNEL_SMS = "sms"
    CHANNEL_BALE = "bale"
    CHANNEL_CHOICES = [(CHANNEL_SMS, "پیامک"), (CHANNEL_BALE, "بله")]
    CONSENT_UNKNOWN = "unknown"
    CONSENT_GRANTED = "granted"
    CONSENT_REVOKED = "revoked"
    CONSENT_CHOICES = [
        (CONSENT_UNKNOWN, "نامشخص"),
        (CONSENT_GRANTED, "مجاز"),
        (CONSENT_REVOKED, "لغوشده"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="contact_channels")
    channel = models.CharField(max_length=8, choices=CHANNEL_CHOICES)
    consent = models.CharField(max_length=8, choices=CONSENT_CHOICES, default=CONSENT_UNKNOWN, db_index=True)
    source = models.CharField(max_length=80, blank=True, default="manual")
    consented_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["channel", "id"]
        constraints = [
            models.UniqueConstraint(fields=["customer", "channel"], name="customers_unique_contact_channel")
        ]
        indexes = [models.Index(fields=["channel", "consent"])]
        verbose_name = "رضایت کانال ارتباطی"
        verbose_name_plural = "رضایت کانال‌های ارتباطی"


class CrmOpportunityStageHistory(models.Model):
    """Idempotent audit trail for automatic and manual opportunity transitions."""

    opportunity = models.ForeignKey(
        CrmOpportunity,
        on_delete=models.CASCADE,
        related_name="stage_history",
        verbose_name="فرصت",
    )
    from_stage = models.CharField(max_length=24, blank=True, default="", verbose_name="مرحله قبلی")
    to_stage = models.CharField(max_length=24, db_index=True, verbose_name="مرحله جدید")
    event = models.CharField(max_length=80, blank=True, default="", verbose_name="رویداد")
    event_key = models.CharField(
        max_length=180,
        null=True,
        blank=True,
        unique=True,
        verbose_name="کلید یکتای رویداد",
    )
    reason = models.CharField(max_length=255, blank=True, default="", verbose_name="دلیل")
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="کاربر عامل",
    )
    metadata = models.JSONField(default=dict, blank=True, verbose_name="اطلاعات رویداد")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "تاریخچه مرحله فرصت"
        verbose_name_plural = "تاریخچه مراحل فرصت‌ها"
        indexes = [models.Index(fields=["opportunity", "created_at"])]

    def __str__(self):
        return f"{self.opportunity_id}: {self.from_stage or '-'} -> {self.to_stage}"


class CrmSyncEvent(models.Model):
    """Retryable record of website-to-CRM synchronization attempts."""

    STATUS_PENDING = "pending"
    STATUS_PROCESSED = "processed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "در انتظار"),
        (STATUS_PROCESSED, "انجام‌شده"),
        (STATUS_FAILED, "ناموفق"),
    ]

    source_type = models.CharField(max_length=24, choices=CrmOpportunity.SOURCE_CHOICES, db_index=True)
    source_id = models.CharField(max_length=64, db_index=True)
    event_key = models.CharField(max_length=180, unique=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "رویداد همگام‌سازی CRM"
        verbose_name_plural = "رویدادهای همگام‌سازی CRM"
        indexes = [models.Index(fields=["status", "updated_at"])]

    def __str__(self):
        return f"{self.source_type}:{self.source_id} ({self.status})"
