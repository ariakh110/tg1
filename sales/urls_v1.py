from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminFreightBidSessionAPIView,
    AdminStoreOrderViewSet,
    AdminStoreOrderLoadingVehicleListCreateAPIView,
    AdminStoreOrderLoadingVehicleDetailAPIView,
    AdminStoreOrderWeighbridgeSlipListCreateAPIView,
    AdminStoreOrderWeighbridgeSlipDestroyAPIView,
    AdminDeliveryDriverMatchAPIView,
    AdminDeliveryRequestReassignAPIView,
    AdminDeliveryRequestListCreateAPIView,
    AdminDriverOperationalProfileDetailAPIView,
    AdminDriverOperationalProfileListAPIView,
    BuyerFreightBidConfirmAPIView,
    CarrierFreightBidInviteListAPIView,
    CarrierFreightBidOfferAPIView,
    DriverAssignmentDocumentAPIView,
    DriverAssignmentListAPIView,
    DriverAssignmentTransitionAPIView,
    DriverLoadOfferListAPIView,
    DriverLoadOfferRespondAPIView,
    DriverOperationalProfileAPIView,
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
    path("store/driver/profile/", DriverOperationalProfileAPIView.as_view(), name="store-driver-profile"),
    path("store/driver/load-offers/", DriverLoadOfferListAPIView.as_view(), name="store-driver-load-offers"),
    path("store/driver/load-offers/<uuid:pk>/respond/", DriverLoadOfferRespondAPIView.as_view(), name="store-driver-load-offer-respond"),
    path("store/driver/assignments/", DriverAssignmentListAPIView.as_view(), name="store-driver-assignments"),
    path("store/driver/assignments/<uuid:pk>/transition/", DriverAssignmentTransitionAPIView.as_view(), name="store-driver-assignment-transition"),
    path("store/driver/assignments/<uuid:pk>/documents/", DriverAssignmentDocumentAPIView.as_view(), name="store-driver-assignment-documents"),
    path("admin/dashboard/driver-profiles/", AdminDriverOperationalProfileListAPIView.as_view(), name="admin-driver-profiles"),
    path("admin/dashboard/driver-profiles/<int:user_id>/", AdminDriverOperationalProfileDetailAPIView.as_view(), name="admin-driver-profile-detail"),
    path("admin/dashboard/delivery-requests/match-drivers/", AdminDeliveryDriverMatchAPIView.as_view(), name="admin-delivery-driver-matches"),
    path("admin/dashboard/delivery-requests/", AdminDeliveryRequestListCreateAPIView.as_view(), name="admin-delivery-requests"),
    path("admin/dashboard/delivery-requests/<uuid:pk>/reassign/", AdminDeliveryRequestReassignAPIView.as_view(), name="admin-delivery-request-reassign"),
    path("admin/dashboard/store-orders/<uuid:pk>/loading-vehicles/", AdminStoreOrderLoadingVehicleListCreateAPIView.as_view(), name="admin-store-order-loading-vehicles"),
    path("admin/dashboard/store-orders/<uuid:pk>/loading-vehicles/<int:vehicle_pk>/", AdminStoreOrderLoadingVehicleDetailAPIView.as_view(), name="admin-store-order-loading-vehicle-detail"),
    path("admin/dashboard/store-orders/<uuid:pk>/weighbridge-slips/", AdminStoreOrderWeighbridgeSlipListCreateAPIView.as_view(), name="admin-store-order-weighbridge-slips"),
    path("admin/dashboard/store-orders/<uuid:pk>/weighbridge-slips/<int:slip_pk>/", AdminStoreOrderWeighbridgeSlipDestroyAPIView.as_view(), name="admin-store-order-weighbridge-slip-detail"),
    path("admin/dashboard/store-orders/<uuid:pk>/freight-bid/", AdminFreightBidSessionAPIView.as_view(), name="admin-store-order-freight-bid"),
    path("carrier/freight-bid-invites/", CarrierFreightBidInviteListAPIView.as_view(), name="carrier-freight-bid-invites"),
    path("carrier/freight-bid-invites/<uuid:invite_pk>/offer/", CarrierFreightBidOfferAPIView.as_view(), name="carrier-freight-bid-offer"),
    path("store/orders/<uuid:pk>/freight-bid/confirm/", BuyerFreightBidConfirmAPIView.as_view(), name="store-freight-bid-confirm"),
    path("", include(router.urls)),
]
