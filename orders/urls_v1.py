from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminActivityFeedAPIView,
    AdminDashboardSummaryAPIView,
    AdminOrderRequestViewSet,
    MarketplaceFeedAPIView,
    MyOrderRequestViewSet,
    OrderOfferViewSet,
    OrderViewSet,
    WarehousePendingRequestListAPIView,
    WarehouseVerifyAPIView,
)

router = DefaultRouter()
router.register(r"orders", OrderViewSet, basename="orders")
router.register(r"offers", OrderOfferViewSet, basename="order-offers")
router.register(r"my/requests", MyOrderRequestViewSet, basename="my-requests")
router.register(
    r"admin/dashboard/order-requests",
    AdminOrderRequestViewSet,
    basename="admin-order-requests",
)

urlpatterns = [
    path("admin/dashboard/summary/", AdminDashboardSummaryAPIView.as_view(), name="admin-dashboard-summary"),
    path("admin/dashboard/activities/", AdminActivityFeedAPIView.as_view(), name="admin-dashboard-activities"),
    path("marketplace/feed/", MarketplaceFeedAPIView.as_view(), name="marketplace-feed"),
    path("warehouse/requests/", WarehousePendingRequestListAPIView.as_view(), name="warehouse-requests"),
    path("warehouse/verify/<uuid:request_id>/", WarehouseVerifyAPIView.as_view(), name="warehouse-verify"),
    path("", include(router.urls)),
]
