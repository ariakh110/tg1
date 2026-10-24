from datetime import timedelta
from celery import shared_task
from django.db.models import Q
from django.utils import timezone
from core.models import SiteSettings
from .models import MarketDataSyncState

from .external_markets import MarketSyncError, sync_global_metals, sync_ime_market


def refresh_market(key, *, force=False):
    """Use one expiring database lease across beat, timer and admin requests."""
    config = SiteSettings.load()
    ime = key == 'ime'
    enabled = config.ime_auto_refresh if ime else config.global_metals_auto_refresh
    if not force and (not enabled or (not ime and not config.global_metals_enabled)):
        return {'skipped': 'manual_mode'}
    if not ime and not config.global_metals_enabled:
        raise MarketSyncError('ابتدا دریافت بازار جهانی را فعال کنید.')
    interval = timedelta(minutes=config.ime_refresh_minutes) if ime else timedelta(hours=config.global_metals_refresh_hours)
    now = timezone.now()
    state, _ = MarketDataSyncState.objects.get_or_create(key=key)
    candidates = MarketDataSyncState.objects.filter(pk=state.pk).filter(Q(lease_until__isnull=True) | Q(lease_until__lte=now))
    if not force:
        candidates = candidates.filter(Q(started_at__isnull=True) | Q(started_at__lte=now - interval))
    if not candidates.update(lease_until=now + timedelta(minutes=5), started_at=now, status='running', error_message=''):
        return {'skipped': 'busy_or_not_due'}
    try:
        count = sync_ime_market() if ime else sync_global_metals(force=True)
        state.refresh_from_db()
        if state.status == 'error':
            raise MarketSyncError(state.error_message)
        finished = timezone.now()
        MarketDataSyncState.objects.filter(pk=state.pk).update(status='success', finished_at=finished, last_success_at=finished, record_count=count)
        return {'synchronized': count}
    except Exception as exc:
        message = str(exc) if isinstance(exc, MarketSyncError) else 'دریافت داده بازار ناموفق بود؛ گزارش سرور را بررسی کنید.'
        MarketDataSyncState.objects.filter(pk=state.pk).update(status='error', finished_at=timezone.now(), error_message=message[:2000])
        raise MarketSyncError(message) from exc
    finally:
        MarketDataSyncState.objects.filter(pk=state.pk).update(lease_until=None)


@shared_task(name="products.tasks.sync_ime_market")
def sync_ime_market_task():
    return refresh_market('ime')


@shared_task(name="products.tasks.sync_global_metals")
def sync_global_metals_task():
    return refresh_market('metals_dev')
