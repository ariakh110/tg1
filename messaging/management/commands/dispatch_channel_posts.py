from django.core.management.base import BaseCommand
from messaging.channel_posts import dispatch_due
class Command(BaseCommand):
    help = "Dispatch due recurring channel posts (no automatic uncertain retries)"
    def handle(self,*args,**options):
        self.stdout.write(str(dispatch_due()))
