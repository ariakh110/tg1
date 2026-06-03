from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminStoreOrderViewSet,
    AdminDeliveryRequestListCreateAPIView,
    DriverAssignmentDocumentAPIView,
    DriverAssignmentListAPIView,
    DriverAssignmentTransitionAPIView,
    DriverLoadOfferListAPIView,
    DriverLoadOfferRespondAPIView,
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
    path("store/driver/load-offers/", DriverLoadOfferListAPIView.as_view(), name="store-driver-load-offers"),
    path("store/driver/load-offers/<uuid:pk>/respond/", DriverLoadOfferRespondAPIView.as_view(), name="store-driver-load-offer-respond"),
    path("store/driver/assignments/", DriverAssignmentListAPIView.as_view(), name="store-driver-assignments"),
    path("store/driver/assignments/<uuid:pk>/transition/", DriverAssignmentTransitionAPIView.as_view(), name="store-driver-assignment-transition"),
    path("store/driver/assignments/<uuid:pk>/documents/", DriverAssignmentDocumentAPIView.as_view(), name="store-driver-assignment-documents"),
    path("admin/dashboard/delivery-requests/", AdminDeliveryRequestListCreateAPIView.as_view(), name="admin-delivery-requests"),
    path("", include(router.urls)),
]
