from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import PricingTier
from .market import capture_product_price_snapshots


@receiver(post_save, sender=PricingTier)
def capture_saved_pricing_tier(sender, instance, raw=False, **kwargs):
    if not raw:
        capture_product_price_snapshots(instance.offer.product_id)


@receiver(post_delete, sender=PricingTier)
def capture_deleted_pricing_tier(sender, instance, **kwargs):
    capture_product_price_snapshots(instance.offer.product_id)
