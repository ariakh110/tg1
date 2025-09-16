from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    """
    اجازهٔ نوشتن فقط برای ادمین/استاف. خواندن برای همه.
    استفاده پیشنهادی برای مدل‌هایی که باید فقط ادمین آنها را تغییر دهد (مثلاً Product).
    """
    def has_permission(self, request, view):
        # همه می‌توانند GET/HEAD/OPTIONS
        if request.method in permissions.SAFE_METHODS:
            return True
        # برای نوشتن فقط staff یا superuser
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser))


class HasSellerProfile(permissions.BasePermission):
    """
    اجازه ایجاد Offer فقط زمانی داده می‌شود که کاربر دارای یک Seller profile باشد.
    چک می‌کند request.user.seller_profile وجود داشته باشد.
    """
    message = "You must have a seller profile to perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # check related name: 'seller_profile'
        return hasattr(request.user, "seller_profile")


class IsOfferOwner(permissions.BasePermission):
    """
    اجازهٔ تغییر (update/delete) روی Offer فقط به صاحب آن Offer (و admin) داده می‌شود.
    این permission برای Offer و همچنین برای PricingTier/DeliveryLocation که به Offer وابسته‌اند کاربرد دارد.
    """
    message = "Only the owner seller (or staff) can modify this object."

    def has_object_permission(self, request, view, obj):
        # staff or superuser can do anything
        if request.user and (request.user.is_staff or request.user.is_superuser):
            return True

        # obj می‌تواند Offer باشد (در این صورت دسترسی مستقیم داریم)
        if hasattr(obj, "seller"):
            return obj.seller.user == request.user

        # obj ممکن است PricingTier یا DeliveryLocation باشد که فیلد offer دارد
        if hasattr(obj, "offer"):
            try:
                return obj.offer.seller.user == request.user
            except Exception:
                return False

        # default deny
        return False
