from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import KYCRequest, KYCStatus, RoleCode, UserRole
from .serializers import (
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
