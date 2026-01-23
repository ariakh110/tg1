from django.db import transaction
from rest_framework import exceptions

from .models import OfferStatus, Order, OrderOffer, OrderStatus, OrderStatusHistory, OrderType


class OrderConflict(exceptions.APIException):
    status_code = 409
    default_code = "order_conflict"
    default_detail = "Order conflict."


class OrderStateService:
    TRANSITIONS = {
        "accept_offer": {
            OrderStatus.OPEN: OrderStatus.OFFER_SELECTED,
        },
    }

    @classmethod
    def transition(cls, order: Order, event: str, actor, meta=None):
        allowed = cls.TRANSITIONS.get(event, {})
        if order.status not in allowed:
            raise OrderConflict(
                {
                    "error": {
                        "code": "ORDER_INVALID_STATUS",
                        "message": "This transition is not allowed.",
                        "details": {
                            "current_status": order.status,
                            "event": event,
                        },
                    }
                }
            )
        new_status = allowed[order.status]
        from_status = order.status
        order.status = new_status
        order.save(update_fields=["status", "updated_at"])
        OrderStatusHistory.objects.create(
            order=order,
            from_status=from_status,
            to_status=new_status,
            event=event,
            actor_user=actor,
            meta=meta or {},
        )
        return order


def accept_offer(offer: OrderOffer, actor):
    order = Order.objects.select_for_update().get(pk=offer.order_id)
    owner = order.owner
    if owner is None or (owner != actor and not actor.is_staff and not actor.is_superuser):
        raise exceptions.PermissionDenied("Only the order owner can accept offers.")
    if offer.status != OfferStatus.PENDING:
        raise OrderConflict("Offer is not pending.")

    with transaction.atomic():
        offer = OrderOffer.objects.select_for_update().get(pk=offer.pk)
        if offer.status != OfferStatus.PENDING:
            raise OrderConflict("Offer is not pending.")

        OrderOffer.objects.filter(order=order).exclude(pk=offer.pk).update(
            status=OfferStatus.DECLINED
        )
        offer.status = OfferStatus.ACCEPTED
        offer.save(update_fields=["status", "updated_at"])

        order.selected_offer = offer
        if order.type == OrderType.BUY:
            order.assigned_provider = offer.offered_by
        elif order.type == OrderType.SELL:
            order.buyer = offer.offered_by
        order.save(update_fields=["selected_offer", "assigned_provider", "buyer", "updated_at"])

        OrderStateService.transition(order, "accept_offer", actor)

    return order
