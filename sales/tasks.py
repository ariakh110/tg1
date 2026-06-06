from celery import shared_task

from .services import expire_due_delivery_offers


@shared_task
def expire_delivery_offers():
    return expire_due_delivery_offers()
