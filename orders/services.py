from django.db import transaction
from django.utils import timezone
from rest_framework import exceptions

from .models import (
    OfferStatus,
    Order,
    OrderOffer,
    OrderRequest,
    OrderRequestAuditLog,
    OrderRequestNotification,
    OrderRequestStatus,
    OrderRequestStatusHistory,
    OrderRequestType,
    OrderStatus,
    OrderStatusHistory,
    OrderType,
)


class OrderConflict(exceptions.APIException):
    status_code = 409
    default_code = "order_conflict"
    default_detail = "Order conflict."


class OrderRequestConflict(exceptions.APIException):
    status_code = 409
    default_code = "order_request_conflict"
    default_detail = "Order request conflict."


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
        order.price_agreed_amount = offer.price_total_amount
        order.price_agreed_currency = offer.price_total_currency
        if order.type == OrderType.BUY:
            order.assigned_provider = offer.offered_by
        elif order.type == OrderType.SELL:
            order.buyer = offer.offered_by
        order.save(
            update_fields=[
                "selected_offer",
                "assigned_provider",
                "buyer",
                "price_agreed_amount",
                "price_agreed_currency",
                "updated_at",
            ]
        )

        OrderStateService.transition(order, "accept_offer", actor)

    return order


class OrderRequestService:
    MATERIAL_FIELDS = {
        "category",
        "product_title",
        "grade",
        "dimensions",
        "quantity",
        "quantity_unit",
        "target_price_amount",
        "target_price_currency",
        "loading_city",
        "unloading_city",
        "loading_location",
        "unloading_location",
        "notes",
        "expires_at",
    }

    @classmethod
    def _audit(cls, order_request: OrderRequest, actor, action: str, payload=None):
        OrderRequestAuditLog.objects.create(
            order_request=order_request,
            action=action,
            actor_user=actor,
            payload=payload or {},
        )

    @classmethod
    def _history(cls, order_request: OrderRequest, actor, from_status, to_status, event, meta=None):
        OrderRequestStatusHistory.objects.create(
            order_request=order_request,
            from_status=from_status,
            to_status=to_status,
            event=event,
            actor_user=actor,
            meta=meta or {},
        )

    @classmethod
    def create_request(cls, owner, validated_data):
        request_type = validated_data.get("type")
        if request_type == OrderRequestType.BUY:
            initial_status = OrderRequestStatus.ACTIVE
        elif request_type == OrderRequestType.SELL:
            initial_status = OrderRequestStatus.PENDING_WAREHOUSE
        else:
            raise OrderRequestConflict("Unsupported request type.")

        with transaction.atomic():
            order_request = OrderRequest.all_objects.create(
                owner=owner,
                status=initial_status,
                is_active=True,
                **validated_data,
            )
            cls._history(
                order_request=order_request,
                actor=owner,
                from_status=None,
                to_status=initial_status,
                event="request_created",
                meta={"type": request_type},
            )
            cls._audit(
                order_request=order_request,
                actor=owner,
                action="request_created",
                payload={"type": request_type},
            )
        return order_request

    @classmethod
    def deactivate_request(cls, order_request: OrderRequest, actor):
        if order_request.status == OrderRequestStatus.DEACTIVATED and not order_request.is_active:
            return order_request
        from_status = order_request.status
        with transaction.atomic():
            order_request.status = OrderRequestStatus.DEACTIVATED
            order_request.is_active = False
            order_request.save(update_fields=["status", "is_active", "updated_at"])
            cls._history(
                order_request=order_request,
                actor=actor,
                from_status=from_status,
                to_status=OrderRequestStatus.DEACTIVATED,
                event="request_deactivated",
            )
            cls._audit(
                order_request=order_request,
                actor=actor,
                action="request_deactivated",
            )
        return order_request

    @classmethod
    def reactivate_request(cls, order_request: OrderRequest, actor):
        if order_request.is_active and order_request.status != OrderRequestStatus.DEACTIVATED:
            return order_request

        from_status = order_request.status
        update_fields = ["is_active", "status", "updated_at"]
        payload = {}

        if order_request.type == OrderRequestType.BUY:
            to_status = OrderRequestStatus.ACTIVE
            payload["requires_warehouse_verification"] = False
        elif order_request.type == OrderRequestType.SELL:
            to_status = OrderRequestStatus.PENDING_WAREHOUSE
            order_request.verified_by = None
            order_request.verified_at = None
            order_request.warehouse_reject_reason = ""
            update_fields.extend(["verified_by", "verified_at", "warehouse_reject_reason"])
            payload["requires_warehouse_verification"] = True
        else:
            raise OrderRequestConflict("Unsupported request type.")

        with transaction.atomic():
            order_request.is_active = True
            order_request.status = to_status
            order_request.save(update_fields=update_fields)
            cls._history(
                order_request=order_request,
                actor=actor,
                from_status=from_status,
                to_status=to_status,
                event="request_reactivated",
                meta=payload,
            )
            cls._audit(
                order_request=order_request,
                actor=actor,
                action="request_reactivated",
                payload=payload,
            )
        return order_request

    @classmethod
    def update_request(cls, order_request: OrderRequest, actor, validated_data):
        if validated_data.get("is_active") is False:
            return cls.deactivate_request(order_request, actor)

        reset_verification = False
        from_status = order_request.status
        changed_fields = []

        for field, value in validated_data.items():
            if field == "is_active":
                continue
            if getattr(order_request, field) != value:
                setattr(order_request, field, value)
                changed_fields.append(field)
                if field in cls.MATERIAL_FIELDS:
                    reset_verification = True

        update_fields = [*changed_fields]
        if (
            order_request.type == OrderRequestType.SELL
            and order_request.status == OrderRequestStatus.APPROVED
            and reset_verification
        ):
            order_request.status = OrderRequestStatus.PENDING_WAREHOUSE
            order_request.verified_by = None
            order_request.verified_at = None
            order_request.warehouse_reject_reason = ""
            update_fields.extend(
                ["status", "verified_by", "verified_at", "warehouse_reject_reason"]
            )

        if not update_fields:
            return order_request

        with transaction.atomic():
            order_request.save(update_fields=[*set(update_fields), "updated_at"])
            if from_status != order_request.status:
                cls._history(
                    order_request=order_request,
                    actor=actor,
                    from_status=from_status,
                    to_status=order_request.status,
                    event="request_resubmitted_for_warehouse",
                    meta={"changed_fields": changed_fields},
                )
            cls._audit(
                order_request=order_request,
                actor=actor,
                action="request_updated",
                payload={"changed_fields": changed_fields},
            )
        return order_request

    @classmethod
    def verify_request(cls, order_request: OrderRequest, actor, approve: bool, reason=""):
        if order_request.type != OrderRequestType.SELL:
            raise OrderRequestConflict("Warehouse verification is allowed only for SELL requests.")
        if order_request.status != OrderRequestStatus.PENDING_WAREHOUSE:
            raise OrderRequestConflict("Request is not pending warehouse verification.")

        from_status = order_request.status
        new_status = OrderRequestStatus.APPROVED if approve else OrderRequestStatus.REJECTED
        event = "warehouse_approved" if approve else "warehouse_rejected"

        with transaction.atomic():
            order_request.status = new_status
            order_request.verified_by = actor
            order_request.verified_at = timezone.now()
            order_request.warehouse_reject_reason = "" if approve else (reason or "")
            order_request.save(
                update_fields=[
                    "status",
                    "verified_by",
                    "verified_at",
                    "warehouse_reject_reason",
                    "updated_at",
                ]
            )
            cls._history(
                order_request=order_request,
                actor=actor,
                from_status=from_status,
                to_status=new_status,
                event=event,
                meta={"reason": order_request.warehouse_reject_reason},
            )
            cls._audit(
                order_request=order_request,
                actor=actor,
                action=event,
                payload={"reason": order_request.warehouse_reject_reason},
            )
            OrderRequestNotification.objects.create(
                order_request=order_request,
                user=order_request.owner,
                event=event,
                payload={
                    "status": new_status,
                    "reason": order_request.warehouse_reject_reason,
                },
            )
        return order_request
