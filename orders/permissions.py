from rest_framework import permissions

from accounts.models import RoleCode
from accounts.services import user_has_role
from .models import OrderStatus, OrderType


def get_order_owner(order):
    if order.type == OrderType.BUY:
        return order.buyer
    if order.type == OrderType.SELL:
        return order.assigned_provider
    return None


class IsOrderParticipant(permissions.BasePermission):
    message = "You are not a participant of this order."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True

        owner = get_order_owner(obj)
        if owner and owner == user:
            return True

        # accepted counterparty
        if obj.type == OrderType.BUY and obj.assigned_provider == user:
            return True
        if obj.type == OrderType.SELL and obj.buyer == user:
            return True

        if obj.status == OrderStatus.OPEN:
            if obj.type == OrderType.BUY and user_has_role(user, RoleCode.SELLER, require_active=True):
                return True
            if obj.type == OrderType.SELL and user_has_role(user, RoleCode.BUYER, require_active=True):
                return True

        return False


class IsOrderOwner(permissions.BasePermission):
    message = "Only the order owner can perform this action."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        owner = get_order_owner(obj)
        return owner == user


class IsOrderOfferParticipant(permissions.BasePermission):
    message = "Not allowed to access this offer."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        if obj.offered_by == user:
            return True
        owner = get_order_owner(obj.order)
        return owner == user
