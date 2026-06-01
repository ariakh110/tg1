from django.urls import path

from .views import (
    AdminOfflinePaymentListAPIView,
    AdminOfflinePaymentReviewAPIView,
    AdminOfflinePaymentUnlockAPIView,
    BankAccountListAPIView,
    OfflinePaymentListCreateAPIView,
    OfflinePaymentStatusAPIView,
    ReceiptFileAPIView,
    ReceiptUploadAPIView,
)


urlpatterns = [
    path("offline-payments/bank-accounts/", BankAccountListAPIView.as_view(), name="offline-payment-bank-accounts"),
    path("offline-payments/", OfflinePaymentListCreateAPIView.as_view(), name="offline-payment-list"),
    path("offline-payments/<uuid:pk>/status/", OfflinePaymentStatusAPIView.as_view(), name="offline-payment-status"),
    path("offline-payments/<uuid:pk>/upload-receipt/", ReceiptUploadAPIView.as_view(), name="offline-payment-upload"),
    path("offline-payments/<uuid:pk>/receipt/", ReceiptFileAPIView.as_view(), name="offline-payment-receipt-file"),
    path("admin/offline-payments/", AdminOfflinePaymentListAPIView.as_view(), name="admin-offline-payment-list"),
    path("admin/offline-payments/<uuid:pk>/review/", AdminOfflinePaymentReviewAPIView.as_view(), name="admin-offline-payment-review"),
    path("admin/offline-payments/<uuid:pk>/unlock/", AdminOfflinePaymentUnlockAPIView.as_view(), name="admin-offline-payment-unlock"),
]
