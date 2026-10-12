from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("blog", "0011_canonicalize_robots_sitemap"),
    ]

    operations = [
        migrations.AddField(
            model_name="landing",
            name="expert_extension",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="landing",
            name="expert_image",
            field=models.ImageField(blank=True, null=True, upload_to="landings/experts/"),
        ),
        migrations.AddField(
            model_name="landing",
            name="expert_mobile",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="landing",
            name="expert_name",
            field=models.CharField(blank=True, default="", max_length=160),
        ),
        migrations.AddField(
            model_name="landing",
            name="expert_role",
            field=models.CharField(blank=True, default="", max_length=160),
        ),
    ]
