"""Non-blocking website event intake for the opportunity funnel."""

import hashlib
import json
import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from assistant.models import AssistantInquiry
from sales.models import StoreOrder

from .models import CrmOpportunity, CrmSyncEvent, Customer
from .opportunities import process_sync_event

logger = logging.getLogger(__name__)


def _enqueue(source_type, source_id, updated_at, payload=None):
    timestamp = updated_at.isoformat() if updated_at else "unknown"
    fingerprint_payload = {"updated_at": timestamp, **(payload or {})}
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:24]
    event_key = f"sync:{source_type}:{source_id}:{fingerprint}"
    sync_event, _created = CrmSyncEvent.objects.get_or_create(
        event_key=event_key,
        defaults={
            "source_type": source_type,
            "source_id": str(source_id),
            "payload": payload or {},
        },
    )
    if sync_event.status != CrmSyncEvent.STATUS_PROCESSED:
        process_sync_event(sync_event)


def _safe_enqueue(source_type, source_id, updated_at, payload=None):
    try:
        _enqueue(source_type, source_id, updated_at, payload=payload)
    except Exception:  # noqa: BLE001
        logger.exception("Could not enqueue CRM synchronization for %s:%s", source_type, source_id)


def _safe_enqueue_new_customer(customer_id):
    try:
        customer = Customer.objects.filter(pk=customer_id).first()
        if not customer:
            return
        from .automation import enqueue_automation_event
        from .models import CrmAutomationRun

        enqueue_automation_event(
            event_key=f"customer.created:{customer.pk}",
            trigger=CrmAutomationRun.TRIGGER_CUSTOMER_CREATED,
            customer=customer,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Could not enqueue initial CRM task for customer %s", customer_id)


@receiver(post_save, sender=Customer, dispatch_uid="customers.crm_customer_initial_task")
def create_initial_customer_task(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        customer_id = instance.pk
        transaction.on_commit(lambda: _safe_enqueue_new_customer(customer_id))


@receiver(post_save, sender=StoreOrder, dispatch_uid="customers.sync_store_order_opportunity")
def sync_store_order_after_commit(sender, instance, **kwargs):
    source_id = str(instance.pk)
    updated_at = instance.updated_at
    payload = {
        "status": instance.status,
        "payment_status": instance.payment_status,
        "quote_confirmation_status": instance.quote_confirmation_status,
        "total_amount": instance.total_amount,
        "contact_phone": instance.contact_phone,
        "contact_name": instance.contact_name,
        "destination_city": instance.destination_city,
    }
    transaction.on_commit(
        lambda: _safe_enqueue(
            CrmOpportunity.SOURCE_STORE_ORDER,
            source_id,
            updated_at,
            payload=payload,
        )
    )


@receiver(post_save, sender=AssistantInquiry, dispatch_uid="customers.sync_assistant_inquiry_opportunity")
def sync_assistant_inquiry_after_commit(sender, instance, **kwargs):
    source_id = str(instance.pk)
    updated_at = instance.updated_at
    payload = {
        "status": instance.status,
        "product": instance.product,
        "size": instance.size,
        "grade": instance.grade,
        "factory": instance.factory,
        "quantity": instance.quantity,
        "city": instance.city,
        "matched_price": instance.matched_price,
        "contact_phone": instance.contact_phone,
    }
    transaction.on_commit(
        lambda: _safe_enqueue(
            CrmOpportunity.SOURCE_ASSISTANT_INQUIRY,
            source_id,
            updated_at,
            payload=payload,
        )
    )
