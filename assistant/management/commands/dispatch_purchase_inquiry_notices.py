import logging

from django.core.management.base import BaseCommand
from assistant.inquiry_notices import dispatch_inquiry_notices


class Command(BaseCommand):
    help = "Dispatch private purchase inquiry notifications and CRM due reminders."

    def handle(self, *args, **options):
        from customers.bale_reminders import dispatch_crm_bale_reminders

        try:
            count = dispatch_crm_bale_reminders()
            self.stdout.write(f"Processed {count} CRM due reminders.")
        except Exception:
            # Reminder failures should not prevent the existing inquiry outbox from running.
            logging.getLogger(__name__).exception("CRM due reminder dispatch failed.")
        count = dispatch_inquiry_notices()
        self.stdout.write(f"Processed {count} notice records.")
