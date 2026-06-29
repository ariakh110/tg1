"""سرویسِ پیام‌رسانیِ کانال‌پذیر (فعلاً فقط SMS/کاوه‌نگار).

نقطهٔ ورودِ یگانه برای ارسال: تنظیمات را می‌خواند، شماره را نرمال می‌کند، یک
`OutboundMessage` ثبت می‌کند، و در صورتِ فعال‌بودن سرویس‌دهنده را صدا می‌زند.
اگر `sms_enabled` خاموش یا کلید نباشد، ارسال «خشک» (skipped) ثبت می‌شود — بدونِ تماس با
سرویس و بدونِ خطا — تا کلِ جریان پیش از وجودِ اعتبار قابلِ آزمایش باشد.
"""
import re

from django.utils import timezone

from customers.models import Customer, CustomerActivity
from .models import MessagingSettings, OutboundMessage
from .providers import kavenegar

# متنِ مراحلِ خرید (پیامکِ فروشِ مستقیم). {order}/{amount} در صورتِ وجود جایگزین می‌شوند.
PURCHASE_STEPS = {
    "registered": "سفارش شما ثبت شد.",
    "preparing": "سفارش شما در حال آماده‌سازی است.",
    "invoiced": "پیش‌فاکتور سفارش شما صادر شد.",
    "shipped": "سفارش شما ارسال شد.",
    "delivered": "سفارش شما تحویل داده شد. از خرید شما سپاسگزاریم.",
}


def normalize_phone(raw):
    """نرمال‌سازیِ شمارهٔ ایران به شکلِ 09XXXXXXXXX (تا یک مشتری به یک گیرنده نگاشت شود)."""
    digits = re.sub(r"\D", "", str(raw or ""))
    if digits.startswith("0098"):
        digits = digits[4:]
    elif digits.startswith("98") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    return digits


def _today_sent_count():
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return OutboundMessage.objects.filter(created_at__gte=start).exclude(
        status=OutboundMessage.STATUS_SKIPPED
    ).count()


def _log_activity(customer, message, status, created_by):
    label = {
        OutboundMessage.STATUS_SENT: "ارسال شد",
        OutboundMessage.STATUS_SKIPPED: "خشک (سرویس غیرفعال)",
        OutboundMessage.STATUS_FAILED: "ناموفق",
    }.get(status, status)
    snippet = (message or "").strip().replace("\n", " ")[:120]
    CustomerActivity.objects.create(
        customer=customer,
        kind=CustomerActivity.KIND_MESSAGE,
        body=f"پیامک ({label}): {snippet}",
        created_by=created_by if getattr(created_by, "is_authenticated", False) else None,
    )


def send_sms(recipient, message, *, customer=None, purpose=OutboundMessage.PURPOSE_MANUAL,
             template="", tokens=None, created_by=None, cfg=None, log_activity=True, meta=None):
    """ارسالِ یک پیامک و ثبتِ آن در لاگ. خروجی: نمونهٔ `OutboundMessage`.

    اگر `template` و `tokens` داده شود، مسیرِ verify/lookup (فیلترنشده) استفاده می‌شود؛
    وگرنه sms/send سادهٔ متنی.
    """
    cfg = cfg or MessagingSettings.load()
    recipient = normalize_phone(recipient)
    body = message or ("[الگو: %s] %s" % (template, " | ".join(tokens or [])) if template else "")

    msg = OutboundMessage(
        channel=OutboundMessage.CHANNEL_SMS,
        provider=cfg.provider,
        customer=customer,
        recipient=recipient,
        purpose=purpose,
        template=template,
        body=body,
        meta=meta,
        created_by=created_by if getattr(created_by, "is_authenticated", False) else None,
    )

    if not recipient:
        msg.status = OutboundMessage.STATUS_FAILED
        msg.error = "شمارهٔ گیرنده نامعتبر است."
    elif not cfg.is_configured:
        # حالتِ خشک: سرویس خاموش یا بدونِ کلید — هیچ تماسی با سرویس‌دهنده گرفته نمی‌شود.
        msg.status = OutboundMessage.STATUS_SKIPPED
        msg.error = "" if cfg.sms_enabled else "ارسالِ پیامک در تنظیمات غیرفعال است."
    else:
        if template and tokens:
            t = list(tokens) + ["", "", ""]
            result = kavenegar.send_lookup(cfg.kavenegar_api_key, recipient, template, t[0], t[1], t[2])
        else:
            result = kavenegar.send_sms(cfg.kavenegar_api_key, recipient, body, cfg.sender)
        msg.status = result.status or (OutboundMessage.STATUS_SENT if result.ok else OutboundMessage.STATUS_FAILED)
        msg.provider_message_id = result.message_id
        msg.cost = result.cost
        msg.error = result.error[:400]

    msg.save()
    if customer and log_activity:
        _log_activity(customer, body, msg.status, created_by)
    return msg


def send_to_customer(customer, message=None, *, template="", tokens=None,
                     purpose=OutboundMessage.PURPOSE_MANUAL, created_by=None, cfg=None):
    """ارسالِ پیامک به مشتریِ CRM (روی شمارهٔ موبایلِ مشتری) + ثبتِ فعالیت روی تایم‌لاین."""
    return send_sms(
        customer.phone, message, customer=customer, template=template, tokens=tokens,
        purpose=purpose, created_by=created_by, cfg=cfg,
    )


def send_bulk(customers, message, *, purpose=OutboundMessage.PURPOSE_BULK, created_by=None, cfg=None):
    """ارسالِ یک متن به گروهی از مشتریان (به‌ترتیب)؛ سقفِ ارسالِ روزانه رعایت می‌شود.

    خروجی: dict خلاصه {sent, skipped, failed, total, messages}.
    """
    cfg = cfg or MessagingSettings.load()
    cap = cfg.daily_send_cap or 0
    already = _today_sent_count() if cap else 0

    results = []
    counters = {"sent": 0, "skipped": 0, "failed": 0}
    for customer in customers:
        if cap and (already + counters["sent"]) >= cap:
            msg = OutboundMessage.objects.create(
                channel=OutboundMessage.CHANNEL_SMS, provider=cfg.provider, customer=customer,
                recipient=normalize_phone(customer.phone), purpose=purpose, body=message,
                status=OutboundMessage.STATUS_SKIPPED, error="سقفِ ارسالِ روزانه پر شده است.",
                created_by=created_by if getattr(created_by, "is_authenticated", False) else None,
            )
        else:
            msg = send_to_customer(customer, message, purpose=purpose, created_by=created_by, cfg=cfg)
        results.append(msg)
        if msg.status in (OutboundMessage.STATUS_SENT, OutboundMessage.STATUS_DELIVERED):
            counters["sent"] += 1
        elif msg.status == OutboundMessage.STATUS_SKIPPED:
            counters["skipped"] += 1
        else:
            counters["failed"] += 1
    return {**counters, "total": len(results), "messages": results}


def notify_purchase_step(customer, step, *, order_no="", amount=None, created_by=None, cfg=None):
    """ارسالِ پیامکِ یک مرحله از خرید به مشتری (فروشِ مستقیم).

    متن از `PURCHASE_STEPS` ساخته می‌شود (+ شمارهٔ سفارش/مبلغ). اگر الگوی مراحلِ خرید
    در تنظیمات باشد، از مسیرِ verify/lookup (فیلترنشده) با توکن‌ها استفاده می‌شود.
    """
    cfg = cfg or MessagingSettings.load()
    base = PURCHASE_STEPS.get(step)
    if not base:
        raise ValueError(f"مرحلهٔ نامعتبر: {step}")

    parts = [base]
    if order_no:
        parts.append(f"شمارهٔ سفارش: {order_no}")
    if amount is not None:
        parts.append(f"مبلغ: {int(amount):,} تومان")
    body = " ".join(parts)

    template = cfg.purchase_template or ""
    tokens = [str(order_no or step)] if template else None
    if template and amount is not None:
        tokens.append(f"{int(amount):,}")

    return send_sms(
        customer.phone, body, customer=customer, template=template, tokens=tokens,
        purpose=OutboundMessage.PURPOSE_ORDER_STATUS, created_by=created_by, cfg=cfg,
        meta={"step": step, "order_no": order_no},
    )


def log_incoming_sms(sender, text, raw=None):
    """پیامکِ دریافتی از مشتری (وب‌هوکِ کاوه‌نگار) را روی تایم‌لاینِ همان مشتری ثبت می‌کند.

    اگر شماره با هیچ مشتری‌ای جور نشود، چیزی ثبت نمی‌شود (None برمی‌گردد).
    """
    phone = normalize_phone(sender)
    customer = Customer.objects.filter(phone=phone).first()
    if not customer:
        return None
    snippet = (text or "").strip().replace("\n", " ")[:200]
    return CustomerActivity.objects.create(
        customer=customer,
        kind=CustomerActivity.KIND_MESSAGE,
        body=f"پیامکِ دریافتی: {snippet}",
    )
