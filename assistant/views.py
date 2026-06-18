import uuid

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrActiveAdminRole

from .ai import AssistantError, ensure_embeddings, run_chat
from .models import AssistantConversation, AssistantInquiry, AssistantKnowledge, AssistantSettings
from .serializers import (
    AssistantConversationDetailSerializer,
    AssistantConversationSerializer,
    AssistantInquirySerializer,
    AssistantKnowledgeSerializer,
    AssistantSettingsSerializer,
    PublicAssistantConfigSerializer,
)

MAX_MESSAGE_LEN = 2000


class AssistantConfigView(APIView):
    """پیکربندی عمومیِ ویجت دستیار (برای نمایش در فرانت)."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(PublicAssistantConfigSerializer(AssistantSettings.load()).data)


class AssistantChatView(APIView):
    """نقطهٔ پایانیِ گفتگوی عمومی با دستیار فروش."""

    permission_classes = [AllowAny]

    def post(self, request):
        cfg = AssistantSettings.load()
        if not cfg.is_enabled:
            return Response({"detail": "دستیار فروش فعال نیست."}, status=status.HTTP_403_FORBIDDEN)

        data = request.data if isinstance(request.data, dict) else {}
        message = str(data.get("message", "")).strip()
        if not message:
            return Response({"detail": "پیام خالی است."}, status=status.HTTP_400_BAD_REQUEST)
        message = message[:MAX_MESSAGE_LEN]

        session_key = str(data.get("session_key", "")).strip()[:64] or uuid.uuid4().hex
        conversation, _created = AssistantConversation.objects.get_or_create(session_key=session_key)
        if request.user.is_authenticated and conversation.user_id is None:
            conversation.user = request.user
            conversation.save(update_fields=["user"])

        try:
            reply = run_chat(conversation, message, cfg)
        except AssistantError as exc:
            handoff = f" برای راهنمایی با {cfg.handoff_phone} تماس بگیرید." if cfg.handoff_phone else ""
            return Response(
                {"session_key": session_key, "reply": f"{exc}{handoff}", "error": True},
                status=status.HTTP_200_OK,
            )
        return Response({"session_key": session_key, "reply": reply})


class AdminAssistantSettingsView(APIView):
    """خواندن/به‌روزرسانیِ تنظیمات دستیار (فقط ادمین)."""

    permission_classes = [IsAdminOrActiveAdminRole]

    def get(self, request):
        return Response(AssistantSettingsSerializer(AssistantSettings.load()).data)

    def patch(self, request):
        cfg = AssistantSettings.load()
        serializer = AssistantSettingsSerializer(cfg, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AssistantSettingsSerializer(cfg).data)


class AdminKnowledgeViewSet(viewsets.ModelViewSet):
    queryset = AssistantKnowledge.objects.all()
    serializer_class = AssistantKnowledgeSerializer
    permission_classes = [IsAdminOrActiveAdminRole]
    pagination_class = None

    @action(detail=False, methods=["post"], url_path="reembed")
    def reembed(self, request):
        try:
            count = ensure_embeddings()
        except AssistantError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({"updated": count, "detail": f"{count} مورد به‌روزرسانی شد."})


class AdminConversationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AssistantConversation.objects.all().prefetch_related("messages")
    permission_classes = [IsAdminOrActiveAdminRole]
    filterset_fields = ["status"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AssistantConversationDetailSerializer
        return AssistantConversationSerializer


class AdminInquiryViewSet(viewsets.ModelViewSet):
    """استعلام‌های ساختاریافته (فقط مشاهده + به‌روزرسانیِ وضعیت/تماس)."""

    queryset = AssistantInquiry.objects.select_related("matched_product", "conversation").all()
    serializer_class = AssistantInquirySerializer
    permission_classes = [IsAdminOrActiveAdminRole]
    http_method_names = ["get", "patch", "head", "options"]
    filterset_fields = ["status"]
    pagination_class = None
