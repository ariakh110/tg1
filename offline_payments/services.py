import json
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import serializers

from orders.models import OrderStatus
from sales.models import (
    StoreOrderStatus,
    StoreOrderStatusHistory,
    StorePayment,
    StorePaymentStatus,
)
from sales.services import (
    PAYMENT_ACTIONABLE_STATUSES,
    is_order_price_expired,
    remaining_amount_for_order,
    set_order_status,
)

from .models import (
    NotificationStatus,
    OfflinePayment,
    OfflinePaymentAuditLog,
    OfflinePaymentNotification,
    OfflinePaymentReceipt,
    OfflinePaymentStatus,
    ReceiptAttemptStatus,
    SatnaBankAccount,
    SatnaBankAccountAuditLog,
)


ACTIVE_STATUSES = {
    OfflinePaymentStatus.PENDING_RECEIPT,
    OfflinePaymentStatus.PENDING_REVIEW,
    OfflinePaymentStatus.REJECTED,
    OfflinePaymentStatus.LOCKED,
}
UPLOADABLE_STATUSES = {
    OfflinePaymentStatus.PENDING_RECEIPT,
    OfflinePaymentStatus.PENDING_REVIEW,
    OfflinePaymentStatus.REJECTED,
}
MIN_AMOUNT = 1_000_000_000
TEHRAN_TZ = ZoneInfo("Asia/Tehran")


def _configured_bank_accounts():
    raw = getattr(settings, "OFFLINE_PAYMENT_BANK_ACCOUNTS_JSON", "[]")
    try:
        rows = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, json.JSONDecodeError):
        rows = []
    return [
        {
            "id": str(row.get("id", "")).strip(),
            "bank_name": str(row.get("bank_name", "")).strip(),
            "iban": str(row.get("iban", "")).strip(),
            "account_holder": str(row.get("account_holder", "")).strip(),
            "account_number": str(row.get("account_number", "")).strip(),
        }
        for row in rows
        if isinstance(row, dict) and str(row.get("id", "")).strip()
    ]


def _bank_account_payload(account):
    return {
        "id": account.code,
        "bank_name": account.bank_name,
        "iban": account.iban,
        "account_holder": account.account_holder,
        "account_number": account.account_number,
    }


def bank_accounts():
    database_accounts = SatnaBankAccount.objects.filter(is_active=True)
    if database_accounts.exists():
        return [_bank_account_payload(account) for account in database_accounts]
    return _configured_bank_accounts()


def bank_account_by_id(account_id):
    account = SatnaBankAccount.objects.filter(code=account_id).first()
    if account:
        return _bank_account_payload(account)
    return next((row for row in _configured_bank_accounts() if row["id"] == account_id), None)


def primary_bank_account():
    database_account = SatnaBankAccount.objects.filter(is_active=True).order_by("-is_primary", "created_at").first()
    if database_account:
        return _bank_account_payload(database_account)
    primary_id = getattr(settings, "OFFLINE_PAYMENT_PRIMARY_IBAN_ID", "IBAN_01")
    account = next((row for row in _configured_bank_accounts() if row["id"] == primary_id), None)
    if not account or not account["iban"] or not account["bank_name"] or not account["account_holder"]:
        raise serializers.ValidationError(
            {"detail": "اطلاعات حساب مقصد ساتنا تنظیم نشده است. با پشتیبانی تماس بگیرید."}
        )
    return account


def payment_deadline(days=1, now=None):
    local_now = (now or timezone.now()).astimezone(TEHRAN_TZ)
    due_date = (local_now + timedelta(days=max(int(days or 1), 1))).date()
    return datetime.combine(due_date, time(hour=10), tzinfo=TEHRAN_TZ)


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",", 1)[0] if forwarded else request.META.get("REMOTE_ADDR")) or None


def audit_bank_account(account, action, actor=None, request=None, payload=None):
    return SatnaBankAccountAuditLog.objects.create(
        account=account,
        action=action,
        actor_user=actor if getattr(actor, "is_authenticated", False) else None,
        ip_address=client_ip(request) if request else None,
        payload=payload or {},
    )


def audit(payment, action, actor=None, request=None, payload=None):
    return OfflinePaymentAuditLog.objects.create(
        payment=payment,
        action=action,
        actor_user=actor if getattr(actor, "is_authenticated", False) else None,
        ip_address=client_ip(request) if request else None,
        payload=payload or {},
    )


def notify(payment, event, dedupe_key="", return_created=False):
    recipient = (payment.user.email or "").strip()
    notification_defaults = {
        "event": event,
        "recipient": recipient,
        "status": NotificationStatus.PENDING,
    }
    if dedupe_key:
        notification, created = OfflinePaymentNotification.objects.get_or_create(
            payment=payment,
            dedupe_key=dedupe_key,
            defaults=notification_defaults,
        )
        if not created:
            return (notification, False) if return_created else notification
    else:
        notification = OfflinePaymentNotification.objects.create(
            payment=payment,
            dedupe_key="",
            **notification_defaults,
        )
    if not recipient:
        notification.status = NotificationStatus.SKIPPED
        notification.error_message = "user_email_is_empty"
        notification.save(update_fields=["status", "error_message"])
        return (notification, True) if return_created else notification
    subject = {
        "receipt_uploaded": "فیش ساتنا دریافت شد",
        "receipt_approved": "پرداخت ساتنا تایید شد",
        "receipt_rejected": "فیش ساتنا رد شد",
        "payment_locked": "بارگذاری فیش ساتنا قفل شد",
        "payment_unlocked": "بارگذاری فیش ساتنا فعال شد",
        "payment_reminder": "یادآوری مهلت پرداخت ساتنا",
        "payment_expired": "مهلت پرداخت ساتنا منقضی شد",
    }.get(event, "بروزرسانی پرداخت ساتنا")
    try:
        send_mail(
            subject,
            f"وضعیت پرداخت ساتنا: {payment.get_status_display()}\n{payment.admin_note}".strip(),
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
    except Exception as exc:  # SMTP failure must not roll back financial actions.
        notification.status = NotificationStatus.FAILED
        notification.error_message = str(exc)[:1000]
        notification.save(update_fields=["status", "error_message"])
        return (notification, True) if return_created else notification
    notification.status = NotificationStatus.SENT
    notification.save(update_fields=["status"])
    return (notification, True) if return_created else notification


def expire_if_due(payment, now=None):
    if payment.status not in ACTIVE_STATUSES or payment.status == OfflinePaymentStatus.LOCKED:
        return payment
    current_time = now or timezone.now()
    if payment.payment_deadline >= current_time:
        return payment
    updated = (
        OfflinePayment.objects.filter(
            pk=payment.pk,
            status__in=ACTIVE_STATUSES,
            payment_deadline__lt=current_time,
        )
        .exclude(status=OfflinePaymentStatus.LOCKED)
        .update(status=OfflinePaymentStatus.EXPIRED, updated_at=current_time)
    )
    if not updated:
        payment.refresh_from_db(fields=["status", "updated_at"])
        return payment
    payment.status = OfflinePaymentStatus.EXPIRED
    payment.updated_at = current_time
    audit(payment, "PAYMENT_EXPIRED", payload={"deadline": payment.payment_deadline.isoformat()})
    notify(payment, "payment_expired", dedupe_key=f"payment_expired:{payment.id}")
    return payment


def _validate_amount(amount):
    if amount < MIN_AMOUNT:
        raise serializers.ValidationError(
            {"detail": f"مبلغ پرداخت ساتنا باید حداقل {MIN_AMOUNT:,} تومان باشد."}
        )


def receipt_amounts(payment):
    amounts = payment.receipts.aggregate(
        approved=Sum("amount", filter=Q(status=ReceiptAttemptStatus.APPROVED)),
        pending=Sum("amount", filter=Q(status=ReceiptAttemptStatus.PENDING)),
    )
    approved = int(amounts["approved"] or 0)
    pending = int(amounts["pending"] or 0)
    return {
        "approved": approved,
        "pending": pending,
        "remaining": max(int(payment.amount) - approved, 0),
        "available_to_upload": max(int(payment.amount) - approved - pending, 0),
    }


def _existing_active(**source):
    candidates = OfflinePayment.objects.filter(status__in=ACTIVE_STATUSES, **source).order_by("-created_at")
    for payment in candidates:
        expire_if_due(payment)
        if payment.status in ACTIVE_STATUSES:
            return payment
    return None


@transaction.atomic
def initiate_store_order_payment(order, actor, request=None):
    if order.buyer_id != actor.id:
        raise serializers.ValidationError({"detail": "فقط خریدار سفارش می‌تواند پرداخت ساتنا را شروع کند."})
    if order.status not in PAYMENT_ACTIONABLE_STATUSES or order.payment_status == StorePaymentStatus.PAID:
        raise serializers.ValidationError({"detail": "این سفارش در وضعیت قابل پرداخت نیست."})
    if is_order_price_expired(order):
        raise serializers.ValidationError({"detail": "اعتبار قیمت سفارش تمام شده است."})
    existing = _existing_active(store_order=order)
    if existing:
        return existing
    amount = remaining_amount_for_order(order)
    _validate_amount(amount)
    account = primary_bank_account()
    deadline = payment_deadline(order.settlement_term_days)
    payment = OfflinePayment.objects.create(
        store_order=order,
        user=actor,
        amount=amount,
        currency=order.currency,
        payment_deadline=deadline,
        target_iban_id=account["id"],
        target_bank_account_snapshot=account,
    )
    order.payment_due_at = deadline
    order.save(update_fields=["payment_due_at", "updated_at"])
    audit(payment, "PAYMENT_INITIATED", actor, request, {"source_type": "store_order"})
    return payment


@transaction.atomic
def initiate_marketplace_order_payment(order, actor, request=None):
    if order.buyer_id != actor.id:
        raise serializers.ValidationError({"detail": "فقط خریدار سفارش می‌تواند پرداخت ساتنا را شروع کند."})
    if order.status != OrderStatus.OFFER_SELECTED or not order.selected_offer_id:
        raise serializers.ValidationError({"detail": "برای این سفارش هنوز پیشنهاد نهایی انتخاب نشده است."})
    existing = _existing_active(marketplace_order=order)
    if existing:
        return existing
    amount = int(order.price_agreed_amount or 0)
    _validate_amount(amount)
    account = primary_bank_account()
    payment = OfflinePayment.objects.create(
        marketplace_order=order,
        user=actor,
        amount=amount,
        currency=order.price_agreed_currency,
        payment_deadline=payment_deadline(1),
        target_iban_id=account["id"],
        target_bank_account_snapshot=account,
    )
    audit(payment, "PAYMENT_INITIATED", actor, request, {"source_type": "marketplace_order"})
    return payment


def validate_receipt_file(file):
    extension = Path(getattr(file, "name", "")).suffix.lower()
    allowed_extensions = {".jpg", ".jpeg", ".png", ".pdf"}
    allowed_mime_types = {"image/jpeg", "image/png", "application/pdf"}
    if extension not in allowed_extensions:
        raise serializers.ValidationError({"receipt_file": "فقط فایل JPG، PNG یا PDF مجاز است."})
    if file.size > int(getattr(settings, "OFFLINE_PAYMENT_RECEIPT_MAX_SIZE_MB", 5)) * 1024 * 1024:
        raise serializers.ValidationError({"receipt_file": "حجم فایل فیش نباید بیشتر از ۵ مگابایت باشد."})
    content_type = getattr(file, "content_type", "")
    if content_type and content_type not in allowed_mime_types:
        raise serializers.ValidationError({"receipt_file": "نوع فایل فیش معتبر نیست."})


@transaction.atomic
def upload_receipt(payment, actor, file, amount, reference_number, note="", request=None):
    payment = OfflinePayment.objects.select_for_update().get(pk=payment.pk)
    expire_if_due(payment)
    if payment.user_id != actor.id:
        raise serializers.ValidationError({"detail": "این پرداخت متعلق به شما نیست."})
    if payment.status == OfflinePaymentStatus.LOCKED:
        raise serializers.ValidationError({"detail": "بارگذاری فیش قفل شده است. با پشتیبانی تماس بگیرید."})
    if payment.status not in UPLOADABLE_STATUSES:
        raise serializers.ValidationError({"detail": "در وضعیت فعلی امکان بارگذاری فیش وجود ندارد."})
    try:
        amount = int(amount)
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError({"amount": "مبلغ فیش باید یک عدد صحیح به تومان باشد."}) from exc
    if amount <= 0:
        raise serializers.ValidationError({"amount": "مبلغ فیش باید بیشتر از صفر باشد."})
    amounts = receipt_amounts(payment)
    if amount > amounts["available_to_upload"]:
        raise serializers.ValidationError(
            {"amount": f"مبلغ فیش نباید بیشتر از مانده قابل ثبت ({amounts['available_to_upload']:,} تومان) باشد."}
        )
    reference_number = str(reference_number or "").strip()
    if not reference_number.isdigit() or len(reference_number) > 30:
        raise serializers.ValidationError({"reference_number": "شماره مرجع ساتنا باید فقط شامل عدد و حداکثر ۳۰ رقم باشد."})
    validate_receipt_file(file)
    one_hour_ago = timezone.now() - timedelta(hours=1)
    upload_limit = int(getattr(settings, "OFFLINE_PAYMENT_RECEIPT_UPLOAD_LIMIT_PER_HOUR", 5))
    if OfflinePaymentReceipt.objects.filter(payment__user=actor, created_at__gte=one_hour_ago).count() >= upload_limit:
        raise serializers.ValidationError({"detail": f"حداکثر {upload_limit} بارگذاری فیش در یک ساعت مجاز است."})
    receipt = OfflinePaymentReceipt.objects.create(
        payment=payment,
        file=file,
        amount=amount,
        reference_number=reference_number,
        note=str(note or "").strip(),
    )
    payment.status = OfflinePaymentStatus.PENDING_REVIEW
    payment.admin_note = ""
    payment.save(update_fields=["status", "admin_note", "updated_at"])
    audit(payment, "RECEIPT_UPLOADED", actor, request, {"receipt_id": receipt.id, "amount": amount})
    notify(payment, "receipt_uploaded")
    return payment


def _approve_store_receipt(payment, receipt, actor):
    order = payment.store_order
    provider_reference = f"satna:{payment.id}:{receipt.id}"
    store_payment, created = StorePayment.objects.get_or_create(
        provider_reference=provider_reference,
        defaults={
            "order": order,
            "amount": receipt.amount,
            "currency": order.currency,
            "status": StorePaymentStatus.PAID,
            "provider": "satna_offline",
            "raw_payload": {"offline_payment_id": str(payment.id), "receipt_id": receipt.id},
        },
    )
    if not created:
        return store_payment
    if remaining_amount_for_order(order) <= 0:
        order.payment_status = StorePaymentStatus.PAID
        order.save(update_fields=["payment_status", "updated_at"])
        set_order_status(
            order,
            StoreOrderStatus.PAID,
            "STORE_ORDER_PAYMENT_CONFIRMED",
            actor,
            meta={"payment_id": store_payment.id, "offline_payment_id": str(payment.id), "receipt_id": receipt.id},
        )
    else:
        order.payment_status = StorePaymentStatus.PENDING
        order.save(update_fields=["payment_status", "updated_at"])
        StoreOrderStatusHistory.objects.create(
            order=order,
            from_status=order.status,
            to_status=order.status,
            event="STORE_ORDER_PARTIAL_PAYMENT_CONFIRMED",
            actor_user=actor,
            meta={
                "payment_id": store_payment.id,
                "offline_payment_id": str(payment.id),
                "receipt_id": receipt.id,
                "amount": receipt.amount,
                "remaining_amount": remaining_amount_for_order(order),
            },
        )
    return store_payment


def _payment_status_for_amounts(payment, amounts):
    if amounts["remaining"] <= 0:
        return OfflinePaymentStatus.APPROVED
    if payment.rejection_count >= 3:
        return OfflinePaymentStatus.LOCKED
    if amounts["pending"] > 0:
        return OfflinePaymentStatus.PENDING_REVIEW
    if payment.rejection_count > 0:
        return OfflinePaymentStatus.REJECTED
    return OfflinePaymentStatus.PENDING_RECEIPT


def _reverse_store_receipt(payment, receipt, actor, note):
    order = payment.store_order
    provider_reference = f"satna:{payment.id}:{receipt.id}"
    store_payment = StorePayment.objects.filter(provider_reference=provider_reference).first()
    if store_payment and store_payment.status == StorePaymentStatus.PAID:
        payload = dict(store_payment.raw_payload or {})
        payload["reversal"] = {
            "offline_payment_id": str(payment.id),
            "receipt_id": receipt.id,
            "admin_note": note,
            "reversed_at": timezone.now().isoformat(),
        }
        store_payment.status = StorePaymentStatus.REFUNDED
        store_payment.raw_payload = payload
        store_payment.save(update_fields=["status", "raw_payload", "updated_at"])

    previous_status = order.status
    remaining = remaining_amount_for_order(order)
    order.payment_status = StorePaymentStatus.PAID if remaining <= 0 else StorePaymentStatus.PENDING
    if remaining > 0 and order.status == StoreOrderStatus.PAID:
        order.status = StoreOrderStatus.PAYMENT_PENDING
    order.save(update_fields=["payment_status", "status", "updated_at"])
    StoreOrderStatusHistory.objects.create(
        order=order,
        from_status=previous_status,
        to_status=order.status,
        event="STORE_ORDER_SATNA_RECEIPT_REVERSED",
        actor_user=actor,
        meta={
            "payment_id": store_payment.id if store_payment else None,
            "offline_payment_id": str(payment.id),
            "receipt_id": receipt.id,
            "amount": receipt.amount,
            "remaining_amount": remaining,
            "admin_note": note,
        },
    )
    return store_payment


@transaction.atomic
def review_payment(payment, actor, decision, admin_note="", receipt_id=None, request=None):
    payment = OfflinePayment.objects.select_for_update().get(pk=payment.pk)
    expire_if_due(payment)
    if payment.status not in {OfflinePaymentStatus.PENDING_REVIEW, OfflinePaymentStatus.LOCKED}:
        raise serializers.ValidationError({"detail": "فقط فیش در انتظار بررسی قابل تایید یا رد است."})
    receipts = payment.receipts.filter(status=ReceiptAttemptStatus.PENDING)
    receipt = receipts.filter(pk=receipt_id).first() if receipt_id else receipts.first()
    if not receipt:
        raise serializers.ValidationError({"detail": "فیشی برای بررسی وجود ندارد."})
    now = timezone.now()
    note = str(admin_note or "").strip()
    if decision == "approve":
        receipt.status = ReceiptAttemptStatus.APPROVED
        receipt.admin_note = note
        receipt.reviewed_by = actor
        receipt.reviewed_at = now
        receipt.save(update_fields=["status", "admin_note", "reviewed_by", "reviewed_at"])
        if payment.store_order_id:
            _approve_store_receipt(payment, receipt, actor)
        amounts = receipt_amounts(payment)
        if amounts["remaining"] <= 0:
            payment.status = OfflinePaymentStatus.APPROVED
        elif payment.rejection_count >= 3:
            payment.status = OfflinePaymentStatus.LOCKED
        elif amounts["pending"] > 0:
            payment.status = OfflinePaymentStatus.PENDING_REVIEW
        else:
            payment.status = OfflinePaymentStatus.PENDING_RECEIPT
        event = "RECEIPT_APPROVED"
        notification_event = "receipt_approved"
    elif decision == "reject":
        if not note:
            raise serializers.ValidationError({"admin_note": "دلیل رد فیش الزامی است."})
        receipt.status = ReceiptAttemptStatus.REJECTED
        receipt.admin_note = note
        receipt.reviewed_by = actor
        receipt.reviewed_at = now
        receipt.save(update_fields=["status", "admin_note", "reviewed_by", "reviewed_at"])
        payment.rejection_count += 1
        amounts = receipt_amounts(payment)
        if payment.rejection_count >= 3:
            payment.status = OfflinePaymentStatus.LOCKED
        elif amounts["pending"] > 0:
            payment.status = OfflinePaymentStatus.PENDING_REVIEW
        else:
            payment.status = OfflinePaymentStatus.REJECTED
        event = "PAYMENT_LOCKED" if payment.status == OfflinePaymentStatus.LOCKED else "RECEIPT_REJECTED"
        notification_event = "payment_locked" if payment.status == OfflinePaymentStatus.LOCKED else "receipt_rejected"
    else:
        raise serializers.ValidationError({"decision": "تصمیم بررسی باید approve یا reject باشد."})
    payment.admin_note = note
    payment.reviewed_by = actor
    payment.reviewed_at = now
    payment.save(
        update_fields=["status", "rejection_count", "admin_note", "reviewed_by", "reviewed_at", "updated_at"]
    )
    amounts = receipt_amounts(payment)
    audit(
        payment,
        event,
        actor,
        request,
        {
            "receipt_id": receipt.id,
            "amount": receipt.amount,
            "admin_note": note,
            "approved_amount": amounts["approved"],
            "remaining_amount": amounts["remaining"],
        },
    )
    notify(payment, notification_event)
    return payment


@transaction.atomic
def reverse_receipt_approval(payment, actor, receipt_id, admin_note="", request=None):
    note = str(admin_note or "").strip()
    if not note:
        raise serializers.ValidationError({"admin_note": "دلیل برگشت تایید فیش الزامی است."})
    payment = OfflinePayment.objects.select_for_update().get(pk=payment.pk)
    receipt = payment.receipts.select_for_update().filter(
        pk=receipt_id,
        status=ReceiptAttemptStatus.APPROVED,
    ).first()
    if not receipt:
        raise serializers.ValidationError({"detail": "فقط فیش تاییدشده قابل برگشت است."})

    store_payment = None
    if payment.store_order_id:
        store_payment = _reverse_store_receipt(payment, receipt, actor, note)

    now = timezone.now()
    receipt.status = ReceiptAttemptStatus.REVERSED
    receipt.admin_note = note
    receipt.reviewed_by = actor
    receipt.reviewed_at = now
    receipt.save(update_fields=["status", "admin_note", "reviewed_by", "reviewed_at"])

    amounts = receipt_amounts(payment)
    payment.status = _payment_status_for_amounts(payment, amounts)
    payment.admin_note = note
    payment.reviewed_by = actor
    payment.reviewed_at = now
    payment.save(update_fields=["status", "admin_note", "reviewed_by", "reviewed_at", "updated_at"])
    audit(
        payment,
        "RECEIPT_APPROVAL_REVERSED",
        actor,
        request,
        {
            "receipt_id": receipt.id,
            "amount": receipt.amount,
            "admin_note": note,
            "store_payment_id": store_payment.id if store_payment else None,
            "approved_amount": amounts["approved"],
            "remaining_amount": amounts["remaining"],
        },
    )
    return payment


@transaction.atomic
def unlock_payment(payment, actor, admin_note="", request=None):
    payment = OfflinePayment.objects.select_for_update().get(pk=payment.pk)
    if payment.status != OfflinePaymentStatus.LOCKED:
        raise serializers.ValidationError({"detail": "فقط پرداخت قفل‌شده قابل بازکردن است."})
    payment.status = (
        OfflinePaymentStatus.PENDING_REVIEW
        if payment.receipts.filter(status=ReceiptAttemptStatus.PENDING).exists()
        else OfflinePaymentStatus.REJECTED
    )
    payment.rejection_count = 0
    payment.admin_note = str(admin_note or "").strip()
    payment.save(update_fields=["status", "rejection_count", "admin_note", "updated_at"])
    audit(payment, "PAYMENT_UNLOCKED", actor, request, {"admin_note": payment.admin_note})
    notify(payment, "payment_unlocked")
    return payment


def _report_datetime(value, *, end_of_day=False):
    value = str(value or "").strip()
    if not value:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        parsed_date = parse_date(value)
        if parsed_date:
            parsed = datetime.combine(parsed_date, time.max if end_of_day else time.min)
    if parsed is None:
        raise serializers.ValidationError({"date": "Invalid report date."})
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, TEHRAN_TZ)
    return parsed


def _payment_source_title(payment):
    if payment.store_order_id:
        first_item = payment.store_order.items.first()
        return first_item.product_name if first_item else f"Store order {payment.store_order_id}"
    return payment.marketplace_order.title if payment.marketplace_order_id else ""


def _financial_report_row(receipt):
    payment = receipt.payment
    account = payment.target_bank_account_snapshot or bank_account_by_id(payment.target_iban_id) or {}
    approved_at = receipt.reviewed_at or receipt.created_at
    return {
        "receipt_id": receipt.id,
        "payment_id": str(payment.id),
        "source_type": payment.source_type,
        "source_id": str(payment.source_id),
        "source_title": _payment_source_title(payment),
        "buyer_id": payment.user_id,
        "buyer_username": payment.user.username,
        "buyer_email": payment.user.email,
        "payment_status": payment.status,
        "payment_amount": payment.amount,
        "receipt_amount": receipt.amount,
        "currency": payment.currency,
        "reference_number": receipt.reference_number,
        "approved_at": approved_at.isoformat() if approved_at else None,
        "payment_created_at": payment.created_at.isoformat() if payment.created_at else None,
        "bank_account_id": payment.target_iban_id,
        "bank_name": account.get("bank_name", ""),
        "iban": account.get("iban", ""),
        "account_holder": account.get("account_holder", ""),
    }


def satna_financial_report(query_params):
    receipts = (
        OfflinePaymentReceipt.objects.filter(status=ReceiptAttemptStatus.APPROVED)
        .select_related(
            "payment",
            "payment__user",
            "payment__store_order",
            "payment__marketplace_order",
            "reviewed_by",
        )
        .prefetch_related("payment__store_order__items")
        .order_by("-reviewed_at", "-created_at", "-id")
    )

    date_from = _report_datetime(
        query_params.get("date_from") or query_params.get("approved_from"),
        end_of_day=False,
    )
    date_to = _report_datetime(
        query_params.get("date_to") or query_params.get("approved_to"),
        end_of_day=True,
    )
    if date_from:
        receipts = receipts.filter(reviewed_at__gte=date_from)
    if date_to:
        receipts = receipts.filter(reviewed_at__lte=date_to)

    source_type = str(query_params.get("source_type") or "").strip()
    if source_type:
        if source_type not in {"store_order", "marketplace_order"}:
            raise serializers.ValidationError({"source_type": "Invalid source type."})
        if source_type == "store_order":
            receipts = receipts.filter(payment__store_order__isnull=False)
        else:
            receipts = receipts.filter(payment__marketplace_order__isnull=False)

    bank_account_id = str(query_params.get("bank_account_id") or "").strip()
    if bank_account_id:
        receipts = receipts.filter(payment__target_iban_id=bank_account_id)

    search = str(query_params.get("q") or "").strip()
    if search:
        receipts = receipts.filter(
            Q(reference_number__icontains=search)
            | Q(payment__user__username__icontains=search)
            | Q(payment__user__email__icontains=search)
            | Q(payment__store_order__contact_name__icontains=search)
            | Q(payment__store_order__contact_phone__icontains=search)
            | Q(payment__store_order__items__product_name__icontains=search)
            | Q(payment__marketplace_order__title__icontains=search)
        ).distinct()

    totals = receipts.aggregate(
        approved_receipt_count=Count("id"),
        approved_payment_count=Count("payment", distinct=True),
        total_approved_amount=Sum("amount"),
        direct_approved_amount=Sum("amount", filter=Q(payment__store_order__isnull=False)),
        marketplace_approved_amount=Sum("amount", filter=Q(payment__marketplace_order__isnull=False)),
    )
    rows = [_financial_report_row(receipt) for receipt in receipts]
    return {
        "filters": {
            "date_from": date_from.isoformat() if date_from else "",
            "date_to": date_to.isoformat() if date_to else "",
            "source_type": source_type,
            "bank_account_id": bank_account_id,
            "q": search,
        },
        "summary": {
            "approved_receipt_count": int(totals["approved_receipt_count"] or 0),
            "approved_payment_count": int(totals["approved_payment_count"] or 0),
            "total_approved_amount": int(totals["total_approved_amount"] or 0),
            "direct_approved_amount": int(totals["direct_approved_amount"] or 0),
            "marketplace_approved_amount": int(totals["marketplace_approved_amount"] or 0),
        },
        "rows": rows,
    }
