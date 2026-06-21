import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import KYCDocument, KYCRequest, KYCStatus, RoleCode, UserRole
from .permissions import IsAdminOrActiveAdminRole
from .serializers import (
    AdminSetActiveSerializer,
    AdminSetPasswordSerializer,
    AdminSetRoleSerializer,
    AdminUserSummarySerializer,
    KYCDocumentSerializer,
    KYCRequestSerializer,
    KYCRequestAdminUpdateSerializer,
    UserMeSerializer,
    UserRoleSerializer,
)
from .services import activate_roles, ensure_user_role

User = get_user_model()


class UserMeAPIView(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        serializer = UserMeSerializer(request.user, context={"request": request})
        return Response(serializer.data)


class UserRoleViewSet(viewsets.ModelViewSet):
    queryset = UserRole.objects.select_related("user")
    serializer_class = UserRoleSerializer
    permission_classes = [IsAdminOrActiveAdminRole]


class AdminUserViewSet(viewsets.ReadOnlyModelViewSet):
    """مدیریتِ کاربران توسط ادمین: نمایش + تأیید/تعلیق، ریست رمز، و مدیریت نقش‌ها."""

    serializer_class = AdminUserSummarySerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def get_queryset(self):
        queryset = User.objects.all().prefetch_related("roles", "kyc_requests").order_by("-date_joined")
        q = (self.request.query_params.get("q") or "").strip()
        role_code = (self.request.query_params.get("role") or "").strip()
        if q:
            queryset = queryset.filter(Q(username__icontains=q) | Q(email__icontains=q))
        if role_code:
            queryset = queryset.filter(roles__role=role_code).distinct()
        return queryset

    def _guard_target(self, target):
        """ادمینِ غیرسوپریوزر نمی‌تواند یک سوپریوزر را تغییر دهد."""
        if target.is_superuser and not self.request.user.is_superuser:
            raise PermissionDenied("نمی‌توانید حسابِ سوپریوزر را تغییر دهید.")

    def _summary(self, user):
        return Response(AdminUserSummarySerializer(user, context={"request": self.request}).data)

    @action(detail=True, methods=["post"], url_path="set_active")
    def set_active(self, request, pk=None):
        target = self.get_object()
        self._guard_target(target)
        serializer = AdminSetActiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_active = serializer.validated_data["is_active"]
        if not is_active and target == request.user:
            return Response(
                {"detail": "نمی‌توانید حسابِ خودتان را غیرفعال کنید."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if target.is_active != is_active:
            target.is_active = is_active
            target.save(update_fields=["is_active"])
        return self._summary(target)

    @action(detail=True, methods=["post"], url_path="set_password")
    def set_password(self, request, pk=None):
        target = self.get_object()
        self._guard_target(target)
        serializer = AdminSetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target.set_password(serializer.validated_data["password"])
        target.save(update_fields=["password"])
        return Response({"detail": "رمز عبور تغییر کرد."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="set_role")
    def set_role(self, request, pk=None):
        target = self.get_object()
        self._guard_target(target)
        serializer = AdminSetRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        is_active = serializer.validated_data["is_active"]
        # دادن/گرفتنِ نقش‌های دارایِ دسترسیِ پنل ادمین (مدیر/بازاریاب) فقط برای سوپریوزر
        if role in (RoleCode.ADMIN, RoleCode.MARKETER) and not request.user.is_superuser:
            raise PermissionDenied("فقط سوپریوزر می‌تواند نقشِ مدیر یا بازاریاب را تغییر دهد.")
        user_role, _created = UserRole.objects.get_or_create(user=target, role=role)
        user_role.is_active = is_active
        user_role.activated_at = timezone.now() if is_active else None
        user_role.save(update_fields=["is_active", "activated_at"])
        return self._summary(target)


class KYCRequestViewSet(viewsets.ModelViewSet):
    queryset = KYCRequest.objects.select_related("user").prefetch_related("documents")
    serializer_class = KYCRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ("approve", "reject"):
            return [permissions.IsAuthenticated(), IsAdminOrActiveAdminRole()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        is_admin_scope = user.is_staff or user.is_superuser or UserRole.objects.filter(
            user=user,
            role=RoleCode.ADMIN,
            is_active=True,
        ).exists()
        if not is_admin_scope:
            queryset = queryset.filter(user=user)
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset

    def create(self, request, *args, **kwargs):
        if KYCRequest.objects.filter(user=request.user, status=KYCStatus.PENDING).exists():
            return Response(
                {"detail": "pending_kyc_exists"},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_roles = serializer.validated_data.get("requested_roles", [])
        active_roles = set(
            UserRole.objects.filter(
                user=request.user, role__in=requested_roles, is_active=True
            ).values_list("role", flat=True)
        )
        if active_roles and active_roles == set(requested_roles):
            return Response(
                {"detail": "roles_already_active"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        for role_code in requested_roles:
            ensure_user_role(request.user, role_code, is_active=False)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _validate_document(self, file):
        allowed_extensions = getattr(
            settings, "KYC_DOCUMENT_ALLOWED_EXTENSIONS", [".pdf", ".zip"]
        )
        allowed_mime_types = getattr(
            settings,
            "KYC_DOCUMENT_ALLOWED_MIME_TYPES",
            [
                "application/pdf",
                "application/zip",
                "application/x-zip-compressed",
                "multipart/x-zip",
            ],
        )
        max_size_mb = getattr(settings, "KYC_DOCUMENT_MAX_SIZE_MB", 10)
        max_size_bytes = int(max_size_mb) * 1024 * 1024

        name = getattr(file, "name", "").lower()
        _, ext = os.path.splitext(name)
        if not ext or ext not in allowed_extensions:
            return f"invalid_extension:{ext}"

        if file.size > max_size_bytes:
            return f"file_too_large:{max_size_mb}MB"

        content_type = getattr(file, "content_type", None)
        if content_type and content_type not in allowed_mime_types:
            return f"invalid_mime:{content_type}"

        return None

    @action(
        detail=True,
        methods=["post"],
        url_path="documents",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_document(self, request, pk=None):
        kyc = self.get_object()
        is_admin_scope = request.user.is_staff or request.user.is_superuser or UserRole.objects.filter(
            user=request.user,
            role=RoleCode.ADMIN,
            is_active=True,
        ).exists()
        if kyc.user != request.user and not is_admin_scope:
            return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
        if kyc.status != KYCStatus.PENDING:
            return Response({"detail": "kyc_not_pending"}, status=status.HTTP_409_CONFLICT)
        files = request.FILES.getlist("file") or request.FILES.getlist("files")
        if not files and request.FILES.get("file"):
            files = [request.FILES.get("file")]
        if not files:
            return Response({"detail": "file_required"}, status=status.HTTP_400_BAD_REQUEST)
        errors = []
        for file in files:
            error = self._validate_document(file)
            if error:
                errors.append({"file": getattr(file, "name", "document"), "error": error})
        if errors:
            return Response(
                {"detail": "invalid_files", "errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        docs = []
        for file in files:
            name = request.data.get("name") if len(files) == 1 else None
            name = name or getattr(file, "name", "document")
            docs.append(KYCDocument.objects.create(kyc_request=kyc, name=name, file=file))

        if len(docs) == 1:
            serializer = KYCDocumentSerializer(docs[0], context={"request": request})
        else:
            serializer = KYCDocumentSerializer(docs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrActiveAdminRole])
    def approve(self, request, pk=None):
        kyc = self.get_object()
        kyc.status = KYCStatus.APPROVED
        kyc.reviewed_at = timezone.now()
        kyc.reject_reason = ""
        kyc.save(update_fields=["status", "reviewed_at", "reject_reason"])
        activate_roles(kyc.user, kyc.requested_roles)

        # If seller profile exists and SELLER role is approved, mark verified.
        if RoleCode.SELLER in kyc.requested_roles:
            seller_profile = getattr(kyc.user, "seller_profile", None)
            if seller_profile and not seller_profile.is_verified:
                seller_profile.is_verified = True
                seller_profile.save(update_fields=["is_verified"])

        serializer = KYCRequestSerializer(kyc, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrActiveAdminRole])
    def reject(self, request, pk=None):
        kyc = self.get_object()
        serializer = KYCRequestAdminUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kyc.status = KYCStatus.REJECTED
        kyc.reviewed_at = timezone.now()
        kyc.reject_reason = serializer.validated_data.get("reject_reason", "")
        kyc.save(update_fields=["status", "reviewed_at", "reject_reason"])
        out = KYCRequestSerializer(kyc, context={"request": request})
        return Response(out.data, status=status.HTTP_200_OK)
