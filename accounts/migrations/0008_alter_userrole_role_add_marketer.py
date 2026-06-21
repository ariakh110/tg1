from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_alter_userrole_role_add_carrier"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userrole",
            name="role",
            field=models.CharField(
                choices=[
                    ("BUYER", "Buyer"),
                    ("SELLER", "Seller"),
                    ("WAREHOUSE_MANAGER", "Warehouse Manager"),
                    ("CUTTER", "Cutter"),
                    ("DRIVER", "Driver"),
                    ("CARRIER", "Carrier"),
                    ("QC", "Quality Control"),
                    ("STRUCTURAL_DESIGNER", "Structural Designer"),
                    ("ADMIN", "Admin"),
                    ("MARKETER", "Marketer"),
                ],
                max_length=32,
            ),
        ),
    ]
