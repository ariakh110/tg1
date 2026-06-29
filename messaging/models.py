import secrets

from django.conf import settings
from django.db import models


class MessagingSettings(models.Model):
    """تنظیماتِ تک‌نمونه‌ایِ پیام‌رسانی (ادمین‌محور): سوییچِ اصلی، سرویس‌دهنده، و کلیدِ پنلِ پیامک.

    پیش‌فرض غیرفعال است؛ تا وقتی `sms_enabled` روشن نشود و کلیدِ کاوه‌نگار وارد نشود،
    همهٔ ارسال‌ها «خشک» (dry-run) ثبت می‌شوند و هیچ پیامکی واقعاً ارسال نمی‌شود.
    """

    PROVIDER_KAVENEGAR = "kavenegar"
    PROVIDER_CHOICES = [(PROVIDER_KAVENEGAR, "کاوه‌نگار")]

    sms_enabled = models.BooleanField(default=False, verbose_name="ارسالِ پیامک فعال است")
    provider = models.CharField(
        max_length=20, choices=PROVIDER_CHOICES, default=PROVIDER_KAVENEGAR, verbose_name="سرویس‌دهنده"
    )

    # کلیدِ محرمانه؛ در API هرگز برنمی‌گردد (write-only در سریالایزر).
    kavenegar_api_key = models.CharField(max_length=255, blank=True, default="", verbose_name="کلید API کاوه‌نگار")
    sender = models.CharField(
        max_length=20, blank=True, default="", verbose_name="خطِ ارسال (اختیاری)",
        help_text="شمارهٔ خطِ پیش‌فرضِ ارسال برای پیامکِ متنی (sms/send). خالی ⇒ خطِ پیش‌فرضِ حساب.",
    )
    # نامِ الگوهای verify/lookup که در پنلِ کاوه‌نگار تعریف و تأیید شده‌اند.
    default_template = models.CharField(
        max_length=80, blank=True, default="", verbose_name="الگوی پیش‌فرض (lookup)",
        help_text="نامِ الگوی verify/lookup برای پیامکِ تراکنشی (فیلترنشده). خالی ⇒ ارسالِ متنیِ ساده.",
    )
    purchase_template = models.CharField(
        max_length=80, blank=True, default="", verbose_name="الگوی مراحلِ خرید (lookup)",
        help_text="نامِ الگوی verify/lookup برای پیامکِ مراحلِ خرید. خالی ⇒ ارسالِ متنیِ ساده.",
    )
    daily_send_cap = models.PositiveIntegerField(
        default=0, verbose_name="سقفِ ارسالِ روزانه",
        help_text="حداکثر پیامکِ ارسالی در هر شبانه‌روز (محافظِ هزینه). صفر یعنی بدونِ محدودیت.",
    )
    # کلیدِ مخفیِ داخلِ مسیرِ وب‌هوک تا فقط کاوه‌نگار بتواند وضعیت/پیامکِ دریافتی را بفرستد.
    webhook_secret = models.CharField(max_length=64, blank=True, default="", verbose_name="کلید مخفیِ وب‌هوک")

    # --- ربات تلگرام (برای اطلاع‌رسانیِ آنیِ ادمین؛ رایگان) ---
    telegram_enabled = models.BooleanField(default=False, verbose_name="اطلاع‌رسانیِ تلگرام فعال است")
    # توکنِ ربات (از BotFather)؛ محرمانه — در API برنمی‌گردد (write-only در سریالایزر).
    telegram_bot_token = models.CharField(max_length=120, blank=True, default="", verbose_name="توکنِ ربات تلگرام")
    telegram_admin_chat_id = models.CharField(
        max_length=120, blank=True, default="", verbose_name="آیدیِ چتِ ادمین",
        help_text="chat_id مقصدِ اطلاع‌رسانی؛ چند مقصد را با کاما جدا کن.",
    )
    # ریشهٔ API تلگرام؛ برای سرورِ داخلِ ایران (که api.telegram.org فیلتر است) یک واسطِ
    # قابل‌دسترس بگذار: Cloudflare Worker یا nginx reverse-proxy روی دامنه/سرورِ خارج.
    telegram_api_base = models.CharField(
        max_length=200, blank=True, default="https://api.telegram.org",
        verbose_name="ریشهٔ API تلگرام",
        help_text="پیش‌فرض api.telegram.org؛ از داخلِ ایران یک واسط (Cloudflare Worker/پروکسی) بگذار.",
    )

    # --- اطلاع‌رسانیِ رویدادهای سایت به ادمین ---
    # شمارهٔ موبایلِ ادمین برای دریافتِ پیامکِ هشدار (در صورتِ فعال‌بودنِ پیامک). خالی ⇒ پیامکِ ادمین نمی‌رود.
    admin_alert_phone = models.CharField(max_length=32, blank=True, default="", verbose_name="موبایلِ ادمین برای هشدارِ پیامکی")
    notify_on_signup = models.BooleanField(default=True, verbose_name="خبر هنگام ثبت‌نامِ کاربر")
    notify_on_order = models.BooleanField(default=True, verbose_name="خبر هنگام ثبتِ سفارش")
    notify_on_chat_lead = models.BooleanField(default=True, verbose_name="خبر هنگام سرنخِ چت")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات پیام‌رسانی"
        verbose_name_plural = "تنظیمات پیام‌رسانی"

    def __str__(self):
        return f"تنظیمات پیام‌رسانی ({'فعال' if self.is_configured else 'غیرفعال'})"

    def save(self, *args, **kwargs):
        self.pk = 1  # همیشه یک رکورد (singleton)
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        if not obj.webhook_secret:
            obj.webhook_secret = secrets.token_urlsafe(24)
            obj.save(update_fields=["webhook_secret"])
        return obj

    @property
    def is_configured(self):
        """آماده برای ارسالِ واقعی: سوییچ روشن و کلید موجود."""
        return bool(self.sms_enabled and (self.kavenegar_api_key or "").strip())

    @property
    def telegram_configured(self):
        """آماده برای ارسالِ تلگرام: سوییچ روشن، توکن و مقصد موجود."""
        return bool(
            self.telegram_enabled
            and (self.telegram_bot_token or "").strip()
            and (self.telegram_admin_chat_id or "").strip()
        )

    @property
    def telegram_chat_ids(self):
        """فهرستِ مقصدهای تلگرام (جداشده با کاما)."""
        raw = (self.telegram_admin_chat_id or "").replace("،", ",")
        return [c.strip() for c in raw.split(",") if c.strip()]


class OutboundMessage(models.Model):
    """لاگِ هر تلاشِ ارسالِ پیام (ممیزی + پیگیریِ وضعیت). کانال‌پذیر تا تلگرام/واتساپ بعداً اضافه شوند."""

    CHANNEL_SMS = "sms"
    CHANNEL_TELEGRAM = "telegram"
    CHANNEL_WHATSAPP = "whatsapp"
    CHANNEL_CHOICES = [
        (CHANNEL_SMS, "پیامک"),
        (CHANNEL_TELEGRAM, "تلگرام"),
        (CHANNEL_WHATSAPP, "واتساپ"),
    ]

    PURPOSE_MANUAL = "manual"
    PURPOSE_BULK = "bulk"
    PURPOSE_ORDER_STATUS = "order_status"
    PURPOSE_OTP = "otp"
    PURPOSE_ADMIN_ALERT = "admin_alert"
    PURPOSE_CHOICES = [
        (PURPOSE_MANUAL, "دستی"),
        (PURPOSE_BULK, "گروهی"),
        (PURPOSE_ORDER_STATUS, "مراحل خرید"),
        (PURPOSE_OTP, "کد یک‌بارمصرف"),
        (PURPOSE_ADMIN_ALERT, "هشدار ادمین"),
    ]

    STATUS_QUEUED = "queued"
    STATUS_SENT = "sent"
    STATUS_DELIVERED = "delivered"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "در صف"),
        (STATUS_SENT, "ارسال شد"),
        (STATUS_DELIVERED, "رسید به گیرنده"),
        (STATUS_FAILED, "ناموفق"),
        (STATUS_SKIPPED, "نادیده (خشک)"),
    ]

    channel = models.CharField(max_length=12, choices=CHANNEL_CHOICES, default=CHANNEL_SMS, db_index=True, verbose_name="کانال")
    provider = models.CharField(max_length=20, blank=True, default="", verbose_name="سرویس‌دهنده")
    customer = models.ForeignKey(
        "customers.Customer", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="messages", verbose_name="مشتری",
    )
    recipient = models.CharField(max_length=32, db_index=True, verbose_name="گیرنده")
    purpose = models.CharField(max_length=16, choices=PURPOSE_CHOICES, default=PURPOSE_MANUAL, db_index=True, verbose_name="هدف")
    template = models.CharField(max_length=80, blank=True, default="", verbose_name="الگو")
    body = models.TextField(blank=True, default="", verbose_name="متن")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_QUEUED, db_index=True, verbose_name="وضعیت")
    provider_message_id = models.CharField(max_length=64, blank=True, default="", verbose_name="شناسهٔ پیام نزدِ سرویس")
    cost = models.IntegerField(null=True, blank=True, verbose_name="هزینه (ریال)")
    error = models.CharField(max_length=400, blank=True, default="", verbose_name="خطا")
    meta = models.JSONField(null=True, blank=True, verbose_name="اطلاعاتِ اضافه")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "پیامِ ارسالی"
        verbose_name_plural = "پیام‌های ارسالی"
        indexes = [
            models.Index(fields=["customer", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_channel_display()} → {self.recipient} ({self.get_status_display()})"
