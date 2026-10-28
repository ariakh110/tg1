from django.core.management.base import BaseCommand
from assistant.inquiry_notices import dispatch_inquiry_notices


class Command(BaseCommand):
    help = "Dispatch claimed private purchase inquiry notifications."

    def handle(self, *args, **options):
        count = dispatch_inquiry_notices()
        self.stdout.write(f"Processed {count} notice records.")
