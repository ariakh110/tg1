import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import KYCRequest, KYCStatus, KYCDocument, RoleCode
from accounts.permissions import IsAdminOrActiveAdminRole
from accounts.serializers import KYCRequestSerializer
from accounts.services import user_has_role
from products.models import Product, ProductAuditLog
from .models import (
    OfferStatus,
    Order,
    OrderOffer,
    OrderRequest,
    OrderRequestAuditLog,
    OrderRequestDocument,
    OrderRequestStatusHistory,
    OrderRequestStatus,
    OrderRequestType,
    OrderStatus,
    OrderType,
)
from .permissions import (
    IsOrderOfferParticipant,
    IsOrderOwner,
    IsOrderParticipant,
    IsWarehouseManager,
)
from .serializers import (
    OrderCreateSerializer,
    OrderOfferCreateSerializer,
    OrderOfferReadSerializer,
    OrderRequestCreateSerializer,
    OrderRequestDocumentSerializer,
    OrderRequestFeedSerializer,
    OrderReadSerializer,
    OrderRequestReadSerializer,
    OrderRequestUpdateSerializer,
    OrderStatusHistorySerializer,
    WarehouseVerificationSerializer,
)
from .services import OrderRequestService, accept_offer

User = get_user_model()


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related("buyer", "assigned_provider", "product_type")

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        return OrderReadSerializer

    def get_permissions(self):
        if self.action in ["retrieve", "offers", "status_history"]:
            return [permissions.IsAuthenticated(), IsOrderParticipant()]
        if self.action in ["update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated(), IsOrderOwner()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        read_serializer = OrderReadSerializer(order)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return self.queryset
        filters = Q(buyer=user) | Q(assigned_provider=user)
        if user_has_role(user, RoleCode.SELLER, require_active=True):
            filters |= Q(type=OrderType.BUY, status=OrderStatus.OPEN)
        if user_has_role(user, RoleCode.BUYER, require_active=True):
            filters |= Q(type=OrderType.SELL, status=OrderStatus.OPEN)
        return self.queryset.filter(filters).distinct()

    @action(detail=True, methods=["get"], url_path="status-history")
    def status_history(self, request, pk=None):
        order = self.get_object()
        serializer = OrderStatusHistorySerializer(order.status_history.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"])
    def offers(self, request, pk=None):
        order = self.get_object()
        user = request.user

        if request.method == "GET":
            if order.owner != user and not (user.is_staff or user.is_superuser):
                return Response({"detail": "forbidden"}, status=status.HTTP_403_FORBIDDEN)
            offers = order.offers.select_related("offered_by").all()
            serializer = OrderOfferReadSerializer(offers, many=True)
            return Response(serializer.data)

        if order.status != OrderStatus.OPEN:
            return Response({"detail": "order_not_open"}, status=status.HTTP_409_CONFLICT)
        if order.owner == user:
            return Response({"detail": "cannot_offer_on_own_order"}, status=status.HTTP_400_BAD_REQUEST)

        if order.type == OrderType.BUY:
            if not user_has_role(user, RoleCode.SELLER, require_active=True):
                return Response({"detail": "active_seller_required"}, status=status.HTTP_403_FORBIDDEN)
        elif order.type == OrderType.SELL:
            if not user_has_role(user, RoleCode.BUYER, require_active=True):
                return Response({"detail": "buyer_role_required"}, status=status.HTTP_403_FORBIDDEN)

        if OrderOffer.objects.filter(order=order, offered_by=user, status=OfferStatus.PENDING).exists():
            return Response({"detail": "offer_already_exists"}, status=status.HTTP_409_CONFLICT)

        serializer = OrderOfferCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer = serializer.save(order=order, offered_by=user)
        read_serializer = OrderOfferReadSerializer(offer)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class OrderOfferViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderOfferReadSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrderOfferParticipant]

    def get_queryset(self):
        user = self.request.user
        base = OrderOffer.objects.select_related("order", "offered_by")
        if user.is_staff or user.is_superuser:
            return base
        return base.filter(
            Q(offered_by=user)
            | Q(order__buyer=user)
            | Q(order__assigned_provider=user)
        ).distinct()

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        offer = self.get_object()
        order = accept_offer(offer, request.user)
        serializer = OrderReadSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


def _validate_request_document(file):
    allowed_extensions = getattr(
        settings, "ORDER_REQUEST_DOC_ALLOWED_EXTENSIONS", [".pdf", ".zip"]
    )
    allowed_mime_types = getattr(
        settings,
        "ORDER_REQUEST_DOC_ALLOWED_MIME_TYPES",
        [
            "application/pdf",
            "application/zip",
            "application/x-zip-compressed",
            "multipart/x-zip",
        ],
    )
    max_size_mb = getattr(settings, "ORDER_REQUEST_DOC_MAX_SIZE_MB", 10)
    max_size_bytes = int(max_size_mb) * 1024 * 1024

    filename = getattr(file, "name", "").lower()
    _, ext = os.path.splitext(filename)
    if not ext or ext not in allowed_extensions:
        return f"invalid_extension:{ext or 'none'}"
    if file.size > max_size_bytes:
        return f"file_too_large:{max_size_mb}MB"
    content_type = getattr(file, "content_type", "")
    if content_type and content_type not in allowed_mime_types:
        return f"invalid_mime:{content_type}"
    return None


class MarketplaceFeedAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OrderRequestFeedSerializer

    def get_queryset(self):
        queryset = OrderRequest.all_objects.public_feed().select_related("owner", "category")
        queryset = queryset.exclude(owner=self.request.user)
        request_type = self.request.query_params.get("type")
        category = self.request.query_params.get("category")
        status_param = self.request.query_params.get("status")
        if request_type:
            queryset = queryset.filter(type=request_type)
        if category:
            queryset = queryset.filter(category_id=category)
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset.order_by("-created_at")


class MyOrderRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            OrderRequest.all_objects.filter(owner=self.request.user)
            .select_related("owner", "category", "verified_by")
            .prefetch_related("documents", "status_history")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return OrderRequestCreateSerializer
        if self.action in ("update", "partial_update"):
            return OrderRequestUpdateSerializer
        return OrderRequestReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        target_price = validated_data.pop("target_price", {})
        validated_data.update(target_price)
        order_request = OrderRequestService.create_request(
            owner=request.user,
            validated_data=validated_data,
        )
        output = OrderRequestReadSerializer(order_request, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        target_price = validated_data.pop("target_price", None)
        if target_price is not None:
            validated_data.update(target_price)
        updated = OrderRequestService.update_request(instance, request.user, validated_data)
        output = OrderRequestReadSerializer(updated, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        OrderRequestService.deactivate_request(instance, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="reactivate")
    def reactivate(self, request, pk=None):
        instance = self.get_object()
        updated = OrderRequestService.reactivate_request(instance, request.user)
        output = OrderRequestReadSerializer(updated, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="documents",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_documents(self, request, pk=None):
        order_request = self.get_object()
        files = request.FILES.getlist("file") or request.FILES.getlist("files")
        if not files and request.FILES.get("file"):
            files = [request.FILES.get("file")]
        if not files:
            return Response({"detail": "file_required"}, status=status.HTTP_400_BAD_REQUEST)
        errors = []
        for file in files:
            error = _validate_request_document(file)
            if error:
                errors.append({"file": file.name, "error": error})
        if errors:
            return Response(
                {"detail": "invalid_files", "errors": errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        created = []
        for file in files:
            created.append(
                OrderRequestDocument.objects.create(
                    order_request=order_request,
                    uploaded_by=request.user,
                    name=file.name,
                    file=file,
                )
            )
        serializer = OrderRequestDocumentSerializer(
            created,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class WarehousePendingRequestListAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsWarehouseManager]
    serializer_class = OrderRequestReadSerializer

    def get_queryset(self):
        return (
            OrderRequest.all_objects.filter(
                type=OrderRequestType.SELL,
                status=OrderRequestStatus.PENDING_WAREHOUSE,
                is_active=True,
            )
            .select_related("owner", "category", "verified_by")
            .prefetch_related("documents", "status_history")
            .order_by("-created_at")
        )


class WarehouseVerifyAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsWarehouseManager]

    def post(self, request, request_id):
        serializer = WarehouseVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order_request = get_object_or_404(OrderRequest.all_objects, pk=request_id)
        decision = serializer.validated_data["decision"]
        reason = serializer.validated_data.get("reason", "")
        updated = OrderRequestService.verify_request(
            order_request=order_request,
            actor=request.user,
            approve=decision == "APPROVE",
            reason=reason,
        )
        output = OrderRequestReadSerializer(updated, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)


def _serialize_user_summary(user):
    if not user:
        return None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
    }


def _normalize_limit(raw_limit, default=50, max_limit=200):
    try:
        parsed = int(raw_limit)
    except (TypeError, ValueError):
        return default
    if parsed < 1:
        return default
    return min(parsed, max_limit)


def _collect_admin_activity_events(limit=50):
    events = []

    product_logs = ProductAuditLog.objects.select_related("actor_user").order_by("-created_at")[:limit]
    for log in product_logs:
        events.append(
            {
                "id": f"product-audit-{log.id}",
                "kind": "PRODUCT_AUDIT",
                "timestamp": log.created_at,
                "title": f"Product audit: {log.action}",
                "description": f"{log.action} on product '{log.product_name}'",
                "actor": _serialize_user_summary(log.actor_user),
                "subject": {
                    "type": "product",
                    "id": str(log.product_id) if log.product_id else None,
                    "name": log.product_name,
                },
                "meta": log.payload or {},
            }
        )

    audit_logs = OrderRequestAuditLog.objects.select_related(
        "actor_user", "order_request", "order_request__owner"
    ).order_by("-created_at")[:limit]
    for log in audit_logs:
        events.append(
            {
                "id": f"order-audit-{log.id}",
                "kind": "ORDER_REQUEST_AUDIT",
                "timestamp": log.created_at,
                "title": f"Order request audit: {log.action}",
                "description": (
                    f"Action '{log.action}' on request {log.order_request_id} "
                    f"owned by {getattr(log.order_request.owner, 'username', 'unknown')}"
                ),
                "actor": _serialize_user_summary(log.actor_user),
                "subject": {
                    "type": "order_request",
                    "id": str(log.order_request_id),
                },
                "meta": log.payload or {},
            }
        )

    status_history = OrderRequestStatusHistory.objects.select_related(
        "actor_user", "order_request", "order_request__owner"
    ).order_by("-at")[:limit]
    for history in status_history:
        events.append(
            {
                "id": f"order-status-{history.id}",
                "kind": "ORDER_REQUEST_STATUS",
                "timestamp": history.at,
                "title": f"Order status changed to {history.to_status}",
                "description": (
                    f"Request {history.order_request_id}: "
                    f"{history.from_status or 'NONE'} -> {history.to_status}"
                ),
                "actor": _serialize_user_summary(history.actor_user),
                "subject": {
                    "type": "order_request",
                    "id": str(history.order_request_id),
                },
                "meta": history.meta or {},
            }
        )

    kyc_requests = KYCRequest.objects.select_related("user").order_by("-submitted_at")[:limit]
    for kyc in kyc_requests:
        events.append(
            {
                "id": f"kyc-submitted-{kyc.id}",
                "kind": "KYC_SUBMITTED",
                "timestamp": kyc.submitted_at,
                "title": "KYC request submitted",
                "description": (
                    f"{kyc.user.username} submitted KYC for roles: "
                    f"{', '.join(kyc.requested_roles or []) or 'N/A'}"
                ),
                "actor": _serialize_user_summary(kyc.user),
                "subject": {"type": "kyc_request", "id": str(kyc.id)},
                "meta": {"requested_roles": kyc.requested_roles or []},
            }
        )
        if kyc.reviewed_at:
            events.append(
                {
                    "id": f"kyc-reviewed-{kyc.id}",
                    "kind": "KYC_REVIEWED",
                    "timestamp": kyc.reviewed_at,
                    "title": f"KYC request reviewed: {kyc.status}",
                    "description": (
                        f"KYC request {kyc.id} for {kyc.user.username} marked {kyc.status}"
                    ),
                    "actor": None,
                    "subject": {"type": "kyc_request", "id": str(kyc.id)},
                    "meta": {
                        "status": kyc.status,
                        "reject_reason": kyc.reject_reason or "",
                    },
                }
            )

    kyc_documents = KYCDocument.objects.select_related("kyc_request", "kyc_request__user").order_by(
        "-uploaded_at"
    )[:limit]
    for doc in kyc_documents:
        events.append(
            {
                "id": f"kyc-document-{doc.id}",
                "kind": "KYC_DOCUMENT_UPLOADED",
                "timestamp": doc.uploaded_at,
                "title": "KYC document uploaded",
                "description": (
                    f"Document '{doc.name}' uploaded for KYC request {doc.kyc_request_id} "
                    f"by {doc.kyc_request.user.username}"
                ),
                "actor": _serialize_user_summary(doc.kyc_request.user),
                "subject": {"type": "kyc_request", "id": str(doc.kyc_request_id)},
                "meta": {"document_id": doc.id, "document_name": doc.name},
            }
        )

    events.sort(key=lambda item: item["timestamp"], reverse=True)
    output = []
    for event in events[:limit]:
        output.append(
            {
                **event,
                "timestamp": event["timestamp"].isoformat() if event["timestamp"] else None,
            }
        )
    return output


class AdminDashboardSummaryAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def get(self, request):
        all_requests = OrderRequest.all_objects
        pending_kyc = KYCRequest.objects.filter(status=KYCStatus.PENDING).count()
        pending_warehouse = all_requests.filter(
            type=OrderRequestType.SELL,
            status=OrderRequestStatus.PENDING_WAREHOUSE,
            is_active=True,
        ).count()

        stats = {
            "users_total": User.objects.count(),
            "users_active": User.objects.filter(is_active=True).count(),
            "products_total": Product.objects.count(),
            "products_active": Product.objects.filter(is_active=True).count(),
            "products_inactive": Product.objects.filter(is_active=False).count(),
            "kyc_pending": pending_kyc,
            "kyc_approved": KYCRequest.objects.filter(status=KYCStatus.APPROVED).count(),
            "order_requests_total": all_requests.count(),
            "order_requests_active": all_requests.filter(is_active=True).count(),
            "warehouse_pending": pending_warehouse,
            "feed_visible": all_requests.public_feed().count(),
            "pending_admin_items": pending_kyc + pending_warehouse,
        }

        latest_order_requests = OrderRequestReadSerializer(
            all_requests.select_related("owner", "category", "verified_by")
            .prefetch_related("documents", "status_history")
            .order_by("-created_at")[:6],
            many=True,
            context={"request": request},
        ).data

        latest_kyc_requests = KYCRequestSerializer(
            KYCRequest.objects.select_related("user").prefetch_related("documents").order_by(
                "-submitted_at"
            )[:6],
            many=True,
            context={"request": request},
        ).data

        recent_activities = _collect_admin_activity_events(limit=10)

        return Response(
            {
                "stats": stats,
                "latest_order_requests": latest_order_requests,
                "latest_kyc_requests": latest_kyc_requests,
                "recent_activities": recent_activities,
            }
        )


class AdminActivityFeedAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def get(self, request):
        limit = _normalize_limit(request.query_params.get("limit"), default=50)
        kind = (request.query_params.get("kind") or "").strip().upper()
        events = _collect_admin_activity_events(limit=max(limit * 2, 60))
        if kind:
            events = [item for item in events if item["kind"] == kind]
        data = events[:limit]
        return Response({"count": len(data), "results": data})


class AdminOrderRequestViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]
    serializer_class = OrderRequestReadSerializer

    def get_queryset(self):
        queryset = (
            OrderRequest.all_objects.select_related("owner", "category", "verified_by")
            .prefetch_related("documents", "status_history", "audit_logs")
            .order_by("-created_at")
        )

        request_type = (self.request.query_params.get("type") or "").strip()
        status_param = (self.request.query_params.get("status") or "").strip()
        owner_id = (self.request.query_params.get("owner") or "").strip()
        is_active_param = (self.request.query_params.get("is_active") or "").strip().lower()
        search = (self.request.query_params.get("q") or "").strip()

        if request_type:
            queryset = queryset.filter(type=request_type)
        if status_param:
            queryset = queryset.filter(status=status_param)
        if owner_id:
            queryset = queryset.filter(owner_id=owner_id)
        if is_active_param in ("true", "false"):
            queryset = queryset.filter(is_active=(is_active_param == "true"))
        if search:
            queryset = queryset.filter(
                Q(product_title__icontains=search)
                | Q(notes__icontains=search)
                | Q(owner__username__icontains=search)
                | Q(owner__email__icontains=search)
            )
        return queryset

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        order_request = self.get_object()
        updated = OrderRequestService.deactivate_request(order_request, request.user)
        serializer = self.get_serializer(updated)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        order_request = self.get_object()
        updated = OrderRequestService.reactivate_request(order_request, request.user)
        serializer = self.get_serializer(updated)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        order_request = self.get_object()
        serializer = WarehouseVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = OrderRequestService.verify_request(
            order_request=order_request,
            actor=request.user,
            approve=serializer.validated_data["decision"] == "APPROVE",
            reason=serializer.validated_data.get("reason", ""),
        )
        output = self.get_serializer(updated)
        return Response(output.data, status=status.HTTP_200_OK)
