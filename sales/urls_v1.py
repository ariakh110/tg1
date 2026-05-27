from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminStoreOrderViewSet,
    StoreBuyerAddressViewSet,
    StoreBuyerInvoiceProfileViewSet,
    StoreDashboardSummaryAPIView,
    StoreOrderViewSet,
    StorePaymentListAPIView,
    StorePendingPaymentsAPIView,
)


router = DefaultRouter()
router.register(r"store/addresses", StoreBuyerAddressViewSet, basename="store-addresses")
router.register(r"store/invoice-profiles", StoreBuyerInvoiceProfileViewSet, basename="store-invoice-profiles")
router.register(r"store/orders", StoreOrderViewSet, basename="store-orders")
router.register(
    r"admin/dashboard/store-orders",
    AdminStoreOrderViewSet,
    basename="admin-store-orders",
)

urlpatterns = [
    path("store/dashboard/summary/", StoreDashboardSummaryAPIView.as_view(), name="store-dashboard-summary"),
    path("store/payments/", StorePaymentListAPIView.as_view(), name="store-payments"),
    path("store/pending-payments/", StorePendingPaymentsAPIView.as_view(), name="store-pending-payments"),
    path("", include(router.urls)),
]
