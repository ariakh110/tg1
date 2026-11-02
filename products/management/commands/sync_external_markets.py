from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from products.models import MarketDataSyncState
from products.tasks import refresh_market
from products.external_markets import MarketSyncError


class Command(BaseCommand):
    help = 'Check both market schedules using admin intervals and database leases.'

    def handle(self, *args, **options):
        errors = []
        for key in ('ime', 'ime_live', 'metals_dev'):
            try:
                self.stdout.write(f'{key}: {refresh_market(key)}')
            except MarketSyncError as exc:
                errors.append(f'{key}: {exc}')
        finished = timezone.now()
        heartbeat = {'status':'error' if errors else 'success', 'finished_at':finished,
                     'error_message':'دریافت یک یا چند بازار ناموفق بود.' if errors else ''}
        if not errors:
            heartbeat['last_success_at'] = finished
        MarketDataSyncState.objects.update_or_create(key='market_scheduler', defaults=heartbeat)
        if errors:
            raise CommandError('; '.join(errors))
