from django.contrib import admin

from .models import (
    OfflinePayment,
    OfflinePaymentAuditLog,
    OfflinePaymentNotification,
    OfflinePaymentReceipt,
    SatnaBankAccount,
    SatnaBankAccountAuditLog,
)


admin.site.register(OfflinePayment)
admin.site.register(OfflinePaymentReceipt)
admin.site.register(OfflinePaymentAuditLog)
admin.site.register(OfflinePaymentNotification)
admin.site.register(SatnaBankAccount)
admin.site.register(SatnaBankAccountAuditLog)
