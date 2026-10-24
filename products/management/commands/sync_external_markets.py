from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from products.models import MarketDataSyncState
from products.tasks import refresh_market
from products.external_markets import MarketSyncError


class Command(BaseCommand):
    help = 'Check both market schedules using admin intervals and database leases.'

    def handle(self, *args, **options):
        errors = []
        for key in ('ime', 'metals_dev'):
            try:
                self.stdout.write(f'{key}: {refresh_market(key)}')
            except MarketSyncError as exc:
                errors.append(f'{key}: {exc}')
        MarketDataSyncState.objects.update_or_create(key='market_scheduler', defaults={
            'status': 'success', 'finished_at': timezone.now(), 'last_success_at': timezone.now(),
        })
        if errors:
            raise CommandError('; '.join(errors))
