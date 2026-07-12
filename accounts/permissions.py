from rest_framework import permissions
from .admin_sections import ALL, effective_admin_sections
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


class IsAdminOrActiveAdminRole(permissions.BasePermission):
    """گیتِ سطحِ ادمین + کنترلِ دسترسیِ بخشی (section-level).

    - سوپریوزر/استاف و نقشِ ``ADMIN`` → دسترسیِ کامل (مثل قبل).
    - نقش‌های محدود (مثل ``MARKETER``) فقط به viewهایی دسترسی دارند که
      بخشِ موردِنیازشان (`admin_section`/`admin_sections`) در مجموعهٔ
      بخش‌های مجازِ آن نقش باشد.
    - viewهای annotate‌نشده برای نقشِ محدود بسته‌اند (پیش‌فرضِ امن)، ولی
      برای ادمینِ کامل بدون تغییر باز می‌مانند.
    """

    message = "Admin access is required."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True

        sections = effective_admin_sections(user)
        if sections == ALL:
            return True
        if not sections:
            return False

        required = self._required_sections(view)
        if required is None:
            # viewِ بدونِ بخشِ تعریف‌شده فقط برای ادمینِ کامل است.
            return False
        return bool(required & sections)

    @staticmethod
    def _required_sections(view):
        """مجموعهٔ بخش‌های لازم برای این view (یا None اگر تعریف نشده)."""
        result = set()
        single = getattr(view, "admin_section", None)
        if single:
            result.add(single)
        multiple = getattr(view, "admin_sections", None)
        if multiple:
            result.update(multiple)
        return result or None


class IsFullAdminUser(permissions.BasePermission):
    """Allow staff/superusers and active ADMIN-role users, excluding scoped roles."""

    message = "Full admin access is required."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if user.is_staff or user.is_superuser:
            return True
        return effective_admin_sections(user) == ALL
