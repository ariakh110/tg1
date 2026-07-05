import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import FeaturedLoad
from .tasks import match_featured_load_alerts

logger = logging.getLogger(__name__)


@receiver(post_save, sender=FeaturedLoad)
def queue_featured_load_alert_matching(sender, instance, **kwargs):
    if not instance.is_active:
        return

    def _queue():
        try:
            match_featured_load_alerts.delay(instance.id)
        except Exception:
            # در دسترس‌نبودنِ بروکر (Redis) نباید ذخیرهٔ بارِ ویژه را ۵۰۰ کند؛
            # فقط ارسالِ هشدارِ ایمیلیِ این بار از دست می‌رود.
            logger.warning("queueing featured-load alert matching failed for load %s", instance.id, exc_info=True)

    transaction.on_commit(_queue)
