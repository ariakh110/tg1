from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Profile, UserRole, RoleCode

User = get_user_model()

@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        # optionally save profile
        try:
            instance.profile.save()
        except Profile.DoesNotExist:
            Profile.objects.create(user=instance)
    buyer_role, _created = UserRole.objects.get_or_create(
        user=instance,
        role=RoleCode.BUYER,
        defaults={"is_active": True, "activated_at": timezone.now()},
    )
    if not buyer_role.is_active:
        buyer_role.is_active = True
        buyer_role.activated_at = buyer_role.activated_at or timezone.now()
        buyer_role.save(update_fields=["is_active", "activated_at"])
