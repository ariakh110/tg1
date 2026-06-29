"""ارکستراسیونِ رویدادهای «ورودِ سرنخ + اطلاع‌رسانیِ ادمین».

این توابع از مسیرِ درخواستِ کاربر (ثبت‌نام/چت) یا از سیگنالِ سفارش صدا زده می‌شوند و
«امن» هستند: هر خطایی را می‌بلعند و لاگ می‌کنند تا هیچ‌وقت جریانِ اصلیِ سایت نشکند.
هر رویداد دو کار می‌کند: (۱) مشتری را در CRM upsert می‌کند، (۲) به ادمین خبر می‌دهد.
"""
import logging

from customers.models import Customer
from customers.services import upsert_lead

logger = logging.getLogger(__name__)


def _profile_phone(user):
    profile = getattr(user, "profile", None)
    return (getattr(profile, "phone", "") or "") if profile else ""


def _display_name(user):
    if not user:
        return ""
    full = (user.get_full_name() or "").strip()
    return full or user.get_username()


def on_user_signup(user, phone="", *, source=Customer.SOURCE_WEBSITE):
    """کاربرِ تازه ثبت‌نام‌کرده → سرنخِ CRM (در صورتِ وجودِ شماره) + خبر به ادمین."""
    try:
        from . import service
        from .models import MessagingSettings

        cfg = MessagingSettings.load()
        phone = (phone or _profile_phone(user)).strip()
        name = _display_name(user)
        customer, _created = upsert_lead(
            phone, name=name, source=source, user=user,
            activity_body="از طریقِ ثبت‌نام در سایت اضافه شد.",
        )
        if cfg.notify_on_signup:
            lines = []
            if name and name != user.get_username():
                lines.append(f"نام: {name}")
            lines.append(f"نام کاربری: {user.get_username()}")
            if phone:
                lines.append(f"موبایل: {phone}")
            if getattr(user, "email", ""):
                lines.append(f"ایمیل: {user.email}")
            if not phone:
                lines.append("(بدون شماره — در CRM ثبت نشد)")
            service.notify_admin("👤 ثبت‌نام جدید در سایت", lines, customer=customer)
        return customer
    except Exception:  # noqa: BLE001
        logger.exception("on_user_signup failed")
        return None


def on_order_submitted(order):
    """سفارشِ ثبت‌شده توسطِ کاربر → سرنخ/مشتریِ CRM + خبر به ادمین."""
    try:
        from . import service
        from .models import MessagingSettings

        cfg = MessagingSettings.load()
        buyer = getattr(order, "buyer", None)
        phone = (getattr(order, "contact_phone", "") or "").strip() or _profile_phone(buyer)
        name = (getattr(order, "contact_name", "") or "").strip() or _display_name(buyer)
        customer, _created = upsert_lead(
            phone, name=name, source=Customer.SOURCE_STORE_PURCHASE,
            user=buyer if getattr(buyer, "pk", None) else None,
            activity_body=f"سفارش روی سایت ثبت کرد (#{str(order.pk)[:8]}).",
        )
        if cfg.notify_on_order:
            lines = []
            if name:
                lines.append(f"نام: {name}")
            if phone:
                lines.append(f"موبایل: {phone}")
            amount = getattr(order, "total_amount", 0) or 0
            if amount:
                lines.append(f"مبلغ: {int(amount):,} ریال")
            try:
                items = list(order.items.all()[:3])
                if items:
                    lines.append("اقلام: " + "، ".join(i.product_name for i in items))
            except Exception:  # noqa: BLE001
                pass
            lines.append(f"شناسهٔ سفارش: {str(order.pk)[:8]}")
            service.notify_admin("🛒 سفارش جدید در سایت", lines, customer=customer)
        return customer
    except Exception:  # noqa: BLE001
        logger.exception("on_order_submitted failed")
        return None


def on_chat_lead(conversation, *, interest=""):
    """سرنخِ ثبت‌شده در چتِ فروش → مشتریِ CRM + خبر به ادمین (فقط اگر شماره باشد)."""
    try:
        from . import service
        from .models import MessagingSettings

        phone = (getattr(conversation, "lead_phone", "") or "").strip()
        if not phone:
            return None
        cfg = MessagingSettings.load()
        name = (getattr(conversation, "lead_name", "") or "").strip()
        interest = (interest or getattr(conversation, "lead_interest", "") or "").strip()
        customer, _created = upsert_lead(
            phone, name=name, source=Customer.SOURCE_CHAT,
            user=getattr(conversation, "user", None),
            note=interest,
            activity_body="سرنخ از چتِ فروش" + (f" — {interest}" if interest else "") + ".",
        )
        if cfg.notify_on_chat_lead:
            lines = []
            if name:
                lines.append(f"نام: {name}")
            lines.append(f"موبایل: {phone}")
            if interest:
                lines.append(f"نیاز: {interest}")
            service.notify_admin("💬 سرنخ از چتِ فروش", lines, customer=customer)
        return customer
    except Exception:  # noqa: BLE001
        logger.exception("on_chat_lead failed")
        return None
