from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.models import RoleCode
from accounts.services import user_has_role
from .models import OfferStatus, Order, OrderOffer, OrderStatus, OrderType
from .permissions import IsOrderOfferParticipant, IsOrderOwner, IsOrderParticipant
from .serializers import (
    OrderCreateSerializer,
    OrderOfferCreateSerializer,
    OrderOfferReadSerializer,
    OrderReadSerializer,
    OrderStatusHistorySerializer,
)
from .services import accept_offer


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
