from django import template

from accounts.models import KYCRequest, KYCStatus

register = template.Library()


@register.simple_tag
def pending_kyc_count():
    try:
        return KYCRequest.objects.filter(status=KYCStatus.PENDING).count()
    except Exception:
        return 0
