import hashlib

from django.conf import settings
from django.db import models


DEFAULT_PERSONA = (
    "تو «مشاور فروش» فروشگاه آنلاین آهن و فولاد هستی؛ یک کارشناسِ باتجربهٔ فروشِ تجهیزات و "
    "مقاطع صنعتی (ورق، رول، تیرآهن، میلگرد، لوله، پروفیل، شمش). لحن تو حرفه‌ای، مودب، دقیق و "
    "کوتاه است و همیشه فارسی پاسخ می‌دهی.\n"
    "اصول کاری:\n"
    "- فقط بر اساس «دانش فروشگاه»، کاتالوگ محصولات و قیمت‌های واقعی پاسخ بده؛ چیزی از خودت نساز.\n"
    "- اگر قیمت یا موجودیِ دقیق را نمی‌دانی، صادقانه بگو و کاربر را به «استعلام قیمت» یا تماس راهنمایی کن.\n"
    "- واحدها را دقیق بیان کن (میلی‌متر، کیلوگرم، تن، تومان) و اعداد را خوانا بنویس.\n"
    "- برای انتخاب درست، نیاز کاربر را بفهم (نوع کالا، گرید/آلیاژ، ضخامت/ابعاد، مقدار، محل تحویل).\n"
    "- هیچ‌وقت ادعای قطعیِ تحویل/زمان/تخفیف نکن مگر در دانش آمده باشد."
)

DEFAULT_WORKFLOW = (
    "گردش‌کار فروش را گام‌به‌گام دنبال کن:\n"
    "۱) خوش‌آمد کوتاه و پرسیدن نیاز مشتری (چه محصولی، چه گرید/ابعادی، چه مقدار).\n"
    "۲) با ابزار جستجوی محصول، گزینه‌های مناسب را پیدا کن و خلاصه و شفاف معرفی کن (با لینک محصول).\n"
    "۳) اگر قیمت خواست، با ابزار قیمت، برآورد قیمت/وزن را بده و شرایط (محل تحویل، ارزش افزوده) را توضیح بده.\n"
    "۴) وقتی مشتری تمایل به خرید/استعلام داشت، نام و شمارهٔ موبایلش را مودبانه بگیر و با ابزار ثبت سرنخ ذخیره کن.\n"
    "۵) در پایان، مسیر ادامهٔ کار را بگو: «استعلام قیمت»/«خرید» در صفحهٔ محصول یا تماس با کارشناس.\n"
    "اگر سوال خارج از حوزهٔ فروش فولاد بود، مودبانه به موضوع فروش برگرد."
)

DEFAULT_GREETING = (
    "سلام 👋 من مشاور فروش فولاد هستم. بفرمایید چه محصولی نیاز دارید (نوع، گرید، ضخامت/ابعاد و مقدار) "
    "تا بهترین گزینه و قیمت را برایتان پیدا کنم."
)


class AssistantSettings(models.Model):
    """تنظیمات تک‌نمونه‌ایِ دستیار فروش (پرسونا، گردش‌کار، مدل‌ها و اتصال به LLM)."""

    is_enabled = models.BooleanField(default=False)  # نمایش ویجت در سایت
    assistant_name = models.CharField(max_length=80, default="مشاور فروش")
    greeting = models.TextField(blank=True, default=DEFAULT_GREETING)
    persona = models.TextField(blank=True, default=DEFAULT_PERSONA)  # پرسونا/دستور سیستم پایه
    sales_workflow = models.TextField(blank=True, default=DEFAULT_WORKFLOW)  # گردش‌کار فروش

    # اتصال به LLM (سازگار با OpenAI). کلید از SiteSettings.openai_api_key خوانده می‌شود.
    openai_base_url = models.CharField(max_length=255, default="https://api.openai.com/v1")
    chat_model = models.CharField(max_length=80, default="gpt-4o-mini")
    embedding_model = models.CharField(max_length=80, default="text-embedding-3-small")
    temperature = models.DecimalField(max_digits=3, decimal_places=2, default=0.30)
    max_context_chunks = models.PositiveSmallIntegerField(default=6)  # تعداد تکه‌های دانش در پرامپت
    max_tool_iterations = models.PositiveSmallIntegerField(default=4)

    lead_capture_enabled = models.BooleanField(default=True)
    handoff_phone = models.CharField(max_length=30, blank=True, default="")
    handoff_note = models.CharField(max_length=255, blank=True, default="برای مشاورهٔ تخصصی با کارشناس تماس بگیرید.")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات دستیار فروش"
        verbose_name_plural = "تنظیمات دستیار فروش"

    def __str__(self):
        return self.assistant_name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def api_key(self):
        from core.models import SiteSettings

        return (SiteSettings.load().openai_api_key or getattr(settings, "OPENAI_API_KEY", "")).strip()


class AssistantKnowledge(models.Model):
    """دانش/آموزشِ ادمین‌مدیریتی برای دستیار فروش (پرسش‌وپاسخ یا مقاله)."""

    KIND_QA = "qa"
    KIND_ARTICLE = "article"
    KIND_CHOICES = [
        (KIND_QA, "پرسش و پاسخ"),
        (KIND_ARTICLE, "مقاله / متن آزاد"),
    ]

    kind = models.CharField(max_length=12, choices=KIND_CHOICES, default=KIND_QA)
    topic = models.CharField(max_length=80, blank=True, default="عمومی")  # موضوع/دسته
    title = models.CharField(max_length=200, blank=True, default="")  # عنوان مقاله یا برچسبِ پرسش
    question = models.TextField(blank=True, default="")  # برای نوع پرسش‌وپاسخ
    answer = models.TextField(blank=True, default="")    # برای نوع پرسش‌وپاسخ
    body = models.TextField(blank=True, default="")      # برای نوع مقاله
    tags = models.CharField(max_length=255, blank=True, default="")  # برچسب‌ها (با کاما)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    # وضعیت embedding برای RAG
    embedding = models.JSONField(null=True, blank=True)          # بردار
    embedding_model = models.CharField(max_length=80, blank=True, default="")
    embedded_hash = models.CharField(max_length=64, blank=True, default="")  # هشِ متنی که embed شده
    embedded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["topic", "sort_order", "id"]
        verbose_name = "دانش دستیار"
        verbose_name_plural = "دانش دستیار"

    def __str__(self):
        return self.display_title

    @property
    def display_title(self):
        if self.title:
            return self.title
        if self.kind == self.KIND_QA and self.question:
            return self.question[:80]
        return (self.body or self.answer or "بدون عنوان")[:80]

    def content_text(self):
        """متن قابل‌استفاده در embedding و تزریق به پرامپت."""
        parts = []
        if self.topic:
            parts.append(f"موضوع: {self.topic}")
        if self.kind == self.KIND_QA:
            if self.title:
                parts.append(self.title)
            if self.question:
                parts.append(f"پرسش: {self.question}")
            if self.answer:
                parts.append(f"پاسخ: {self.answer}")
        else:
            if self.title:
                parts.append(self.title)
            if self.body:
                parts.append(self.body)
        if self.tags:
            parts.append(f"برچسب‌ها: {self.tags}")
        return "\n".join(p for p in parts if p).strip()

    def content_hash(self):
        return hashlib.sha256(self.content_text().encode("utf-8")).hexdigest()

    @property
    def needs_embedding(self):
        return self.is_active and (not self.embedding or self.embedded_hash != self.content_hash())


class AssistantConversation(models.Model):
    """یک گفتگوی دستیار با یک بازدیدکننده/مشتری."""

    STATUS_OPEN = "open"
    STATUS_LEAD = "lead"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_OPEN, "باز"),
        (STATUS_LEAD, "سرنخ"),
        (STATUS_CLOSED, "بسته"),
    ]

    session_key = models.CharField(max_length=64, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assistant_conversations"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)

    # سرنخ ثبت‌شده
    lead_name = models.CharField(max_length=120, blank=True, default="")
    lead_phone = models.CharField(max_length=30, blank=True, default="")
    lead_interest = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "گفتگوی دستیار"
        verbose_name_plural = "گفتگوهای دستیار"

    def __str__(self):
        return f"{self.session_key} ({self.get_status_display()})"


class AssistantMessage(models.Model):
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_TOOL = "tool"
    ROLE_CHOICES = [
        (ROLE_USER, "کاربر"),
        (ROLE_ASSISTANT, "دستیار"),
        (ROLE_TOOL, "ابزار"),
    ]

    conversation = models.ForeignKey(AssistantConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=12, choices=ROLE_CHOICES)
    content = models.TextField(blank=True, default="")
    tool_name = models.CharField(max_length=60, blank=True, default="")
    tool_payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"


class AssistantInquiry(models.Model):
    """استعلام/سرنخِ ساختاریافته که از متن آزادِ مشتری استخراج شده است."""

    STATUS_NEW = "new"
    STATUS_QUOTED = "quoted"
    STATUS_CONTACTED = "contacted"
    STATUS_WON = "won"
    STATUS_LOST = "lost"
    STATUS_CHOICES = [
        (STATUS_NEW, "جدید"),
        (STATUS_QUOTED, "پیش‌فاکتور"),
        (STATUS_CONTACTED, "پیگیری‌شده"),
        (STATUS_WON, "موفق"),
        (STATUS_LOST, "ازدست‌رفته"),
    ]

    conversation = models.ForeignKey(
        AssistantConversation, null=True, blank=True, on_delete=models.SET_NULL, related_name="inquiries"
    )
    product = models.CharField(max_length=120, blank=True, default="")   # نوع کالا (میلگرد/ورق/...)
    size = models.CharField(max_length=60, blank=True, default="")       # سایز/ضخامت
    grade = models.CharField(max_length=60, blank=True, default="")      # گرید/آلیاژ
    factory = models.CharField(max_length=80, blank=True, default="")    # کارخانه/مبدا
    quantity = models.CharField(max_length=60, blank=True, default="")   # مقدار
    city = models.CharField(max_length=80, blank=True, default="")       # شهر
    note = models.CharField(max_length=255, blank=True, default="")
    raw_text = models.TextField(blank=True, default="")                  # متنِ اصلیِ مشتری

    matched_product = models.ForeignKey(
        "products.Product", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    matched_price = models.DecimalField(max_digits=14, decimal_places=0, null=True, blank=True)  # تومان

    contact_name = models.CharField(max_length=120, blank=True, default="")
    contact_phone = models.CharField(max_length=30, blank=True, default="")

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_NEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "استعلام ساختاریافته"
        verbose_name_plural = "استعلام‌های ساختاریافته"

    def __str__(self):
        return self.summary or "استعلام"

    @property
    def summary(self):
        parts = [self.product, self.grade, self.size, self.factory, self.quantity, self.city]
        return " - ".join(p for p in parts if p)
