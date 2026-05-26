from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsAdminOrActiveAdminRole

from .models import StoreOrder, StoreOrderNotification, StoreOrderStatus, StorePayment, StorePaymentStatus
from .serializers import (
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
)
from .services import remaining_amount_for_order, set_order_status


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


class StoreOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            StoreOrder.objects.filter(buyer=self.request.user)
            .select_related("buyer")
            .prefetch_related("items", "status_history", "payments", "notifications")
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


class AdminStoreOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]
    serializer_class = StoreOrderReadSerializer
    http_method_names = ["get", "patch", "post", "head", "options"]

    def get_queryset(self):
        queryset = (
            StoreOrder.objects.select_related("buyer")
            .prefetch_related("items", "status_history", "payments", "notifications")
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
