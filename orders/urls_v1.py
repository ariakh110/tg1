from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OrderOfferViewSet, OrderViewSet

router = DefaultRouter()
router.register(r"orders", OrderViewSet, basename="orders")
router.register(r"offers", OrderOfferViewSet, basename="order-offers")

urlpatterns = [
    path("", include(router.urls)),
]
