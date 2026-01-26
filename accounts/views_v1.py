import os

from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import KYCDocument, KYCRequest, KYCStatus, RoleCode, UserRole
from .serializers import (
    KYCDocumentSerializer,
    KYCRequestSerializer,
    KYCRequestAdminUpdateSerializer,
    UserMeSerializer,
    UserRoleSerializer,
)
from .services import activate_roles, ensure_user_role


class UserMeAPIView(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        serializer = UserMeSerializer(request.user, context={"request": request})
        return Response(serializer.data)


class UserRoleViewSet(viewsets.ModelViewSet):
    queryset = UserRole.objects.select_related("user")
    serializer_class = UserRoleSerializer
    permission_classes = [permissions.IsAdminUser]


class KYCRequestViewSet(viewsets.ModelViewSet):
    queryset = KYCRequest.objects.select_related("user").prefetch_related("documents")
    serializer_class = KYCRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return self.queryset
        return self.queryset.filter(user=user)

    def create(self, request, *args, **kwargs):
        if KYCRequest.objects.filter(user=request.user, status=KYCStatus.PENDING).exists():
            return Response(
                {"detail": "pending_kyc_exists"},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_roles = serializer.validated_data.get("requested_roles", [])
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
        if kyc.user != request.user and not (request.user.is_staff or request.user.is_superuser):
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

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
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

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAdminUser])
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
