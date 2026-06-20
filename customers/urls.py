from rest_framework.routers import DefaultRouter

from .views import CustomerTransactionViewSet, CustomerViewSet

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="crm-customer")
router.register(r"transactions", CustomerTransactionViewSet, basename="crm-transaction")

app_name = "customers"
urlpatterns = router.urls
