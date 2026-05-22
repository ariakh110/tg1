from django.db import migrations
from django.db.models import F, Max


def upsert_option(ProductAttributeOption, *, group, value, label, product_kind="", parent=None, sort_order=0):
    ProductAttributeOption.objects.update_or_create(
        group=group,
        value=value,
        parent=parent,
        defaults={
            "label": label,
            "product_kind": product_kind,
            "sort_order": sort_order,
            "is_active": True,
        },
    )


def ensure_sheet_child_category(ProductCategory, sheet, *, code, name, surface_finish, sort_order):
    defaults = {
        "name": name,
        "parent": sheet,
        "product_kind": "sheet",
        "spec_defaults": {"material_type": "sheet", "surface_finish": surface_finish},
        "required_spec_fields": ["steel_grade", "thickness_mm", "width_mm"],
        "sort_order": sort_order,
        "is_active": True,
    }
    category = ProductCategory.objects.filter(code=code).first()
    if category:
        for field, value in defaults.items():
            setattr(category, field, value)
        category.save(update_fields=list(defaults.keys()))
        return category

    insert_at = sheet.rght
    ProductCategory.objects.filter(tree_id=sheet.tree_id, rght__gte=insert_at).update(rght=F("rght") + 2)
    ProductCategory.objects.filter(tree_id=sheet.tree_id, lft__gt=insert_at).update(lft=F("lft") + 2)
    category = ProductCategory.objects.create(
        code=code,
        tree_id=sheet.tree_id,
        lft=insert_at,
        rght=insert_at + 1,
        level=sheet.level + 1,
        **defaults,
    )
    sheet.rght += 2
    return category


def ensure_root_category(ProductCategory, *, code, name, product_kind, required_spec_fields, sort_order):
    defaults = {
        "name": name,
        "parent": None,
        "product_kind": product_kind,
        "spec_defaults": {"material_type": product_kind},
        "required_spec_fields": required_spec_fields,
        "sort_order": sort_order,
        "is_active": True,
    }
    category = ProductCategory.objects.filter(code=code).first()
    if category:
        for field, value in defaults.items():
            setattr(category, field, value)
        category.save(update_fields=list(defaults.keys()))
        return category

    next_tree_id = (ProductCategory.objects.aggregate(max_tree_id=Max("tree_id"))["max_tree_id"] or 0) + 1
    return ProductCategory.objects.create(
        code=code,
        tree_id=next_tree_id,
        lft=1,
        rght=2,
        level=0,
        **defaults,
    )


def seed_grade_dependencies(apps, schema_editor):
    ProductCategory = apps.get_model("products", "ProductCategory")
    ProductAttributeOption = apps.get_model("products", "ProductAttributeOption")

    sheet = ProductCategory.objects.filter(code="sheet").first()
    if sheet:
        ensure_sheet_child_category(
            ProductCategory,
            sheet,
            code="sheet-acid-washed",
            name="ورق اسیدشویی",
            surface_finish="acid_washed",
            sort_order=35,
        )
        ensure_sheet_child_category(
            ProductCategory,
            sheet,
            code="sheet-stainless",
            name="ورق استیل",
            surface_finish="stainless",
            sort_order=60,
        )

    ensure_root_category(
        ProductCategory,
        code="billet",
        name="شمش",
        product_kind="billet",
        required_spec_fields=["steel_grade"],
        sort_order=60,
    )

    surface_options = {
        option.value: option
        for option in ProductAttributeOption.objects.filter(group="surface_finish", product_kind="sheet")
    }
    grade_map = {
        "black": ["ST37"],
        "acid_washed": ["ST37"],
        "oiled": ["ST12", "ST13", "ST14"],
        "alloy": ["ST52", "CK45", "A516", "A283"],
        "galvanized": ["DX51D"],
        "color": ["DX51D"],
        "stainless": ["304", "316"],
    }
    for surface_value, grades in grade_map.items():
        parent = surface_options.get(surface_value)
        if not parent:
            continue
        for sort_order, grade in enumerate(grades, start=1):
            upsert_option(
                ProductAttributeOption,
                group="steel_grade",
                value=grade,
                label=grade,
                product_kind="sheet",
                parent=parent,
                sort_order=sort_order,
            )

    for sort_order, grade in enumerate(["3SP", "5SP"], start=1):
        upsert_option(
            ProductAttributeOption,
            group="steel_grade",
            value=grade,
            label=grade,
            product_kind="billet",
            sort_order=sort_order,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0011_seed_sheet_acid_washed_category"),
    ]

    operations = [
        migrations.RunPython(seed_grade_dependencies, migrations.RunPython.noop),
    ]
