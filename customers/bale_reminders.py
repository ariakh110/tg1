"""Dispatch due CRM work to the verified private Bale account of its operator."""

import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Exists, OuterRef
from django.db.models.functions import Coalesce
from django.utils import timezone

from accounts.admin_sections import ALL, effective_admin_sections
from accounts.models import RoleCode
from messaging.models import BaleUserBinding, MessagingSettings
from messaging.providers import telegram

from .models import CrmDueReminder, CrmFollowUp, CrmTask, CustomerActivity

logger = logging.getLogger(__name__)
BALE_URL = "https://tapi.bale.ai"
WORK_TYPES = {
    "task": (CrmTask, "due_at", {"status": CrmTask.STATUS_OPEN}),
    "follow_up": (CrmFollowUp, "due_at", {"status": CrmFollowUp.STATUS_PENDING}),
    "activity": (CustomerActivity, "follow_up_at", {"follow_up_done": False, "crm_follow_up__isnull": True}),
}


def can_receive_crm_bale_reminders(user):
    if not user.is_active:
        return False
    if user.roles.filter(role=RoleCode.CRM_SALES, is_active=True).exists():
        return True
    sections = effective_admin_sections(user)
    return sections == ALL or bool({"crm", "crm-funnel"} & sections)


def _recipient_id(work):
    return getattr(work, "owner_id", None) or (
        work.customer.assigned_to_id if work.customer_id else None
    ) or work.created_by_id


def _candidates(kind, now, recipient_ids, limit):
    model, due_field, open_filter = WORK_TYPES[kind]
    owners = ["customer__assigned_to_id", "created_by_id"]
    if model is not CustomerActivity:
        owners.insert(0, "owner_id")
    previous = CrmDueReminder.objects.filter(
        kind=kind, work_id=OuterRef("pk"), due_at=OuterRef(due_field), recipient_id=OuterRef("reminder_user"),
    )
    return list(
        model.objects.filter(**open_filter, **{f"{due_field}__lte": now})
        .annotate(reminder_user=Coalesce(*owners))
        .filter(reminder_user__in=recipient_ids)
        .filter(~Exists(previous))
        .order_by(due_field, "pk")
        .values_list(due_field, "pk", "reminder_user")[:limit]
    )


def _claim(kind, work_id, due_at, recipient_id):
    model, due_field, open_filter = WORK_TYPES[kind]
    with transaction.atomic():
        work = model.objects.select_for_update().filter(pk=work_id, **{due_field: due_at}).first()
        if not work or _recipient_id(work) != recipient_id:
            return None
        if not model.objects.filter(pk=work_id, **open_filter).exists():
            return None
        binding = BaleUserBinding.objects.select_related("user").filter(user_id=recipient_id, is_active=True).first()
        if not binding or not can_receive_crm_bale_reminders(binding.user):
            return None
        target = binding.bale_user_id
        if not target.isascii() or not target.isdecimal() or int(target) <= 0:
            return None
        reminder, created = CrmDueReminder.objects.get_or_create(
            kind=kind, work_id=work_id, due_at=due_at, recipient_id=recipient_id,
        )
        if not created:
            return None
    title = work.follow_up_note if model is CustomerActivity else work.title
    return reminder, target, title


def dispatch_crm_bale_reminders(*, limit=3):
    cfg = MessagingSettings.load()
    token = (cfg.telegram_bot_token or "").strip()
    if not cfg.telegram_enabled or not token or cfg.telegram_api_base.strip().rstrip("/") != BALE_URL:
        return 0

    now = timezone.now()
    CrmDueReminder.objects.filter(status="sending", created_at__lt=now - timedelta(minutes=10)).update(status="unknown")
    recipients = [
        binding.user_id for binding in BaleUserBinding.objects.select_related("user")
        .filter(is_active=True, user__is_active=True, bale_user_id__regex=r"^[1-9][0-9]*$")
        if can_receive_crm_bale_reminders(binding.user)
    ]
    if not recipients:
        return 0
    candidates = sorted(
        (due_at, kind, work_id, recipient)
        for kind in WORK_TYPES
        for due_at, work_id, recipient in _candidates(kind, now, recipients, limit)
    )

    attempted = 0
    for due_at, kind, work_id, recipient in candidates[:limit]:
        claimed = _claim(kind, work_id, due_at, recipient)
        if not claimed:
            continue
        reminder, chat_id, title = claimed
        label = "کار" if kind == "task" else "پیگیری"
        message = f"🔔 سررسید {label} CRM\n{title or label}\nشمارهٔ {label}: {work_id}"
        try:
            result = telegram.send_message(token, chat_id, message, base_url=BALE_URL)
            sent = bool(result.ok and result.message_id)
        except Exception:
            sent = False
        CrmDueReminder.objects.filter(pk=reminder.pk).update(status="sent" if sent else "unknown")
        if not sent:
            logger.warning("Bale CRM reminder %s did not confirm delivery", reminder.pk)
        attempted += 1
    return attempted
