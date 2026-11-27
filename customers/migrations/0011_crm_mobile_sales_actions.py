import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0010_customer_assigned_to_crmmobilecallpolicy_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="customeractivity",
            name="channel",
            field=models.CharField(
                blank=True,
                choices=[
                    ("phone", "تلفن"),
                    ("whatsapp", "واتساپ"),
                    ("telegram", "تلگرام"),
                    ("bale", "بله"),
                    ("rubika", "روبیکا"),
                    ("other", "سایر"),
                ],
                default="",
                max_length=16,
                verbose_name="کانال ارتباط",
            ),
        ),
        migrations.AddField(
            model_name="customeractivity",
            name="mobile_event_uuid",
            field=models.UUIDField(blank=True, null=True, unique=True, verbose_name="شناسه ثبت موبایل"),
        ),
        migrations.CreateModel(
            name="CrmCustomerMobilePreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_favorite", models.BooleanField(db_index=True, default=False, verbose_name="مشتری ویژه")),
                ("bale_chat_url", models.CharField(blank=True, default="", max_length=500, verbose_name="لینک چت بله")),
                ("rubika_chat_url", models.CharField(blank=True, default="", max_length=500, verbose_name="لینک چت روبیکا")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mobile_preferences", to="customers.customer", verbose_name="مشتری")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="crm_mobile_customer_preferences", to=settings.AUTH_USER_MODEL, verbose_name="کاربر CRM")),
            ],
            options={
                "verbose_name": "ترجیحات CRM موبایل",
                "verbose_name_plural": "ترجیحات CRM موبایل",
                "indexes": [models.Index(fields=["user", "is_favorite"], name="crm_mobile_favorite_idx")],
                "constraints": [models.UniqueConstraint(fields=("user", "customer"), name="uniq_crm_mobile_customer_pref")],
            },
        ),
        migrations.AlterField(
            model_name="crmfollowup",
            name="channel",
            field=models.CharField(
                choices=[
                    ("call", "تماس"),
                    ("sms", "پیامک"),
                    ("whatsapp", "واتساپ"),
                    ("telegram", "تلگرام"),
                    ("bale", "بله"),
                    ("rubika", "روبیکا"),
                    ("meeting", "جلسه"),
                    ("other", "سایر"),
                ],
                default="call",
                max_length=12,
            ),
        ),
    ]
