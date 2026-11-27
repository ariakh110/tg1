from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import (
    CrmOpportunityViewSet,
    CrmSyncEventViewSet,
    CrmAutomationRunViewSet,
    CrmFollowUpViewSet,
    CrmPhoneIntakeView,
    CrmTaskViewSet,
    CrmWorkQueueView,
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
router.register(r"tasks", CrmTaskViewSet, basename="crm-task")
router.register(r"follow-ups", CrmFollowUpViewSet, basename="crm-follow-up")
router.register(r"automation-runs", CrmAutomationRunViewSet, basename="crm-automation-run")

app_name = "customers"
urlpatterns = [
    path("work-queue/", CrmWorkQueueView.as_view(), name="crm-work-queue"),
    path("phone-intake/", CrmPhoneIntakeView.as_view(), name="crm-phone-intake"),
    *router.urls,
]
