"""مغزِ ربات دوطرفهٔ بله: مسیریابیِ آپدیت‌ها (پیام/کلیکِ دکمه).

سه کار می‌کند:
- دکمه‌های عملیاتیِ روی پیام‌های گروه (callback_query) → آپدیتِ مستقیمِ CRM.
- دستورهای مدیریتی (/امروز /سرنخ /بدهکاران) برای ادمین‌ها.
- ربات قیمت برای کاربران: هر متنِ آزاد → جستجوی محصول و پاسخِ قیمت (موتورِ دستیار).

همه چیز «امن» است: هیچ خطایی نباید به وب‌هوک نشت کند (خودِ ویو هم try/except دارد).
"""
import logging
from datetime import timedelta

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from customers.models import Customer, CustomerActivity, CustomerTransaction
from customers.services import normalize_phone

logger = logging.getLogger(__name__)

WELCOME_PUBLIC = (
    "سلام 👋 به ربات کاوکس خوش آمدید.\n"
    "نامِ محصول را بفرستید تا قیمت و موجودی را بدهم؛ مثلاً «میلگرد ۱۴» یا «ورق ۳ سیاه»."
)
WELCOME_ADMIN = (
    "پنلِ مدیریتِ کاوکس 👤\n"
    "دستورها:\n"
    "/امروز — سرنخ‌های جدید و پیگیری‌های سررسیده\n"
    "/سرنخ 0912... — پروندهٔ یک مشتری\n"
    "/بدهکاران — مشتریانِ بدهکار"
)


def _cfg():
    from .models import MessagingSettings

    return MessagingSettings.load()


def _reply(cfg, chat_id, text, reply_markup=None):
    from .providers import telegram

    return telegram.send_message(
        cfg.telegram_bot_token, chat_id, text, base_url=cfg.telegram_api_base, reply_markup=reply_markup,
    )


def _toman(amount):
    n = int(amount or 0)
    return f"{n:,} تومان"


# ── کارت‌ها و خلاصه‌های CRM ─────────────────────────────────────────────────

def _balance_qs():
    T = CustomerTransaction
    return Customer.objects.annotate(
        _p=Coalesce(Sum("transactions__amount", filter=Q(transactions__kind=T.KIND_PURCHASE)), 0),
        _pay=Coalesce(Sum("transactions__amount", filter=Q(transactions__kind=T.KIND_PAYMENT)), 0),
        _adj=Coalesce(Sum("transactions__amount", filter=Q(transactions__kind=T.KIND_ADJUSTMENT)), 0),
    ).annotate(_bal=F("_p") - F("_pay") + F("_adj"))


def build_daily_digest():
    """خلاصهٔ روزانه: سرنخ‌های جدیدِ امروز، پیگیری‌های سررسیده/امروز، و بدهکارها. (title, lines)"""
    now = timezone.localtime()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    new_today = Customer.objects.filter(created_at__gte=today_start).count()
    open_follow = (
        CustomerActivity.objects.select_related("customer")
        .filter(follow_up_at__isnull=False, follow_up_done=False, follow_up_at__lt=today_end)
        .order_by("follow_up_at")
    )
    debtors = _balance_qs().filter(_bal__gt=0).count()

    lines = [f"🆕 سرنخِ جدیدِ امروز: {new_today}", f"⏰ پیگیریِ سررسیده/امروز: {open_follow.count()}"]
    for a in open_follow[:8]:
        when = timezone.localtime(a.follow_up_at).strftime("%H:%M")
        lines.append(f"• {a.customer.name} ({a.customer.phone}) — {when}")
    lines.append(f"💰 مشتریِ بدهکار: {debtors}")
    return "📋 خلاصهٔ امروزِ کاوکس", lines


def _today_text():
    title, lines = build_daily_digest()
    return title + "\n" + "\n".join(lines)


def _customer_card_text(phone):
    norm = normalize_phone(phone)
    if not norm:
        return "شماره نامعتبر است. مثال: /سرنخ 09120000000"
    customer = _balance_qs().filter(phone=norm).first()
    if not customer:
        return f"مشتری‌ای با شمارهٔ {norm} پیدا نشد."
    last = customer.activities.order_by("-occurred_at").first()
    parts = [
        f"👤 {customer.name}",
        f"📞 {customer.phone}",
    ]
    if customer.company:
        parts.append(f"🏢 {customer.company}")
    parts.append(f"مرحله: {customer.get_stage_display()} | منبع: {customer.get_source_display()}")
    bal = customer._bal or 0
    parts.append("مانده: " + ("تسویه" if bal == 0 else (f"بدهکار {_toman(bal)}" if bal > 0 else f"بستانکار {_toman(-bal)}")))
    if last and last.body:
        parts.append(f"آخرین تعامل: {last.body[:80]}")
    return "\n".join(parts)


def _debtors_text():
    rows = _balance_qs().filter(_bal__gt=0).order_by("-_bal")[:10]
    if not rows:
        return "هیچ مشتریِ بدهکاری نداریم. 👌"
    lines = ["💰 بدهکارها (تا ۱۰ نفر):"]
    for c in rows:
        lines.append(f"• {c.name} ({c.phone}) — {_toman(c._bal)}")
    return "\n".join(lines)


# ── ربات قیمت (کاربران) ─────────────────────────────────────────────────────

def _price_text(query, cfg):
    try:
        from assistant.tools import search_products
    except Exception:  # noqa: BLE001
        return "جستجوی محصول در دسترس نیست."
    found = search_products(query=query, max_results=3)
    products = found.get("products") or []
    if not products:
        return "محصولی با این مشخصات پیدا نشد. لطفاً دقیق‌تر بنویسید (نوع، گرید، ضخامت)."
    base = (cfg.site_base_url or "https://kavex.ir").rstrip("/")
    lines = ["🔎 نتایج:"]
    for p in products:
        price = p.get("price_toman")
        price_txt = f"{int(price):,} تومان" if price else "نیازمندِ استعلام"
        lines.append(f"\n• {p.get('title')}\n  قیمت: {price_txt}\n  {base}{p.get('url')}")
    lines.append("\nقیمت‌ها بدونِ ارزش افزوده‌اند. برای ثبتِ سفارش/استعلام در سایت اقدام کنید.")
    return "\n".join(lines)


# ── دکمه‌های عملیاتی (callback) ──────────────────────────────────────────────

def _lead_buttons(customer_id):
    return {
        "inline_keyboard": [[
            {"text": "✅ تماس گرفتم", "callback_data": f"crm:called:{customer_id}"},
            {"text": "⏰ پیگیری فردا", "callback_data": f"crm:fup:{customer_id}"},
            {"text": "🤝 مشتری شد", "callback_data": f"crm:won:{customer_id}"},
        ]]
    }


def _apply_callback(action, customer, actor_name):
    """عملِ دکمه را روی CRM اعمال می‌کند و یک توضیحِ کوتاه برمی‌گرداند."""
    if action == "called":
        CustomerActivity.objects.create(
            customer=customer, kind=CustomerActivity.KIND_CALL,
            body=f"تماس گرفته شد (از بله، {actor_name}).",
        )
        return f"✅ «تماس گرفتم» برای {customer.name} ثبت شد."
    if action == "fup":
        when = (timezone.localtime() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        CustomerActivity.objects.create(
            customer=customer, kind=CustomerActivity.KIND_NOTE,
            body=f"پیگیری زمان‌بندی شد (از بله، {actor_name}).",
            follow_up_at=when, follow_up_note="پیگیری از بله",
        )
        return f"⏰ پیگیریِ فردا ۹ صبح برای {customer.name} ثبت شد."
    if action == "won":
        old = customer.stage
        if customer.stage != Customer.STAGE_WON:
            customer.stage = Customer.STAGE_WON
            customer.save(update_fields=["stage", "updated_at"])
            labels = dict(Customer.STAGE_CHOICES)
            CustomerActivity.objects.create(
                customer=customer, kind=CustomerActivity.KIND_STAGE,
                body=f"مرحله: {labels.get(old, old)} ← {labels.get(Customer.STAGE_WON)} (از بله)",
                stage_from=old, stage_to=Customer.STAGE_WON,
            )
        return f"🤝 {customer.name} «مشتری فعال» شد."
    return "عملِ نامشخص."


# ── مسیریابِ اصلی ───────────────────────────────────────────────────────────

def handle_update(update):
    """ورودیِ یک Update از وب‌هوکِ بله. هیچ‌وقت raise نمی‌کند."""
    try:
        cfg = _cfg()
        if not cfg.bale_webhook_enabled:
            return
        if "callback_query" in update:
            _handle_callback(update["callback_query"], cfg)
        elif "message" in update:
            _handle_message(update["message"], cfg)
    except Exception:  # noqa: BLE001
        logger.exception("bale handle_update failed")


def _handle_callback(cb, cfg):
    from .providers import telegram

    data = str(cb.get("data") or "")
    cb_id = cb.get("id")
    message = cb.get("message") or {}
    chat = message.get("chat") or {}
    from_user = cb.get("from") or {}
    actor_name = (from_user.get("first_name") or from_user.get("username") or "ادمین").strip()

    # فقط ادمین‌ها (یا اعضای گروهِ تنظیم‌شده) اجازهٔ تغییرِ CRM دارند.
    if not cfg.is_admin_sender(chat.get("id"), from_user.get("id")):
        telegram.answer_callback_query(cfg.telegram_bot_token, cb_id, "اجازه ندارید.", base_url=cfg.telegram_api_base)
        return

    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "crm":
        telegram.answer_callback_query(cfg.telegram_bot_token, cb_id, "", base_url=cfg.telegram_api_base)
        return
    _, action, cid = parts
    customer = Customer.objects.filter(pk=cid).first()
    if not customer:
        telegram.answer_callback_query(cfg.telegram_bot_token, cb_id, "مشتری پیدا نشد.", base_url=cfg.telegram_api_base)
        return

    note = _apply_callback(action, customer, actor_name)
    telegram.answer_callback_query(cfg.telegram_bot_token, cb_id, "ثبت شد ✅", base_url=cfg.telegram_api_base)
    _reply(cfg, chat.get("id"), note)


def _handle_message(message, cfg):
    text = (message.get("text") or "").strip()
    if not text:
        return
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    chat_id = chat.get("id")
    is_admin = cfg.is_admin_sender(chat_id, from_user.get("id"))

    if text.startswith("/"):
        token = text[1:].split()[0].split("@")[0]
        arg = text[len("/" + token):].strip()
        if token in ("start", "help", "شروع", "راهنما"):
            _reply(cfg, chat_id, WELCOME_ADMIN if is_admin else WELCOME_PUBLIC)
            return
        if is_admin and token in ("today", "امروز"):
            _reply(cfg, chat_id, _today_text())
            return
        if is_admin and token in ("lead", "سرنخ", "مشتری"):
            _reply(cfg, chat_id, _customer_card_text(arg))
            return
        if is_admin and token in ("debtors", "بدهکاران", "بدهکار"):
            _reply(cfg, chat_id, _debtors_text())
            return
        # دستورِ ناشناخته → راهنما
        _reply(cfg, chat_id, WELCOME_ADMIN if is_admin else WELCOME_PUBLIC)
        return

    # متنِ آزاد ⇒ ربات قیمت (برای همه)
    _reply(cfg, chat_id, _price_text(text, cfg))
