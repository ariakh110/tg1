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


class VerificationResend(models.Model):
    """Track resend attempts per user to enforce a simple rate limit.

    Fields:
    - user: FK to the User
    - count: number of resends within the window
    - window_start: when the current window started
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='verification_resend')
    count = models.PositiveIntegerField(default=0)
    window_start = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Resend({self.user.username})={self.count} since {self.window_start}"


class RoleCode(models.TextChoices):
    BUYER = "BUYER", _("Buyer")
    SELLER = "SELLER", _("Seller")
    CUTTER = "CUTTER", _("Cutter")
    DRIVER = "DRIVER", _("Driver")
    QC = "QC", _("Quality Control")
    STRUCTURAL_DESIGNER = "STRUCTURAL_DESIGNER", _("Structural Designer")
    ADMIN = "ADMIN", _("Admin")


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="roles")
    role = models.CharField(max_length=32, choices=RoleCode.choices)
    is_active = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "role")

    def __str__(self):
        return f"{self.user} - {self.role}"


class KYCStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")


class KYCRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="kyc_requests")
    requested_roles = models.JSONField(default=list)
    status = models.CharField(max_length=16, choices=KYCStatus.choices, default=KYCStatus.PENDING)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reject_reason = models.TextField(blank=True)

    class Meta:
        ordering = ("-submitted_at",)

    def __str__(self):
        return f"KYCRequest({self.user})={self.status}"


class KYCDocument(models.Model):
    kyc_request = models.ForeignKey(KYCRequest, on_delete=models.CASCADE, related_name="documents")
    name = models.CharField(max_length=255)
    file = models.FileField(upload_to="kyc_docs/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"KYCDocument({self.kyc_request_id}) - {self.name}"
