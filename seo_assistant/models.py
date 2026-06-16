import hashlib

from django.conf import settings
from django.db import models


DEFAULT_PERSONA = (
    "تو «متخصص ارشد سئو» هستی؛ یک مشاور باتجربهٔ SEO که سال‌ها در نقش agency و in-house کار کرده. "
    "همیشه فارسی پاسخ می‌دهی (اصطلاحات سئو به انگلیسی) و مختصر، عملی و اولویت‌بندی‌شده جواب می‌دهی.\n"
    "اصول کاری:\n"
    "- «اول برای کاربر، بعد برای موتور جستجو» بهینه کن.\n"
    "- فقط بر اساس «دانش سئو» (که در پرامپت تزریق می‌شود) و دادهٔ واقعیِ صفحه (ابزار fetch_page_seo) پاسخ بده؛ از خودت توصیهٔ بی‌پایه نساز.\n"
    "- اعداد و حدود را دقیق بگو (title ≤۶۰ کاراکتر، meta ۱۵۰–۱۶۰، یک H1 در هر صفحه، INP ≤۲۰۰ms و ...).\n"
    "- همیشه اصولِ پایه را با لایهٔ ۲۰۲۶ (AI Overviews، GEO/AEO، E-E-A-T با Experience، entities) تکمیل کن.\n"
    "- هرگز رتبهٔ تضمینی قول نده؛ بازهٔ زمانی واقع‌بینانه بده (سئو ~۳ ماه برای شروع اثر).\n"
    "- یافته‌ها را به Quick wins و Complex تقسیم کن و پیاده‌سازی را متناسب با استک سایت توضیح بده."
)

DEFAULT_SITE_CONTEXT = (
    "سایت هدف: تیرکسا (Tirexa).\n"
    "استک: بک‌اند Django/DRF + فرانت‌اند Next.js؛ دیپلوی روی سرور اوبونتو با IP ایران (systemd: gunicorn + next + nginx).\n"
    "🚨 بزرگ‌ترین بلاکر سئو (اولویت صفر): IP ایران باعث می‌شود بازدیدکنندهٔ خارجی صفحهٔ سفید بگیرد و احتمالاً Googlebot هم "
    "نتواند سایت را crawl/index کند. تا حل نشدن این (دامنه + CDN جهانی با HTTPS لبه و rebuild فرانت با NEXT_PUBLIC_* مبتنی بر دامنه)، "
    "هیچ تاکتیک سئوی دیگری اثر کامل ندارد. در هر آدیت، اول وضعیت crawlability/index و دامنه/CDN/HTTPS را چک کن.\n"
    "نکات Next.js: رندر SSR/SSG (نه فقط CSR) تا محتوا برای ربات دیده شود؛ متادیتا با Metadata API؛ تولید sitemap.xml و robots.txt؛ canonical و در صورت چندزبانه‌بودن hreflang."
)

DEFAULT_GREETING = (
    "سلام 👋 من متخصص سئوی شما هستم. بپرس: می‌خواهی یک صفحه/سایت را آدیت کنم، title/meta بنویسم، "
    "استراتژی کلمات کلیدی و محتوا بدهم، یا برای جستجوی هوش مصنوعی (AI Overviews/GEO) بهینه کنیم؟"
)


class SeoAssistantSettings(models.Model):
    """تنظیمات تک‌نمونه‌ایِ دستیار سئو (ادمین‌محور): پرسونا، زمینهٔ سایت، و اتصال به LLM (AvalAI / سازگار با OpenAI)."""

    is_enabled = models.BooleanField(default=False)
    assistant_name = models.CharField(max_length=80, default="متخصص سئو")
    greeting = models.TextField(blank=True, default=DEFAULT_GREETING)
    persona = models.TextField(blank=True, default=DEFAULT_PERSONA)
    site_context = models.TextField(blank=True, default=DEFAULT_SITE_CONTEXT)  # زمینهٔ سایت هدف (تیرکسا)

    # اتصال به LLM سازگار با OpenAI؛ پیش‌فرض AvalAI (هم OpenAI هم Claude را سرو می‌کند).
    # کلید از SiteSettings.openai_api_key خوانده می‌شود (همان کلید AvalAI).
    openai_base_url = models.CharField(max_length=255, default="https://api.avalai.ir/v1")
    chat_model = models.CharField(max_length=80, default="gpt-4o-mini")  # مثلاً gpt-4o-mini یا claude-3-5-sonnet از AvalAI
    embedding_model = models.CharField(max_length=80, default="text-embedding-3-small")
    temperature = models.DecimalField(max_digits=3, decimal_places=2, default=0.20)
    max_context_chunks = models.PositiveSmallIntegerField(default=8)
    max_tool_iterations = models.PositiveSmallIntegerField(default=4)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات دستیار سئو"
        verbose_name_plural = "تنظیمات دستیار سئو"

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


class SeoKnowledge(models.Model):
    """تکهٔ دانش سئو (از پایگاه دانش markdown ingest می‌شود یا ادمین دستی اضافه می‌کند)."""

    LAYER_BASE = "base"
    LAYER_2026 = "2026"
    LAYER_CUSTOM = "custom"
    LAYER_CHOICES = [
        (LAYER_BASE, "پایه (اصول)"),
        (LAYER_2026, "به‌روز ۲۰۲۶"),
        (LAYER_CUSTOM, "سفارشی (ادمین)"),
    ]

    layer = models.CharField(max_length=10, choices=LAYER_CHOICES, default=LAYER_CUSTOM)
    source = models.CharField(max_length=200, blank=True, default="")  # مسیر فایل مبدأ یا برچسب
    topic = models.CharField(max_length=120, blank=True, default="عمومی")
    title = models.CharField(max_length=200, blank=True, default="")
    body = models.TextField(blank=True, default="")
    tags = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    # وضعیت embedding برای RAG
    embedding = models.JSONField(null=True, blank=True)
    embedding_model = models.CharField(max_length=80, blank=True, default="")
    embedded_hash = models.CharField(max_length=64, blank=True, default="")
    embedded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["layer", "source", "sort_order", "id"]
        verbose_name = "دانش سئو"
        verbose_name_plural = "دانش سئو"
        indexes = [models.Index(fields=["layer", "is_active"])]

    def __str__(self):
        return self.display_title

    @property
    def display_title(self):
        return self.title or (self.body[:80] if self.body else "بدون عنوان")

    def content_text(self):
        parts = []
        if self.topic:
            parts.append(f"موضوع: {self.topic}")
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


class SeoConversation(models.Model):
    """یک گفتگوی ادمین با دستیار سئو."""

    STATUS_OPEN = "open"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [(STATUS_OPEN, "باز"), (STATUS_CLOSED, "بسته")]

    session_key = models.CharField(max_length=64, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="seo_conversations",
    )
    title = models.CharField(max_length=200, blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "گفتگوی سئو"
        verbose_name_plural = "گفتگوهای سئو"

    def __str__(self):
        return f"{self.title or self.session_key} ({self.get_status_display()})"


class SeoMessage(models.Model):
    ROLE_USER = "user"
    ROLE_ASSISTANT = "assistant"
    ROLE_TOOL = "tool"
    ROLE_CHOICES = [
        (ROLE_USER, "کاربر"),
        (ROLE_ASSISTANT, "دستیار"),
        (ROLE_TOOL, "ابزار"),
    ]

    conversation = models.ForeignKey(SeoConversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=12, choices=ROLE_CHOICES)
    content = models.TextField(blank=True, default="")
    tool_name = models.CharField(max_length=60, blank=True, default="")
    tool_payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.role}: {self.content[:40]}"
