from django.contrib import admin

from .models import (
    OfflinePayment,
    OfflinePaymentAuditLog,
    OfflinePaymentNotification,
    OfflinePaymentReceipt,
)


admin.site.register(OfflinePayment)
admin.site.register(OfflinePaymentReceipt)
admin.site.register(OfflinePaymentAuditLog)
admin.site.register(OfflinePaymentNotification)
