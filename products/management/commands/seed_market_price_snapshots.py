from django.core.management.base import BaseCommand
from django.db.models import Q

from products.market import capture_product_price_snapshots
from products.models import Product


class Command(BaseCommand):
    help = "Create today's baseline market snapshots from current active catalog prices."

    def handle(self, *args, **options):
        product_ids = (
            Product.objects.filter(
                is_active=True,
                offers__is_active=True,
                offers__pricing_tiers__unit_price__gt=0,
            )
            .filter(Q(offers__pricing_tiers__price_basis__isnull=False))
            .values_list("id", flat=True)
            .distinct()
        )
        snapshots = 0
        products = 0
        for product_id in product_ids.iterator():
            products += 1
            snapshots += len(capture_product_price_snapshots(product_id))
        self.stdout.write(self.style.SUCCESS(f"Seeded {snapshots} daily snapshots for {products} products."))
