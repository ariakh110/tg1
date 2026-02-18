from django.contrib import admin

from .models import (
    Order,
    OrderOffer,
    OrderRequest,
    OrderRequestAuditLog,
    OrderRequestDocument,
    OrderRequestNotification,
    OrderRequestStatusHistory,
    OrderStatusHistory,
)

admin.site.register(Order)
admin.site.register(OrderOffer)
admin.site.register(OrderStatusHistory)
admin.site.register(OrderRequest)
admin.site.register(OrderRequestStatusHistory)
admin.site.register(OrderRequestDocument)
admin.site.register(OrderRequestAuditLog)
admin.site.register(OrderRequestNotification)
