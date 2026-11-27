from django.urls import path

from .mobile_api import (
    MobileCustomerDetailView,
    MobileCustomerListView,
    MobileCustomerPreferenceView,
    MobileActivityCreateView,
    MobileMeView,
    MobileTaskActionView,
    MobileTaskCreateView,
    MobileWorkView,
)

app_name = "crm-mobile"
urlpatterns = [
    path("me/", MobileMeView.as_view(), name="me"),
    path("customers/", MobileCustomerListView.as_view(), name="customers"),
    path("customers/<int:pk>/", MobileCustomerDetailView.as_view(), name="customer-detail"),
    path("customers/<int:pk>/preferences/", MobileCustomerPreferenceView.as_view(), name="customer-preferences"),
    path("customers/<int:pk>/activities/", MobileActivityCreateView.as_view(), name="customer-activities"),
    path("work/", MobileWorkView.as_view(), name="work"),
    path("tasks/", MobileTaskCreateView.as_view(), name="task-create"),
    path("tasks/<int:pk>/<str:action_name>/", MobileTaskActionView.as_view(), name="task-action"),
]
