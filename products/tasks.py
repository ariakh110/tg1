from celery import shared_task

from .external_markets import sync_global_metals, sync_ime_market


@shared_task(name="products.tasks.sync_ime_market")
def sync_ime_market_task():
    return sync_ime_market()


@shared_task(name="products.tasks.sync_global_metals")
def sync_global_metals_task():
    return sync_global_metals()
