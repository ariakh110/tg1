"""خلاصهٔ روزانهٔ CRM را به کانال‌های اطلاع‌رسانیِ ادمین (بله/گروه + پیامک) می‌فرستد.

روی سرور با cron اجرا کن، مثلاً هر روز ۸ صبح:
    0 8 * * *  cd /opt/tirexa/backend && python manage.py bale_daily_digest
"""
from django.core.management.base import BaseCommand

from messaging import service
from messaging.bale_bot import build_daily_digest


class Command(BaseCommand):
    help = "ارسالِ خلاصهٔ روزانهٔ CRM به ادمین/گروه از طریقِ بله و پیامک."

    def handle(self, *args, **options):
        title, lines = build_daily_digest()
        messages = service.notify_admin(title, lines)
        statuses = ", ".join(f"{m.get_channel_display()}:{m.status}" for m in messages)
        self.stdout.write(self.style.SUCCESS(f"digest sent ({statuses or 'no channel'})"))
