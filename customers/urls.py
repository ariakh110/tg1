from rest_framework.routers import DefaultRouter

from .views import (
    CrmOpportunityViewSet,
    CrmSyncEventViewSet,
    CustomerActivityViewSet,
    CustomerTransactionViewSet,
    CustomerViewSet,
)

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="crm-customer")
router.register(r"transactions", CustomerTransactionViewSet, basename="crm-transaction")
router.register(r"activities", CustomerActivityViewSet, basename="crm-activity")
router.register(r"opportunities", CrmOpportunityViewSet, basename="crm-opportunity")
router.register(r"sync-events", CrmSyncEventViewSet, basename="crm-sync-event")

app_name = "customers"
urlpatterns = router.urls
