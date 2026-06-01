import json
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
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
)


ACTIVE_STATUSES = {
    OfflinePaymentStatus.PENDING_RECEIPT,
    OfflinePaymentStatus.PENDING_REVIEW,
    OfflinePaymentStatus.REJECTED,
    OfflinePaymentStatus.LOCKED,
}
UPLOADABLE_STATUSES = {
    OfflinePaymentStatus.PENDING_RECEIPT,
    OfflinePaymentStatus.REJECTED,
}
MIN_AMOUNT = 100_000
MAX_AMOUNT = 2_000_000_000
TEHRAN_TZ = ZoneInfo("Asia/Tehran")


def bank_accounts():
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
        }
        for row in rows
        if isinstance(row, dict) and str(row.get("id", "")).strip()
    ]


def primary_bank_account():
    primary_id = getattr(settings, "OFFLINE_PAYMENT_PRIMARY_IBAN_ID", "IBAN_01")
    account = next((row for row in bank_accounts() if row["id"] == primary_id), None)
    if not account or not account["iban"] or not account["bank_name"] or not account["account_holder"]:
        raise serializers.ValidationError({"detail": "offline_payment_bank_account_not_configured"})
    return account


def payment_deadline(days=1, now=None):
    local_now = (now or timezone.now()).astimezone(TEHRAN_TZ)
    due_date = (local_now + timedelta(days=max(int(days or 1), 1))).date()
    return datetime.combine(due_date, time(hour=10), tzinfo=TEHRAN_TZ)


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",", 1)[0] if forwarded else request.META.get("REMOTE_ADDR")) or None


def audit(payment, action, actor=None, request=None, payload=None):
    return OfflinePaymentAuditLog.objects.create(
        payment=payment,
        action=action,
        actor_user=actor if getattr(actor, "is_authenticated", False) else None,
        ip_address=client_ip(request) if request else None,
        payload=payload or {},
    )


def notify(payment, event):
    recipient = (payment.user.email or "").strip()
    if not recipient:
        return OfflinePaymentNotification.objects.create(
            payment=payment,
            event=event,
            recipient="",
            status=NotificationStatus.SKIPPED,
            error_message="user_email_is_empty",
        )
    subject = {
        "receipt_uploaded": "فیش ساتنا دریافت شد",
        "receipt_approved": "پرداخت ساتنا تایید شد",
        "receipt_rejected": "فیش ساتنا رد شد",
        "payment_locked": "بارگذاری فیش ساتنا قفل شد",
        "payment_unlocked": "بارگذاری فیش ساتنا فعال شد",
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
        return OfflinePaymentNotification.objects.create(
            payment=payment,
            event=event,
            recipient=recipient,
            status=NotificationStatus.FAILED,
            error_message=str(exc)[:1000],
        )
    return OfflinePaymentNotification.objects.create(
        payment=payment,
        event=event,
        recipient=recipient,
        status=NotificationStatus.SENT,
    )


def expire_if_due(payment, now=None):
    if payment.status not in ACTIVE_STATUSES or payment.status == OfflinePaymentStatus.LOCKED:
        return payment
    if payment.payment_deadline >= (now or timezone.now()):
        return payment
    payment.status = OfflinePaymentStatus.EXPIRED
    payment.save(update_fields=["status", "updated_at"])
    audit(payment, "PAYMENT_EXPIRED", payload={"deadline": payment.payment_deadline.isoformat()})
    return payment


def _validate_amount(amount):
    if amount < MIN_AMOUNT or amount > MAX_AMOUNT:
        raise serializers.ValidationError(
            {"detail": f"مبلغ پرداخت ساتنا باید بین {MIN_AMOUNT:,} و {MAX_AMOUNT:,} تومان باشد."}
        )


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
def upload_receipt(payment, actor, file, reference_number, note="", request=None):
    payment = OfflinePayment.objects.select_for_update().get(pk=payment.pk)
    expire_if_due(payment)
    if payment.user_id != actor.id:
        raise serializers.ValidationError({"detail": "این پرداخت متعلق به شما نیست."})
    if payment.status == OfflinePaymentStatus.LOCKED:
        raise serializers.ValidationError({"detail": "بارگذاری فیش قفل شده است. با پشتیبانی تماس بگیرید."})
    if payment.status not in UPLOADABLE_STATUSES:
        raise serializers.ValidationError({"detail": "در وضعیت فعلی امکان بارگذاری فیش وجود ندارد."})
    reference_number = str(reference_number or "").strip()
    if not reference_number.isdigit() or len(reference_number) > 30:
        raise serializers.ValidationError({"reference_number": "شماره مرجع ساتنا باید فقط شامل عدد و حداکثر ۳۰ رقم باشد."})
    validate_receipt_file(file)
    one_hour_ago = timezone.now() - timedelta(hours=1)
    if OfflinePaymentReceipt.objects.filter(payment__user=actor, created_at__gte=one_hour_ago).count() >= 5:
        raise serializers.ValidationError({"detail": "حداکثر پنج بارگذاری فیش در یک ساعت مجاز است."})
    receipt = OfflinePaymentReceipt.objects.create(
        payment=payment,
        file=file,
        reference_number=reference_number,
        note=str(note or "").strip(),
    )
    payment.status = OfflinePaymentStatus.PENDING_REVIEW
    payment.admin_note = ""
    payment.save(update_fields=["status", "admin_note", "updated_at"])
    audit(payment, "RECEIPT_UPLOADED", actor, request, {"receipt_id": receipt.id})
    notify(payment, "receipt_uploaded")
    return payment


def _approve_store_payment(payment, actor):
    order = payment.store_order
    provider_reference = f"satna:{payment.id}"
    store_payment, created = StorePayment.objects.get_or_create(
        provider_reference=provider_reference,
        defaults={
            "order": order,
            "amount": payment.amount,
            "currency": order.currency,
            "status": StorePaymentStatus.PAID,
            "provider": "satna_offline",
            "raw_payload": {"offline_payment_id": str(payment.id)},
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
            meta={"payment_id": store_payment.id, "offline_payment_id": str(payment.id)},
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
            meta={"payment_id": store_payment.id, "offline_payment_id": str(payment.id)},
        )
    return store_payment


@transaction.atomic
def review_payment(payment, actor, decision, admin_note="", request=None):
    payment = OfflinePayment.objects.select_for_update().get(pk=payment.pk)
    expire_if_due(payment)
    if payment.status != OfflinePaymentStatus.PENDING_REVIEW:
        raise serializers.ValidationError({"detail": "فقط فیش در انتظار بررسی قابل تایید یا رد است."})
    receipt = payment.receipts.first()
    if not receipt:
        raise serializers.ValidationError({"detail": "فیشی برای بررسی وجود ندارد."})
    now = timezone.now()
    note = str(admin_note or "").strip()
    if decision == "approve":
        receipt.status = ReceiptAttemptStatus.APPROVED
        payment.status = OfflinePaymentStatus.APPROVED
        if payment.store_order_id:
            _approve_store_payment(payment, actor)
        event = "RECEIPT_APPROVED"
        notification_event = "receipt_approved"
    elif decision == "reject":
        if not note:
            raise serializers.ValidationError({"admin_note": "دلیل رد فیش الزامی است."})
        receipt.status = ReceiptAttemptStatus.REJECTED
        payment.rejection_count += 1
        payment.status = (
            OfflinePaymentStatus.LOCKED
            if payment.rejection_count >= 3
            else OfflinePaymentStatus.REJECTED
        )
        event = "PAYMENT_LOCKED" if payment.status == OfflinePaymentStatus.LOCKED else "RECEIPT_REJECTED"
        notification_event = "payment_locked" if payment.status == OfflinePaymentStatus.LOCKED else "receipt_rejected"
    else:
        raise serializers.ValidationError({"decision": "تصمیم بررسی باید approve یا reject باشد."})
    receipt.admin_note = note
    receipt.reviewed_by = actor
    receipt.reviewed_at = now
    receipt.save(update_fields=["status", "admin_note", "reviewed_by", "reviewed_at"])
    payment.admin_note = note
    payment.reviewed_by = actor
    payment.reviewed_at = now
    payment.save(
        update_fields=["status", "rejection_count", "admin_note", "reviewed_by", "reviewed_at", "updated_at"]
    )
    audit(payment, event, actor, request, {"receipt_id": receipt.id, "admin_note": note})
    notify(payment, notification_event)
    return payment


@transaction.atomic
def unlock_payment(payment, actor, admin_note="", request=None):
    payment = OfflinePayment.objects.select_for_update().get(pk=payment.pk)
    if payment.status != OfflinePaymentStatus.LOCKED:
        raise serializers.ValidationError({"detail": "فقط پرداخت قفل‌شده قابل بازکردن است."})
    payment.status = OfflinePaymentStatus.REJECTED
    payment.rejection_count = 0
    payment.admin_note = str(admin_note or "").strip()
    payment.save(update_fields=["status", "rejection_count", "admin_note", "updated_at"])
    audit(payment, "PAYMENT_UNLOCKED", actor, request, {"admin_note": payment.admin_note})
    notify(payment, "payment_unlocked")
    return payment
