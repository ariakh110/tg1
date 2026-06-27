from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from .models import (
    FeaturedLoad,
    FeaturedLoadAlert,
    FeaturedLoadAlertChannel,
    FeaturedLoadAlertMatch,
    FeaturedLoadAlertStatus,
)


def _alert_matches_load(alert, load):
    keyword = alert.keyword.strip().lower()
    if not keyword:
        return False
    haystack = " ".join(
        filter(None, [load.title, load.specification, load.description, load.quality_grade])
    ).lower()
    if keyword not in haystack:
        return False
    origin = alert.origin.strip().lower()
    if origin and origin not in (load.origin or "").lower():
        return False
    return True


def _send_alert_match_email(alert, load):
    recipient = (alert.user.email or "").strip()
    match = FeaturedLoadAlertMatch.objects.create(
        alert=alert,
        load=load,
        channel=FeaturedLoadAlertChannel.EMAIL,
        status=FeaturedLoadAlertStatus.PENDING,
    )
    if not recipient:
        match.status = FeaturedLoadAlertStatus.SKIPPED
        match.error_message = "user_email_is_empty"
        match.save(update_fields=["status", "error_message"])
        return match

    frontend_base = getattr(settings, "FRONTEND_BASE", "http://localhost:3000").rstrip("/")
    lines = [
        f"سلام {alert.user.get_full_name() or alert.user.username}،",
        "",
        f"باری مطابق با معیار هشدار شما («{alert.keyword}») در بارانداز ویژه‌ی کاوکس اعلام شد:",
        "",
        f"عنوان: {load.title}",
    ]
    if load.specification:
        lines.append(f"مشخصات: {load.specification}")
    if load.origin:
        lines.append(f"مبدا بارگیری: {load.origin}")
    if load.price:
        lines.append(f"قیمت: {load.price}")
    lines += [
        "",
        f"برای مشاهده‌ی جزئیات و تماس به این نشانی مراجعه کنید: {frontend_base}/barandaz",
    ]
    message = "\n".join(lines)

    try:
        send_mail(
            f"بار مطابق هشدار شما در بارانداز ویژه: {load.title}",
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
    except Exception as exc:  # SMTP failure must not break the matching loop.
        match.status = FeaturedLoadAlertStatus.FAILED
        match.error_message = str(exc)[:1000]
        match.save(update_fields=["status", "error_message"])
        return match

    match.status = FeaturedLoadAlertStatus.SENT
    match.save(update_fields=["status"])
    return match


@shared_task
def match_featured_load_alerts(load_id):
    try:
        load = FeaturedLoad.objects.get(pk=load_id, is_active=True)
    except FeaturedLoad.DoesNotExist:
        return {"matched": 0}

    already_notified = set(
        FeaturedLoadAlertMatch.objects.filter(load=load).values_list("alert_id", flat=True)
    )
    matched = 0
    alerts = FeaturedLoadAlert.objects.filter(is_active=True).select_related("user")
    for alert in alerts.iterator():
        if alert.id in already_notified:
            continue
        if not _alert_matches_load(alert, load):
            continue
        _send_alert_match_email(alert, load)
        matched += 1
    return {"matched": matched}
