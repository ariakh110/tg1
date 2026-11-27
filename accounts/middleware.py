from django.http import HttpResponseForbidden

from .models import RoleCode


class CrmSalesDjangoAdminGuard:
    """Keep limited CRM sales accounts out of the global Django admin site."""

    admin_prefix = "/django-admin/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            request.path.startswith(self.admin_prefix)
            and user
            and user.is_authenticated
            and not user.is_superuser
            and user.roles.filter(role=RoleCode.CRM_SALES, is_active=True).exists()
        ):
            return HttpResponseForbidden("CRM sales accounts must use the scoped CRM interface.")
        return self.get_response(request)
