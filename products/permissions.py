# products/permissions.py
from rest_framework import permissions

from accounts.models import RoleCode
from accounts.services import user_has_role

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    خواندن برای همه. نوشتن فقط برای staff / superuser.
    مناسب برای مدل‌هایی که تغییرشان فقط توسط ادمین مجاز است.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))


class HasSellerProfile(permissions.BasePermission):
    """
    اجازهٔ نوشتن (create/update/delete) فقط در صورتی که:
      - کاربر لاگین کرده و
      - یا profile.role شامل SELLER/BOTH باشد
      - یا کاربر قبلاً یک Seller مدل ساخته باشد (request.user.seller_profile)
    این کلاس برای endpointهایی مثل ایجاد Offer یا PricingTier مناسب است.
    """
    message = "You must have a seller profile (or role=SELLER) to perform this action."

    def has_permission(self, request, view):
        # read allowed
        if request.method in permissions.SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Require verified (active) users for seller actions
        if not getattr(user, "is_active", False):
            return False

        # 1) explicit seller model exists and is verified
        if hasattr(user, "seller_profile"):
            seller_profile = getattr(user, "seller_profile", None)
            if seller_profile and seller_profile.is_verified:
                return True

        # 2) profile.role allows seller actions
        profile = getattr(user, "profile", None)
        if profile is not None:
            # profile.Role might be an enum-like class on Profile
            try:
                role_value = profile.role
            except Exception:
                role_value = None
            if role_value in ("SELLER", "BOTH") and user_has_role(user, RoleCode.SELLER, require_active=True):
                return True

        if user_has_role(user, RoleCode.SELLER, require_active=True):
            return True

        return False


class IsOfferOwner(permissions.BasePermission):
    """
    اجازهٔ تغییر (update/delete) برای Offer و اشیائی که به Offer وابسته‌اند
    (مثل PricingTier, DeliveryLocation) تنها برای مالک آن Offer یا admin است.
    """
    message = "Only the owner seller (or staff) can modify this object."

    def has_object_permission(self, request, view, obj):
        # always allow read
        if request.method in permissions.SAFE_METHODS:
            return True

        user = request.user
        # staff / superuser override
        if user and (user.is_staff or user.is_superuser):
            return True

        # Find seller (robustly)
        seller = None

        # Direct Offer model with seller attribute
        if hasattr(obj, "seller"):
            seller = getattr(obj, "seller", None)
        # Models linked to an offer (PricingTier, DeliveryLocation, etc.)
        elif hasattr(obj, "offer"):
            offer = getattr(obj, "offer", None)
            if offer is not None:
                seller = getattr(offer, "seller", None)
        # Sometimes obj could be PricingTier with .offer attribute -> covered above

        if not seller:
            return False

        # Compare either by seller.user or by seller instance equality with request.user.seller_profile
        try:
            # if seller has a user FK
            if hasattr(seller, "user") and seller.user == user:
                return True
        except Exception:
            pass

        # or compare seller object with request.user.seller_profile
        if hasattr(user, "seller_profile") and user.seller_profile == seller:
            return True

        return False


class IsSellerOwnerOrAdmin(permissions.BasePermission):
    """
    برای مدل Seller: فقط صاحب (مالک) یا admin می‌تواند ویرایش/حذف کند.
    خواندن برای همه (یا می‌توانید محدود کنید).
    """
    message = "Only the owner seller or admin can modify this seller profile."

    def has_object_permission(self, request, view, obj):
        # read allowed
        if request.method in permissions.SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        # obj expected to be Seller instance with 'user' FK
        owner_user = getattr(obj, "user", None)
        return owner_user == user
