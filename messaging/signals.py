"""سیگنال‌های پیام‌رسانی: تشخیصِ «ثبتِ سفارش توسطِ کاربر» و خبردادن به ادمین.

به‌جای پیداکردنِ تک‌تکِ مسیرهای ثبتِ سفارش، روی `StoreOrder` می‌نشینیم و هر گذار به
وضعیتِ SUBMITTED را می‌گیریم؛ این مستقل از مسیرِ کد است و فقط هنگامِ ورود به این وضعیت
یک‌بار شلیک می‌کند. `connect_signals()` از `MessagingConfig.ready()` صدا زده می‌شود.
"""
import logging

logger = logging.getLogger(__name__)


def _track_status(sender, instance, **kwargs):
    """قبل از ذخیره، وضعیتِ فعلیِ دیتابیس را روی نمونه نگه می‌داریم تا گذار را بفهمیم."""
    if instance.pk:
        instance._messaging_old_status = (
            sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
        )
    else:
        instance._messaging_old_status = None


def _on_order_saved(sender, instance, created, **kwargs):
    from sales.models import StoreOrderStatus

    old = getattr(instance, "_messaging_old_status", None)
    if instance.status == StoreOrderStatus.SUBMITTED and old != StoreOrderStatus.SUBMITTED:
        from . import events

        events.on_order_submitted(instance)


def connect_signals():
    """اتصالِ سیگنال‌های `StoreOrder` (اگر اپِ sales موجود باشد)."""
    try:
        from sales.models import StoreOrder
    except Exception:  # noqa: BLE001 — اپِ sales نصب نیست
        return
    from django.db.models.signals import post_save, pre_save

    pre_save.connect(_track_status, sender=StoreOrder, dispatch_uid="messaging_storeorder_track")
    post_save.connect(_on_order_saved, sender=StoreOrder, dispatch_uid="messaging_storeorder_notify")
