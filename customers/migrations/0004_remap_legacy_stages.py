# نگاشتِ کدهای قدیمیِ مرحله به قیفِ B2B جدید.
from django.db import migrations

# قدیمی → جدید
STAGE_MAP = {
    "lead": "new",
    "contacted": "nurturing",
    "active": "won",
    "dormant": "won",
    # "lost" بدون تغییر
}


def remap_forward(apps, schema_editor):
    Customer = apps.get_model("customers", "Customer")
    for old, new in STAGE_MAP.items():
        Customer.objects.filter(stage=old).update(stage=new)


def remap_backward(apps, schema_editor):
    # کدهای قدیمی حذف شده‌اند؛ بازگشت no-op است.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("customers", "0003_customeractivity_stage_from_and_more"),
    ]

    operations = [
        migrations.RunPython(remap_forward, remap_backward),
    ]
