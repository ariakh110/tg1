from datetime import time
from django.db import migrations


def seed(apps,schema_editor):
    Schedule=apps.get_model('messaging','ChannelPostSchedule')
    Schedule.objects.create(title='سلام صبح‌بخیر',body='بسم الله الرحمن الرحیم\n\nسلام، صبح بخیر 🌹☀️\nامروز {{weekday}} {{jalali_date}}\n{{site_name}}',send_time=time(8,0),weekdays=list(range(7)),platforms=['bale'],enabled=False)


class Migration(migrations.Migration):
    dependencies=[('messaging','0017_channelpostschedule_channelpostrun')]
    operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
