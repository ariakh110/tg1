from django.core.management.base import BaseCommand, CommandError
from products.tasks import refresh_market
from products.external_markets import MarketSyncError

class Command(BaseCommand):
    help = 'Manually receive an official steel-board snapshot with the shared lease.'
    def handle(self, *args, **options):
        try:
            self.stdout.write(str(refresh_market('ime_live', force=True)))
        except MarketSyncError as exc:
            raise CommandError(str(exc)) from exc
