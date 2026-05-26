from decimal import Decimal

from django.db import migrations


def backfill_legacy_price_basis(apps, schema_editor):
    PricingTier = apps.get_model("products", "PricingTier")
    # 0013 added price_basis with default="ton", so existing daily steel prices
    # like 140000 were marked as per-ton even though they were entered per-kg.
    # A real per-ton steel price in this project should be far above this range.
    PricingTier.objects.filter(
        price_basis="ton",
        unit_price__lt=Decimal("10000000"),
    ).update(price_basis="kg")


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0014_alter_pricingtier_price_basis"),
    ]

    operations = [
        migrations.RunPython(backfill_legacy_price_basis, migrations.RunPython.noop),
    ]
