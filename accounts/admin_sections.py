"""منبعِ یگانهٔ «بخش‌های پنل ادمین» و نگاشتِ نقش‌ها به بخش‌ها.

idهای این لیست دقیقاً با `id`های نوار کناریِ پنل ادمین در فرانت
(`ADMIN_NAV_ITEMS` در `kavehmetal/app/components/admin/AdminDashboardPage.js`)
یکی هستند تا فیلترِ منو و enforcementِ سرور با یک واژگانِ مشترک کار کنند.
"""

from .models import RoleCode

# مقدارِ ویژه: دسترسیِ کامل به همهٔ بخش‌ها (سوپریوزر/استاف و نقشِ ADMIN).
ALL = "ALL"

# همهٔ بخش‌های پنل ادمین (ترتیب = ترتیبِ نمایش).
ADMIN_SECTIONS = [
    "overview",
    "direct-sales",
    "orders",
    "offline-payments",
    "delivery-logistics",
    "products",
    "taxonomy",
    "homepage-slider",
    "featured-loads",
    "kyc",
    "users",
    "activity",
    "faq",
    "landings",
    "bulk-price",
    "crm",
    "crm-followups",
    "crm-funnel",
    "assistant",
    "seo-assistant",
    "settings",
]

# نگاشتِ نقش‌های غیرسوپرادمین به بخش‌های مجاز.
# ADMIN = دسترسی کامل؛ MARKETER = فقط CRM/فروش.
ROLE_SECTIONS = {
    RoleCode.ADMIN: ALL,
    RoleCode.MARKETER: [
        "crm",
        "crm-followups",
        "crm-funnel",
        "assistant",
        "direct-sales",
    ],
}


def effective_admin_sections(user):
    """مجموعهٔ بخش‌های مجاز برای کاربر.

    خروجی یا رشتهٔ ``ALL`` (دسترسی کامل) است یا یک ``set`` از idها.
    کاربرِ بدونِ هیچ نقشِ ادمینی → ``set()`` خالی (هیچ دسترسی‌ای).
    """
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    if user.is_staff or user.is_superuser:
        return ALL

    active_roles = set(
        user.roles.filter(is_active=True).values_list("role", flat=True)
    )
    allowed = set()
    for role in active_roles:
        sections = ROLE_SECTIONS.get(role)
        if sections == ALL:
            return ALL
        if sections:
            allowed.update(sections)
    return allowed
