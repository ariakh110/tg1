from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from accounts.models import RoleCode, UserRole
from accounts.permissions import IsAdminOrActiveAdminRole
from accounts.services import user_has_role

from .models import (
    FreightBidInvite,
    FreightBidInviteStatus,
    FreightBidSession,
    FreightBidStatus,
    StoreDeliveryAssignment,
    StoreDeliveryOffer,
    StoreDeliveryRequest,
    StoreDriverOperationalProfile,
    StoreBuyerAddress,
    StoreBuyerInvoiceProfile,
    StoreOrder,
    StoreOrderLoadingVehicle,
    StoreOrderNotification,
    StoreOrderStatus,
    StoreOrderWeighbridgeSlip,
    StorePayment,
    StorePaymentStatus,
)
from .serializers import (
    FreightBidOfferSubmitSerializer,
    FreightBidSessionCreateSerializer,
    FreightBidSessionReadSerializer,
    StoreBuyerAddressSerializer,
    StoreBuyerInvoiceProfileSerializer,
    StoreFinalWeightSerializer,
    StoreAdminQuoteSerializer,
    StoreOrderAdminUpdateSerializer,
    StoreOrderCreateSerializer,
    StoreOrderNotificationSerializer,
    StoreQuoteConfirmSerializer,
    StoreQuoteRejectSerializer,
    StorePaymentLinkSendSerializer,
    StorePaymentLinkSerializer,
    StoreOrderReadSerializer,
    StoreOrderTransitionSerializer,
    StorePaymentConfirmSerializer,
    StorePaymentSerializer,
    StoreDeliveryAssignmentSerializer,
    StoreDeliveryAssignmentTransitionSerializer,
    StoreDeliveryDocumentSerializer,
    StoreDeliveryDocumentUploadSerializer,
    StoreDeliveryDriverMatchRequestSerializer,
    StoreDeliveryDriverMatchSerializer,
    StoreDeliveryOfferResponseSerializer,
    StoreDeliveryOfferSerializer,
    StoreDeliveryReassignSerializer,
    StoreDeliveryRequestCreateSerializer,
    StoreDeliveryRequestSerializer,
    StoreDriverOperationalProfileSerializer,
    StoreOrderLoadingVehicleSerializer,
    StoreOrderWeighbridgeSlipSerializer,
    StoreOrderWeighbridgeSlipUploadSerializer,
)
from .services import (
    confirm_freight_bid,
    decline_freight_bid_invite,
    delivery_weight_kg_for_order,
    ensure_driver_operational_profile,
    mirror_first_loading_vehicle,
    reject_freight_bid,
    remaining_amount_for_order,
    required_driver_count_for_weight,
    set_order_status,
    start_freight_bid_session,
    submit_freight_bid_offer,
)


def _store_order_title(order):
    item = next(iter(order.items.all()), None)
    return item.product_name if item else str(order.id)


def _dashboard_notification(kind, severity, title, order, body, at=None, href="/account/payments"):
    return {
        "type": kind,
        "severity": severity,
        "title": title,
        "body": body,
        "order_id": str(order.id),
        "href": href,
        "created_at": at.isoformat() if at else None,
    }


class IsActiveLogisticsRecipientRole(permissions.BasePermission):
    message = "Active driver or carrier role is required."

    def has_permission(self, request, view):
        return (
            user_has_role(request.user, RoleCode.DRIVER, require_active=True)
            or user_has_role(request.user, RoleCode.CARRIER, require_active=True)
        )


def _delivery_request_queryset():
    return (
        StoreDeliveryRequest.objects.select_related("order", "order__buyer", "created_by")
        .prefetch_related(
            "order__items",
            "offers",
            "offers__driver",
            "offers__driver__store_driver_profile",
            "assignments",
            "assignments__driver",
            "assignments__documents",
            "assignments__events",
            "events",
        )
        .order_by("-created_at")
    )


class StoreBuyerAddressViewSet(viewsets.ModelViewSet):
    serializer_class = StoreBuyerAddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return StoreBuyerAddress.objects.filter(buyer=self.request.user).order_by("-is_default", "-updated_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class StoreBuyerInvoiceProfileViewSet(viewsets.ModelViewSet):
    serializer_class = StoreBuyerInvoiceProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return StoreBuyerInvoiceProfile.objects.filter(buyer=self.request.user).order_by("-is_default", "-updated_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class StoreOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            StoreOrder.objects.filter(buyer=self.request.user)
            .select_related("buyer")
            .prefetch_related("items", "status_history", "payments", "notifications", "loading_vehicles", "weighbridge_slips", "freight_bid_sessions__invites__carrier", "freight_bid_sessions__invites__offer", "freight_bid_sessions__winner_offer__invite__carrier")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return StoreOrderCreateSerializer
        return StoreOrderReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        output = StoreOrderReadSerializer(order, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        set_order_status(order, StoreOrderStatus.CANCELLED, "STORE_ORDER_CANCELLED_BY_BUYER", request.user)
        output = StoreOrderReadSerializer(order, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="confirm-quote")
    def confirm_quote(self, request, pk=None):
        order = self.get_object()
        serializer = StoreQuoteConfirmSerializer(data=request.data, context={"request": request, "order": order})
        serializer.is_valid(raise_exception=True)
        try:
            updated = serializer.save()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        output = StoreOrderReadSerializer(updated, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reject-quote")
    def reject_quote(self, request, pk=None):
        order = self.get_object()
        serializer = StoreQuoteRejectSerializer(data=request.data, context={"request": request, "order": order})
        serializer.is_valid(raise_exception=True)
        try:
            updated = serializer.save()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        output = StoreOrderReadSerializer(updated, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)


class StoreDashboardSummaryAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        orders = StoreOrder.objects.filter(buyer=request.user).prefetch_related("items")
        pending_payment = orders.filter(payment_status__in=[StorePaymentStatus.UNPAID, StorePaymentStatus.PENDING])
        active_pending_payment = pending_payment.exclude(
            status__in=[StoreOrderStatus.CANCELLED, StoreOrderStatus.EXPIRED, StoreOrderStatus.COMPLETED]
        )
        overdue = active_pending_payment.filter(payment_due_at__lt=now)
        price_expired = active_pending_payment.filter(price_valid_until__lt=now).exclude(price_valid_until__isnull=True)
        notifications = []
        for order in overdue.order_by("payment_due_at", "-created_at")[:5]:
            notifications.append(
                _dashboard_notification(
                    "payment_overdue",
                    "danger",
                    "مهلت تسویه گذشته است",
                    order,
                    f"{_store_order_title(order)} | مانده {remaining_amount_for_order(order):,} تومان",
                    at=order.payment_due_at,
                )
            )
        for order in price_expired.order_by("price_valid_until", "-created_at")[: max(0, 5 - len(notifications))]:
            notifications.append(
                _dashboard_notification(
                    "price_expired",
                    "danger",
                    "اعتبار قیمت تمام شده است",
                    order,
                    _store_order_title(order),
                    at=order.price_valid_until,
                    href=f"/account/orders/{order.id}",
                )
            )
        for order in active_pending_payment.filter(payment_due_at__gte=now).order_by("payment_due_at", "-created_at")[: max(0, 5 - len(notifications))]:
            notifications.append(
                _dashboard_notification(
                    "payment_pending",
                    "warning",
                    "تسویه در انتظار پرداخت است",
                    order,
                    f"{_store_order_title(order)} | مانده {remaining_amount_for_order(order):,} تومان",
                    at=order.payment_due_at,
                )
            )
        recent_system_notifications = (
            StoreOrderNotification.objects.filter(order__buyer=request.user)
            .select_related("order")
            .prefetch_related("order__items")
            .order_by("-created_at")[: max(0, 5 - len(notifications))]
        )
        for row in recent_system_notifications:
            notifications.append(
                _dashboard_notification(
                    "order_notification",
                    "info",
                    "پیام سفارش ثبت شد",
                    row.order,
                    _store_order_title(row.order),
                    at=row.created_at,
                    href=f"/account/orders/{row.order_id}",
                )
            )
        data = {
            "total_orders": orders.count(),
            "pending_payment_orders": pending_payment.count(),
            "overdue_payment_orders": overdue.count(),
            "expired_price_orders": price_expired.count(),
            "notification_count": len(notifications),
            "notifications": notifications,
            "completed_orders": orders.filter(status__in=[StoreOrderStatus.DELIVERED, StoreOrderStatus.COMPLETED]).count(),
            "active_orders": orders.exclude(
                status__in=[StoreOrderStatus.CANCELLED, StoreOrderStatus.EXPIRED, StoreOrderStatus.COMPLETED]
            ).count(),
            "total_paid_amount": sum(
                payment.amount
                for payment in StorePayment.objects.filter(order__buyer=request.user, status=StorePaymentStatus.PAID)
            ),
        }
        return Response(data, status=status.HTTP_200_OK)


class StorePaymentListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        payments = (
            StorePayment.objects.filter(order__buyer=request.user)
            .select_related("order")
            .prefetch_related("order__items")
            .order_by("-created_at")
        )
        serializer = StorePaymentSerializer(payments, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class StorePendingPaymentsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orders = (
            StoreOrder.objects.filter(
                buyer=request.user,
                payment_status__in=[StorePaymentStatus.UNPAID, StorePaymentStatus.PENDING],
            )
            .exclude(status__in=[StoreOrderStatus.CANCELLED, StoreOrderStatus.EXPIRED, StoreOrderStatus.COMPLETED])
            .select_related("buyer")
            .prefetch_related("items", "status_history", "payments", "notifications")
            .order_by("payment_due_at", "-created_at")
        )
        serializer = StoreOrderReadSerializer(orders, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class DriverOperationalProfileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveLogisticsRecipientRole]

    def get(self, request):
        profile = ensure_driver_operational_profile(request.user)
        serializer = StoreDriverOperationalProfileSerializer(profile, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        profile = ensure_driver_operational_profile(request.user)
        serializer = StoreDriverOperationalProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={"request": request, "allow_admin_fields": False},
        )
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        output = StoreDriverOperationalProfileSerializer(profile, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)


class AdminDriverOperationalProfileListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def get(self, request):
        for role in UserRole.objects.filter(role__in=[RoleCode.DRIVER, RoleCode.CARRIER], is_active=True).select_related("user"):
            ensure_driver_operational_profile(role.user)
        queryset = (
            StoreDriverOperationalProfile.objects.select_related("user", "verified_by")
            .prefetch_related("user__roles")
            .order_by("user__username", "user_id")
        )
        available = (request.query_params.get("available") or "").strip().lower()
        verified = (request.query_params.get("verified") or "").strip().lower()
        if available in {"1", "true", "yes"}:
            queryset = queryset.filter(is_available=True)
        if verified in {"1", "true", "yes"}:
            queryset = queryset.filter(is_verified=True)
        serializer = StoreDriverOperationalProfileSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminDriverOperationalProfileDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def patch(self, request, user_id):
        role = (
            UserRole.objects.select_related("user")
            .filter(user_id=user_id, role__in=[RoleCode.DRIVER, RoleCode.CARRIER])
            .order_by("role")
            .first()
        )
        if not role:
            return Response({"detail": "logistics_recipient_not_found"}, status=status.HTTP_404_NOT_FOUND)
        profile = ensure_driver_operational_profile(role.user)
        serializer = StoreDriverOperationalProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={"request": request, "allow_admin_fields": True},
        )
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        output = StoreDriverOperationalProfileSerializer(profile, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)


class AdminDeliveryDriverMatchAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def post(self, request):
        serializer = StoreDeliveryDriverMatchRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        rows = serializer.get_matches()
        output = StoreDeliveryDriverMatchSerializer(rows, many=True)
        return Response(output.data, status=status.HTTP_200_OK)


class AdminDeliveryRequestListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def get(self, request):
        queryset = _delivery_request_queryset()
        status_param = (request.query_params.get("status") or "").strip()
        order_id = (request.query_params.get("order") or "").strip()
        if status_param:
            queryset = queryset.filter(status=status_param)
        if order_id:
            queryset = queryset.filter(order_id=order_id)
        serializer = StoreDeliveryRequestSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = StoreDeliveryRequestCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        delivery_request = serializer.save()
        output = StoreDeliveryRequestSerializer(delivery_request, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class AdminDeliveryRequestReassignAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def post(self, request, pk):
        delivery_request = get_object_or_404(_delivery_request_queryset(), pk=pk)
        serializer = StoreDeliveryReassignSerializer(
            data=request.data,
            context={"request": request, "delivery_request": delivery_request},
        )
        serializer.is_valid(raise_exception=True)
        offers = serializer.save()
        output = StoreDeliveryOfferSerializer(offers, many=True, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class DriverLoadOfferListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveLogisticsRecipientRole]

    def get(self, request):
        offers = (
            StoreDeliveryOffer.objects.filter(driver=request.user)
            .select_related("request", "request__order", "request__order__buyer", "driver", "driver__store_driver_profile")
            .order_by("-created_at")
        )
        offer_status = (request.query_params.get("status") or "").strip()
        if offer_status:
            offers = offers.filter(status=offer_status)
        serializer = StoreDeliveryOfferSerializer(offers, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class DriverLoadOfferRespondAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveLogisticsRecipientRole]

    def post(self, request, pk):
        offer = get_object_or_404(
            StoreDeliveryOffer.objects.select_related("request", "driver").filter(driver=request.user),
            pk=pk,
        )
        serializer = StoreDeliveryOfferResponseSerializer(data=request.data, context={"request": request, "offer": offer})
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()
        if assignment:
            output = StoreDeliveryAssignmentSerializer(assignment, context={"request": request})
            return Response(output.data, status=status.HTTP_201_CREATED)
        offer.refresh_from_db()
        output = StoreDeliveryOfferSerializer(offer, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)


class DriverAssignmentListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveLogisticsRecipientRole]

    def get(self, request):
        assignments = (
            StoreDeliveryAssignment.objects.filter(driver=request.user)
            .select_related("request", "order", "driver")
            .prefetch_related("documents", "events")
            .order_by("-created_at")
        )
        assignment_status = (request.query_params.get("status") or "").strip()
        if assignment_status:
            assignments = assignments.filter(status=assignment_status)
        serializer = StoreDeliveryAssignmentSerializer(assignments, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class DriverAssignmentTransitionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveLogisticsRecipientRole]

    def post(self, request, pk):
        assignment = get_object_or_404(
            StoreDeliveryAssignment.objects.select_related("request", "order", "driver").filter(driver=request.user),
            pk=pk,
        )
        serializer = StoreDeliveryAssignmentTransitionSerializer(
            data=request.data,
            context={"request": request, "assignment": assignment},
        )
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()
        output = StoreDeliveryAssignmentSerializer(assignment, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)


class DriverAssignmentDocumentAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsActiveLogisticsRecipientRole]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        assignment = get_object_or_404(
            StoreDeliveryAssignment.objects.select_related("request", "driver").filter(driver=request.user),
            pk=pk,
        )
        serializer = StoreDeliveryDocumentUploadSerializer(
            data=request.data,
            context={"request": request, "assignment": assignment},
        )
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        output = StoreDeliveryDocumentSerializer(document, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class AdminStoreOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]
    serializer_class = StoreOrderReadSerializer
    http_method_names = ["get", "patch", "post", "head", "options"]

    def get_queryset(self):
        queryset = (
            StoreOrder.objects.select_related("buyer")
            .prefetch_related("items", "status_history", "payments", "notifications", "loading_vehicles", "weighbridge_slips", "freight_bid_sessions__invites__carrier", "freight_bid_sessions__invites__offer", "freight_bid_sessions__winner_offer__invite__carrier")
            .order_by("-created_at")
        )
        status_param = (self.request.query_params.get("status") or "").strip()
        payment_status = (self.request.query_params.get("payment_status") or "").strip()
        buyer_id = (self.request.query_params.get("buyer") or "").strip()
        search = (self.request.query_params.get("q") or "").strip()
        overdue = (self.request.query_params.get("overdue") or "").strip().lower()
        if status_param:
            queryset = queryset.filter(status=status_param)
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        if buyer_id:
            queryset = queryset.filter(buyer_id=buyer_id)
        if overdue in {"1", "true", "yes"}:
            queryset = queryset.filter(
                payment_due_at__lt=timezone.now(),
                payment_status__in=[StorePaymentStatus.UNPAID, StorePaymentStatus.PENDING],
            )
        if search:
            queryset = queryset.filter(
                Q(contact_name__icontains=search)
                | Q(contact_phone__icontains=search)
                | Q(buyer__username__icontains=search)
                | Q(buyer__email__icontains=search)
                | Q(items__product_name__icontains=search)
            )
        return queryset.distinct()

    def get_serializer_class(self):
        if self.action in {"partial_update", "update"}:
            return StoreOrderAdminUpdateSerializer
        return StoreOrderReadSerializer

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        output = StoreOrderReadSerializer(order, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        order = self.get_object()
        serializer = StoreOrderTransitionSerializer(
            data=request.data,
            context={"request": request, "order": order},
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        output = StoreOrderReadSerializer(updated, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="confirm-payment")
    def confirm_payment(self, request, pk=None):
        order = self.get_object()
        serializer = StorePaymentConfirmSerializer(
            data=request.data,
            context={"request": request, "order": order},
        )
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        output = StorePaymentSerializer(payment)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="payment-link")
    def payment_link(self, request, pk=None):
        order = self.get_object()
        serializer = StorePaymentLinkSerializer(data=request.data, context={"request": request, "order": order})
        serializer.is_valid(raise_exception=True)
        try:
            updated = serializer.save()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        output = StoreOrderReadSerializer(updated, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="send-payment-link")
    def send_payment_link(self, request, pk=None):
        order = self.get_object()
        serializer = StorePaymentLinkSendSerializer(data=request.data, context={"request": request, "order": order})
        serializer.is_valid(raise_exception=True)
        try:
            notification = serializer.save()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        output = StoreOrderNotificationSerializer(notification, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="final-weight")
    def final_weight(self, request, pk=None):
        order = self.get_object()
        serializer = StoreFinalWeightSerializer(data=request.data, context={"request": request, "order": order})
        serializer.is_valid(raise_exception=True)
        try:
            updated = serializer.save()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        output = StoreOrderReadSerializer(updated, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="quote")
    def quote(self, request, pk=None):
        order = self.get_object()
        serializer = StoreAdminQuoteSerializer(data=request.data, context={"request": request, "order": order})
        serializer.is_valid(raise_exception=True)
        try:
            updated = serializer.save()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        output = StoreOrderReadSerializer(updated, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)


class AdminStoreOrderLoadingVehicleListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def _get_order(self, pk):
        return get_object_or_404(StoreOrder, pk=pk)

    def get(self, request, pk):
        order = self._get_order(pk)
        vehicles = order.loading_vehicles.all()
        serializer = StoreOrderLoadingVehicleSerializer(vehicles, many=True)
        return Response(serializer.data)

    def post(self, request, pk):
        order = self._get_order(pk)
        serializer = StoreOrderLoadingVehicleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        next_sequence = (order.loading_vehicles.count() or 0) + 1
        vehicle = StoreOrderLoadingVehicle.objects.create(
            order=order,
            sequence=next_sequence,
            created_by=request.user,
            **{k: v for k, v in serializer.validated_data.items() if k not in ("sequence",)},
        )
        mirror_first_loading_vehicle(order)
        output = StoreOrderLoadingVehicleSerializer(vehicle)
        return Response(output.data, status=status.HTTP_201_CREATED)


class AdminStoreOrderLoadingVehicleDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def _get_vehicle(self, order_pk, vehicle_pk):
        return get_object_or_404(StoreOrderLoadingVehicle, pk=vehicle_pk, order_id=order_pk)

    def patch(self, request, pk, vehicle_pk):
        vehicle = self._get_vehicle(pk, vehicle_pk)
        serializer = StoreOrderLoadingVehicleSerializer(vehicle, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(vehicle, field, value)
        vehicle.save()
        mirror_first_loading_vehicle(vehicle.order)
        output = StoreOrderLoadingVehicleSerializer(vehicle)
        return Response(output.data)

    def delete(self, request, pk, vehicle_pk):
        vehicle = self._get_vehicle(pk, vehicle_pk)
        order = vehicle.order
        vehicle.delete()
        mirror_first_loading_vehicle(order)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminStoreOrderWeighbridgeSlipListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]
    parser_classes = [MultiPartParser, FormParser]

    def _get_order(self, pk):
        return get_object_or_404(StoreOrder, pk=pk)

    def get(self, request, pk):
        order = self._get_order(pk)
        slips = order.weighbridge_slips.all()
        serializer = StoreOrderWeighbridgeSlipSerializer(slips, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request, pk):
        order = self._get_order(pk)
        serializer = StoreOrderWeighbridgeSlipUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        vehicle = None
        vehicle_id = data.get("loading_vehicle_id")
        if vehicle_id:
            vehicle = get_object_or_404(StoreOrderLoadingVehicle, pk=vehicle_id, order=order)
        slip = StoreOrderWeighbridgeSlip.objects.create(
            order=order,
            loading_vehicle=vehicle,
            file=data["file"],
            slip_number=data.get("slip_number", ""),
            weight_kg=data.get("weight_kg"),
            note=data.get("note", ""),
            uploaded_by=request.user,
        )
        output = StoreOrderWeighbridgeSlipSerializer(slip, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class AdminStoreOrderWeighbridgeSlipDestroyAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def delete(self, request, pk, slip_pk):
        slip = get_object_or_404(StoreOrderWeighbridgeSlip, pk=slip_pk, order_id=pk)
        slip.file.delete(save=False)
        slip.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Freight Bidding Views ────────────────────────────────────────────────────

class AdminFreightBidSessionAPIView(APIView):
    """Admin: start a bid session (POST) or view current session (GET) for an order."""
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def _get_order(self, pk):
        return get_object_or_404(StoreOrder, pk=pk)

    def get(self, request, pk):
        order = self._get_order(pk)
        session = order.freight_bid_sessions.prefetch_related(
            "invites__carrier", "invites__offer", "winner_offer__invite__carrier"
        ).order_by("-created_at").first()
        if not session:
            return Response({"detail": "no_active_session"}, status=status.HTTP_404_NOT_FOUND)
        return Response(FreightBidSessionReadSerializer(session).data)

    def post(self, request, pk):
        order = self._get_order(pk)
        ser = FreightBidSessionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        carriers = list(User.objects.filter(id__in=ser.validated_data["carrier_ids"]))
        if len(carriers) != len(ser.validated_data["carrier_ids"]):
            return Response({"detail": "some_carriers_not_found"}, status=status.HTTP_400_BAD_REQUEST)
        session = start_freight_bid_session(
            order,
            carriers,
            ser.validated_data["deadline_at"],
            admin_note=ser.validated_data.get("admin_note", ""),
            created_by=request.user,
        )
        session.refresh_from_db()
        out = FreightBidSessionReadSerializer(
            FreightBidSession.objects.prefetch_related("invites__carrier", "invites__offer").get(pk=session.pk)
        )
        return Response(out.data, status=status.HTTP_201_CREATED)


class CarrierFreightBidInviteListAPIView(APIView):
    """Carrier: list own invites."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        invites = (
            FreightBidInvite.objects.filter(carrier=request.user)
            .select_related("session__order", "offer")
            .order_by("-invited_at")
        )
        data = []
        for inv in invites:
            offer_data = None
            if hasattr(inv, "offer"):
                offer_data = {"amount": str(inv.offer.amount), "note": inv.offer.note, "submitted_at": inv.offer.submitted_at}
            data.append({
                "id": str(inv.id),
                "status": inv.status,
                "session_id": str(inv.session_id),
                "session_status": inv.session.status,
                "deadline_at": inv.session.deadline_at,
                "order_id": str(inv.session.order_id),
                "order_summary": _store_order_title(inv.session.order),
                "invited_at": inv.invited_at,
                "responded_at": inv.responded_at,
                "offer": offer_data,
            })
        return Response(data)


class CarrierFreightBidOfferAPIView(APIView):
    """Carrier: submit offer (POST) or decline (DELETE) for a specific invite."""
    permission_classes = [permissions.IsAuthenticated]

    def _get_invite(self, request, invite_pk):
        return get_object_or_404(FreightBidInvite, pk=invite_pk, carrier=request.user)

    def post(self, request, invite_pk):
        invite = self._get_invite(request, invite_pk)
        ser = FreightBidOfferSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            offer = submit_freight_bid_offer(invite, ser.validated_data["amount"], ser.validated_data.get("note", ""))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": str(offer.id), "amount": str(offer.amount)}, status=status.HTTP_201_CREATED)

    def delete(self, request, invite_pk):
        invite = self._get_invite(request, invite_pk)
        try:
            decline_freight_bid_invite(invite)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)


class BuyerFreightBidConfirmAPIView(APIView):
    """Buyer: confirm or reject the awarded freight quote for their order."""
    permission_classes = [permissions.IsAuthenticated]

    def _get_session(self, request, pk):
        order = get_object_or_404(StoreOrder, pk=pk, buyer=request.user)
        session = order.freight_bid_sessions.filter(status=FreightBidStatus.AWARDED).order_by("-created_at").first()
        if not session:
            return None, order
        return session, order

    def post(self, request, pk):
        action_type = request.data.get("action")
        session, order = self._get_session(request, pk)
        if not session:
            return Response({"detail": "no_awarded_session"}, status=status.HTTP_404_NOT_FOUND)
        try:
            if action_type == "confirm":
                confirm_freight_bid(session)
            elif action_type == "reject":
                reject_freight_bid(session)
            else:
                return Response({"detail": "invalid_action"}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        return Response(StoreOrderReadSerializer(order, context={"request": request}).data)
