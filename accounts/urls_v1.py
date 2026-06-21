from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_v1 import AdminUserViewSet, KYCRequestViewSet, UserMeAPIView, UserRoleViewSet

router = DefaultRouter()
router.register(r"kyc", KYCRequestViewSet, basename="kyc")
router.register(r"roles", UserRoleViewSet, basename="roles")
router.register(r"admin/users", AdminUserViewSet, basename="admin-users")

urlpatterns = [
    path("users/me/", UserMeAPIView.as_view({"get": "list"}), name="users-me"),
    path("", include(router.urls)),
]
