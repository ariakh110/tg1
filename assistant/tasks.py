from celery import shared_task


@shared_task
def dispatch_purchase_inquiry_notices():
    from .inquiry_notices import dispatch_inquiry_notices
    return dispatch_inquiry_notices()
