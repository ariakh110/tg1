from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile, UserRole, RoleCode

User = get_user_model()

@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
        UserRole.objects.get_or_create(
            user=instance,
            role=RoleCode.BUYER,
            defaults={"is_active": False, "activated_at": None},
        )
    else:
        # optionally save profile
        try:
            instance.profile.save()
        except Profile.DoesNotExist:
            Profile.objects.create(user=instance)
        UserRole.objects.get_or_create(
            user=instance,
            role=RoleCode.BUYER,
            defaults={"is_active": False, "activated_at": None},
        )
