from json import JSONDecodeError
from django.http import JsonResponse
from .serializers import ContactSerializer, SiteSettingsSerializer
from .models import SiteSettings
from rest_framework.parsers import JSONParser
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.authentication import JWTAuthentication



class ContactAPIView(views.APIView):
    """
    A simple APIView for creating contact entires.
    """
    permission_classes = [AllowAny]
    serializer_class = ContactSerializer

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }

    def get_serializer(self, *args, **kwargs):
        kwargs['context'] = self.get_serializer_context()
        return self.serializer_class(*args, **kwargs)

    def post(self, request):
        try:
            data = JSONParser().parse(request)
            serializer = ContactSerializer(data=data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response(serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except JSONDecodeError:
            return JsonResponse({"result": "error","message": "Json decoding error"}, status= 400)


class SiteSettingsAPIView(views.APIView):
    """تنظیمات سایت: GET عمومی، PATCH فقط ادمین."""

    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAdminUser()]

    def get(self, request):
        return Response(SiteSettingsSerializer(SiteSettings.load()).data)

    def patch(self, request):
        obj = SiteSettings.load()
        data = request.data if isinstance(request.data, dict) else {}

        name = data.get("site_name")
        if name is not None and str(name).strip():
            obj.site_name = str(name).strip()[:120]

        gid = data.get("google_oauth_client_id")
        if gid is not None:
            obj.google_oauth_client_id = str(gid).strip()[:255]

        gtm = data.get("google_tag_manager_id")
        if gtm is not None:
            obj.google_tag_manager_id = str(gtm).strip()[:20]

        model_name = data.get("openai_content_model")
        if model_name is not None:
            obj.openai_content_model = str(model_name).strip()[:80]

        # کلید OpenAI محرمانه است: فقط با مقدار غیرخالی به‌روزرسانی می‌شود (در GET برنمی‌گردد)
        openai_key = data.get("openai_api_key")
        if openai_key is not None and str(openai_key).strip():
            obj.openai_api_key = str(openai_key).strip()[:255]

        commodity = data.get("commodity_exchange")
        if commodity is not None:
            if not isinstance(commodity, dict):
                raise ValidationError({'commodity_exchange': 'ساختار تنظیمات بورس کالا نامعتبر است.'})
            if 'auto_refresh' in commodity:
                if not isinstance(commodity['auto_refresh'], bool):
                    raise ValidationError({'commodity_exchange.auto_refresh': 'مقدار باید true یا false باشد.'})
                obj.ime_auto_refresh = commodity['auto_refresh']
            if 'refresh_minutes' in commodity:
                minutes = commodity['refresh_minutes']
                if type(minutes) is not int or not 5 <= minutes <= 1440:
                    raise ValidationError({'commodity_exchange.refresh_minutes': 'فاصله باید عدد صحیح بین ۵ تا ۱۴۴۰ دقیقه باشد.'})
                obj.ime_refresh_minutes = minutes

        global_metals = data.get("global_metals")
        if global_metals is not None:
            if not isinstance(global_metals, dict):
                raise ValidationError({"global_metals": "ساختار تنظیمات بازار جهانی نامعتبر است."})
            if "enabled" in global_metals:
                if not isinstance(global_metals["enabled"], bool):
                    raise ValidationError({"global_metals.enabled": "مقدار فعال‌بودن باید true یا false باشد."})
                obj.global_metals_enabled = global_metals["enabled"]
            if 'auto_refresh' in global_metals:
                if not isinstance(global_metals['auto_refresh'], bool):
                    raise ValidationError({'global_metals.auto_refresh': 'مقدار باید true یا false باشد.'})
                obj.global_metals_auto_refresh = global_metals['auto_refresh']
            if "provider" in global_metals:
                provider = str(global_metals["provider"]).strip()
                allowed = {choice[0] for choice in SiteSettings.GLOBAL_METALS_PROVIDER_CHOICES}
                if provider not in allowed:
                    raise ValidationError({"global_metals.provider": "ارائه‌دهنده انتخاب‌شده پشتیبانی نمی‌شود."})
                obj.global_metals_provider = provider
            if "visible_codes" in global_metals:
                from products.external_markets import available_global_metals
                codes = global_metals["visible_codes"]
                allowed_codes = {item["code"] for item in available_global_metals()}
                if codes is not None and (
                    not isinstance(codes, list)
                    or any(not isinstance(code, str) or code not in allowed_codes for code in codes)
                ):
                    raise ValidationError({"global_metals.visible_codes": "فهرست فلزات انتخابی نامعتبر است."})
                obj.global_metals_visible_codes = list(dict.fromkeys(codes)) if codes is not None else None
            api_key = global_metals.get("api_key")
            if api_key is not None and str(api_key).strip():
                obj.global_metals_api_key = str(api_key).strip()[:255]
            if global_metals.get("clear_api_key") is True:
                obj.global_metals_api_key = ""
            if "refresh_hours" in global_metals:
                try:
                    refresh_hours = int(global_metals["refresh_hours"])
                except (TypeError, ValueError) as exc:
                    raise ValidationError({"global_metals.refresh_hours": "فاصله همگام‌سازی باید عدد باشد."}) from exc
                if refresh_hours < 1 or refresh_hours > 168:
                    raise ValidationError({"global_metals.refresh_hours": "فاصله همگام‌سازی باید بین ۱ تا ۱۶۸ ساعت باشد."})
                obj.global_metals_refresh_hours = refresh_hours

        # اسکریپت‌های سفارشی هدر/فوتر (HTML خام؛ متن کامل بدون محدودیت طول)
        head_scripts = data.get("head_scripts")
        if head_scripts is not None:
            obj.head_scripts = str(head_scripts)

        footer_scripts = data.get("footer_scripts")
        if footer_scripts is not None:
            obj.footer_scripts = str(footer_scripts)

        sections = data.get("sections") or {}
        field_map = {
            "marketplace": "marketplace_enabled",
            "featured_loads": "featured_loads_enabled",
            "export": "export_enabled",
            "offers": "offers_enabled",
            "blog": "blog_enabled",
        }
        for key, field in field_map.items():
            if key in sections:
                setattr(obj, field, bool(sections[key]))

        obj.save()
        return Response(SiteSettingsSerializer(obj).data)
