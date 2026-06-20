from rest_framework.routers import DefaultRouter

from .views import (
    CustomerActivityViewSet,
    CustomerTransactionViewSet,
    CustomerViewSet,
)

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="crm-customer")
router.register(r"transactions", CustomerTransactionViewSet, basename="crm-transaction")
router.register(r"activities", CustomerActivityViewSet, basename="crm-activity")

app_name = "customers"
urlpatterns = router.urls
