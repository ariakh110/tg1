from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0019_seed_t006_10mm_content"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="productimage",
            options={"ordering": ("-is_featured", "id")},
        ),
    ]
