from django.urls import path

from .views import (
    AdminOfflinePaymentFinancialReportAPIView,
    AdminOfflinePaymentListAPIView,
    AdminOfflinePaymentReceiptReversalAPIView,
    AdminOfflinePaymentReviewAPIView,
    AdminOfflinePaymentUnlockAPIView,
    AdminSatnaBankAccountDetailAPIView,
    AdminSatnaBankAccountListCreateAPIView,
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
    path("offline-payments/<uuid:pk>/receipt/", ReceiptFileAPIView.as_view(), name="offline-payment-current-receipt-file"),
    path("offline-payments/<uuid:pk>/receipts/<int:receipt_id>/file/", ReceiptFileAPIView.as_view(), name="offline-payment-receipt-file"),
    path("admin/offline-payments/financial-report/", AdminOfflinePaymentFinancialReportAPIView.as_view(), name="admin-offline-payment-financial-report"),
    path("admin/offline-payments/", AdminOfflinePaymentListAPIView.as_view(), name="admin-offline-payment-list"),
    path("admin/offline-payments/bank-accounts/", AdminSatnaBankAccountListCreateAPIView.as_view(), name="admin-offline-payment-bank-account-list"),
    path("admin/offline-payments/bank-accounts/<str:code>/", AdminSatnaBankAccountDetailAPIView.as_view(), name="admin-offline-payment-bank-account-detail"),
    path("admin/offline-payments/<uuid:pk>/receipts/<int:receipt_id>/reverse/", AdminOfflinePaymentReceiptReversalAPIView.as_view(), name="admin-offline-payment-receipt-reverse"),
    path("admin/offline-payments/<uuid:pk>/review/", AdminOfflinePaymentReviewAPIView.as_view(), name="admin-offline-payment-review"),
    path("admin/offline-payments/<uuid:pk>/unlock/", AdminOfflinePaymentUnlockAPIView.as_view(), name="admin-offline-payment-unlock"),
]
