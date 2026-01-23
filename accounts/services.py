from django.utils import timezone
from .models import UserRole


def ensure_user_role(user, role_code, is_active=False):
    role, _created = UserRole.objects.get_or_create(
        user=user,
        role=role_code,
        defaults={
            "is_active": bool(is_active),
            "activated_at": timezone.now() if is_active else None,
        },
    )
    if is_active and not role.is_active:
        role.is_active = True
        role.activated_at = timezone.now()
        role.save(update_fields=["is_active", "activated_at"])
    return role


def activate_roles(user, role_codes):
    now = timezone.now()
    for role_code in role_codes:
        role, _created = UserRole.objects.get_or_create(user=user, role=role_code)
        if not role.is_active:
            role.is_active = True
            role.activated_at = now
            role.save(update_fields=["is_active", "activated_at"])


def user_has_role(user, role_code, require_active=False):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    qs = UserRole.objects.filter(user=user, role=role_code)
    if require_active:
        qs = qs.filter(is_active=True)
    return qs.exists()
