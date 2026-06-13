from json import JSONDecodeError
from django.http import JsonResponse
from .serializers import ContactSerializer, SiteSettingsSerializer
from .models import SiteSettings
from rest_framework.parsers import JSONParser
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
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