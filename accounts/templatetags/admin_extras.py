from django import template

from accounts.models import KYCRequest, KYCStatus
from orders.models import OrderRequest, OrderRequestStatus, OrderRequestType

register = template.Library()


@register.simple_tag
def pending_kyc_count():
    try:
        return KYCRequest.objects.filter(status=KYCStatus.PENDING).count()
    except Exception:
        return 0


@register.simple_tag
def pending_warehouse_request_count():
    try:
        return OrderRequest.all_objects.filter(
            type=OrderRequestType.SELL,
            status=OrderRequestStatus.PENDING_WAREHOUSE,
            is_active=True,
        ).count()
    except Exception:
        return 0
