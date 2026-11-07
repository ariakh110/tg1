"""Small, explicit and retryable CRM automation whitelist."""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import RoleCode

from .models import CrmAutomationRun, CrmFollowUp, CrmOpportunity, CrmTask, Customer

logger = logging.getLogger(__name__)


def _single_active_sales_owner():
    """Assign work only when the active sales operator is unambiguous."""
    user_model = get_user_model()
    candidates = list(
        user_model.objects.filter(is_active=True)
        .filter(
            Q(is_staff=True)
            | Q(is_superuser=True)
            | Q(roles__is_active=True, roles__role__in=[RoleCode.ADMIN, RoleCode.MARKETER])
        )
        .distinct()[:2]
    )
    return candidates[0] if len(candidates) == 1 else None


def enqueue_automation_event(*, event_key, trigger, customer=None, opportunity=None, actor=None):
    """Persist a whitelisted event once, then process it without affecting its source transaction."""
    allowed = {code for code, _label in CrmAutomationRun.TRIGGER_CHOICES}
    if trigger not in allowed:
        raise ValueError(f"unsupported_crm_automation_trigger:{trigger}")
    event_key = str(event_key or "").strip()[:180]
    if not event_key:
        raise ValueError("crm_automation_event_key_required")

    defaults = {
        "trigger": trigger,
        "customer": customer,
        "opportunity": opportunity,
        "payload": {},
    }
    run, created = CrmAutomationRun.objects.get_or_create(event_key=event_key, defaults=defaults)
    if created or run.status == CrmAutomationRun.STATUS_PENDING:
        process_automation_run(run)
    return run


def process_automation_run(run_or_id):
    """Execute one event atomically; a failed run remains visible and can be explicitly retried."""
    run_id = run_or_id.pk if isinstance(run_or_id, CrmAutomationRun) else run_or_id
    try:
        with transaction.atomic():
            run = CrmAutomationRun.objects.select_for_update().get(pk=run_id)
            if run.status == CrmAutomationRun.STATUS_SUCCEEDED:
                return run
            run.status = CrmAutomationRun.STATUS_PROCESSING
            run.attempts += 1
            run.last_error = ""
            run.save(update_fields=["status", "attempts", "last_error", "updated_at"])

        with transaction.atomic():
            run = CrmAutomationRun.objects.select_for_update().select_related(
                "customer", "opportunity", "opportunity__owner"
            ).get(pk=run_id)
            if run.status == CrmAutomationRun.STATUS_SUCCEEDED:
                return run
            owner = run.opportunity.owner if run.opportunity_id and run.opportunity.owner_id else None
            owner = owner or _single_active_sales_owner()
            if run.trigger == CrmAutomationRun.TRIGGER_CUSTOMER_CREATED:
                customer = run.customer
                if customer:
                    CrmTask.objects.get_or_create(
                        idempotency_key=f"{run.event_key}:initial-contact"[:180],
                        defaults={
                            "customer": customer,
                            "owner": owner,
                            "title": "تماس اولیه با سرنخ جدید",
                            "description": "نیاز مشتری را بررسی و نتیجه تماس را در تایم‌لاین ثبت کنید.",
                            "trigger": run.trigger,
                        },
                    )
            elif run.trigger == CrmAutomationRun.TRIGGER_OPPORTUNITY_STAGE_CHANGED:
                opportunity = run.opportunity
                if opportunity:
                    if opportunity.stage in CrmOpportunity.CLOSED_STAGES:
                        CrmTask.objects.filter(
                            opportunity=opportunity, status=CrmTask.STATUS_OPEN
                        ).update(status=CrmTask.STATUS_CANCELLED, updated_at=timezone.now())
                        CrmFollowUp.objects.filter(
                            opportunity=opportunity, status=CrmFollowUp.STATUS_PENDING
                        ).update(status=CrmFollowUp.STATUS_CANCELLED, updated_at=timezone.now())
                    else:
                        next_action = (opportunity.next_action or "").strip()
                        title = next_action or f"پیگیری فرصت: {opportunity.title}"
                        CrmTask.objects.get_or_create(
                            idempotency_key=f"{run.event_key}:stage-follow-up"[:180],
                            defaults={
                                "customer": opportunity.customer,
                                "opportunity": opportunity,
                                "source_order_id": opportunity.source_id
                                if opportunity.source_type == CrmOpportunity.SOURCE_STORE_ORDER
                                else "",
                                "owner": owner,
                                "title": title[:240],
                                "description": f"مرحله فعلی فرصت: {opportunity.get_stage_display()}",
                                "trigger": run.trigger,
                                "due_at": opportunity.next_follow_up_at,
                            },
                        )
            else:
                raise ValueError(f"unsupported_crm_automation_trigger:{run.trigger}")

            run.status = CrmAutomationRun.STATUS_SUCCEEDED
            run.last_error = ""
            run.processed_at = timezone.now()
            run.save(update_fields=["status", "last_error", "processed_at", "updated_at"])
            return run
    except Exception as exc:  # noqa: BLE001 - persist failures for the CRM retry queue.
        logger.exception("CRM automation failed for event %s", run_id)
        CrmAutomationRun.objects.filter(pk=run_id).update(
            status=CrmAutomationRun.STATUS_FAILED,
            last_error=str(exc)[:4000],
            processed_at=None,
            updated_at=timezone.now(),
        )
        return CrmAutomationRun.objects.get(pk=run_id)
