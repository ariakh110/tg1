from rest_framework import permissions
from .models import RoleCode, UserRole


class HasActiveRole(permissions.BasePermission):
    message = "Required role is not active."

    def __init__(self, role_code: str):
        self.role_code = role_code

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        return UserRole.objects.filter(
            user=user, role=self.role_code, is_active=True
        ).exists()


class HasRole(permissions.BasePermission):
    message = "Required role is missing."

    def __init__(self, role_code: str):
        self.role_code = role_code

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        return UserRole.objects.filter(user=user, role=self.role_code).exists()
