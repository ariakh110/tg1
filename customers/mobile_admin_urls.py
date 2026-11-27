from django.urls import path

from .mobile_api import (
    MobileAdminPolicyListView,
    MobileAdminPolicyUpdateView,
    MobileReviewQueueView,
    MobileReviewRejectView,
    MobileReviewResolveView,
)

app_name = "crm-mobile-admin"
urlpatterns = [
    path("policies/", MobileAdminPolicyListView.as_view(), name="policies"),
    path("policies/<str:role_code>/", MobileAdminPolicyUpdateView.as_view(), name="policy-update"),
    path("captures/", MobileReviewQueueView.as_view(), name="captures"),
    path("captures/<uuid:event_uuid>/resolve/", MobileReviewResolveView.as_view(), name="capture-resolve"),
    path("captures/<uuid:event_uuid>/reject/", MobileReviewRejectView.as_view(), name="capture-reject"),
]
