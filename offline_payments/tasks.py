from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import OfflinePayment, OfflinePaymentNotification, OfflinePaymentStatus
from .services import ACTIVE_STATUSES, audit, expire_if_due, notify


@shared_task
def check_payment_deadlines():
    now = timezone.now()
    payments = OfflinePayment.objects.filter(
        status__in=ACTIVE_STATUSES,
        payment_deadline__lt=now,
    ).exclude(status=OfflinePaymentStatus.LOCKED)
    expired = 0
    for payment in payments.iterator():
        previous_status = payment.status
        expire_if_due(payment, now)
        if previous_status != payment.status:
            expired += 1
    return {"expired": expired}


@shared_task
def send_payment_deadline_reminders():
    now = timezone.now()
    reminder_until = now + timedelta(hours=2)
    payments = OfflinePayment.objects.filter(
        status__in=ACTIVE_STATUSES,
        payment_deadline__gt=now,
        payment_deadline__lte=reminder_until,
    ).exclude(status=OfflinePaymentStatus.LOCKED)
    sent = 0
    for payment in payments.iterator():
        dedupe_key = f"payment_reminder:{payment.id}"
        if OfflinePaymentNotification.objects.filter(payment=payment, dedupe_key=dedupe_key).exists():
            continue
        _, created = notify(payment, "payment_reminder", dedupe_key=dedupe_key, return_created=True)
        if not created:
            continue
        audit(payment, "PAYMENT_REMINDER_SENT", payload={"deadline": payment.payment_deadline.isoformat()})
        sent += 1
    return {"reminded": sent}
