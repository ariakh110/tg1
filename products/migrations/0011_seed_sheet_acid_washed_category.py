from django.db import migrations
from django.db.models import F


def seed_sheet_acid_washed_category(apps, schema_editor):
    ProductCategory = apps.get_model("products", "ProductCategory")
    sheet = ProductCategory.objects.filter(code="sheet").first()
    if not sheet:
        return

    defaults = {
        "name": "ورق اسیدشویی",
        "parent": sheet,
        "product_kind": "sheet",
        "spec_defaults": {"material_type": "sheet", "surface_finish": "acid_washed"},
        "required_spec_fields": ["steel_grade", "thickness_mm", "width_mm"],
        "sort_order": 35,
        "is_active": True,
    }
    category = ProductCategory.objects.filter(code="sheet-acid-washed").first()
    if category:
        for field, value in defaults.items():
            setattr(category, field, value)
        category.save(update_fields=[*defaults.keys()])
        return

    insert_at = sheet.rght
    ProductCategory.objects.filter(tree_id=sheet.tree_id, rght__gte=insert_at).update(rght=F("rght") + 2)
    ProductCategory.objects.filter(tree_id=sheet.tree_id, lft__gt=insert_at).update(lft=F("lft") + 2)
    ProductCategory.objects.create(
        code="sheet-acid-washed",
        tree_id=sheet.tree_id,
        lft=insert_at,
        rght=insert_at + 1,
        level=sheet.level + 1,
        **defaults,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0010_product_availability_status_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_sheet_acid_washed_category, migrations.RunPython.noop),
    ]
