from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

User = settings.AUTH_USER_MODEL

class Profile(models.Model):
    class Role(models.TextChoices):
        BUYER = "BUYER", _("خریدار")
        SELLER = "SELLER", _("فروشنده")
        BOTH = "BOTH", _("هر دو")

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.BUYER)
    phone = models.CharField(max_length=40, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    language = models.CharField(max_length=10, blank=True, null=True, default="fa")
    company_requested = models.BooleanField(default=False)  # کاربر درخواست تبدیل به فروشنده داده
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # optional fields for KYC
    vat_number = models.CharField(max_length=100, blank=True, null=True)
    business_registration_document = models.FileField(upload_to="kyc_docs/", null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"
