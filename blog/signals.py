from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import FeaturedLoad
from .tasks import match_featured_load_alerts


@receiver(post_save, sender=FeaturedLoad)
def queue_featured_load_alert_matching(sender, instance, **kwargs):
    if instance.is_active:
        transaction.on_commit(lambda: match_featured_load_alerts.delay(instance.id))
