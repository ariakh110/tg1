from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('products','0027_steel_shapes_history')]
    operations = [migrations.AddField(model_name='marketdatasyncstate',name='lease_token',field=models.CharField(max_length=36,blank=True,default=''))]
