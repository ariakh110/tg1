"""Execution-local lease identity; all state publication uses conditional writes."""
from contextvars import ContextVar
from .models import MarketDataSyncState

current_lease = ContextVar('market_lease', default=None)


def owned_state(state):
    owner = current_lease.get()
    token = owner[1] if owner and owner[0] == state.key else ''
    return MarketDataSyncState.objects.filter(pk=state.pk, lease_token=token)
