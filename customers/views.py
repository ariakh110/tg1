from datetime import timedelta

from django.db.models import Count, F, Min, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsAdminOrActiveAdminRole

from .models import CrmOpportunity, CrmSyncEvent, Customer, CustomerActivity, CustomerTransaction
from .opportunities import opportunity_funnel_snapshot, process_sync_event, transition_opportunity
from .serializers import (
    CrmOpportunityDetailSerializer,
    CrmOpportunitySerializer,
    CrmOpportunityTransitionSerializer,
    CrmSyncEventSerializer,
    CustomerActivitySerializer,
    CustomerDetailSerializer,
    CustomerSerializer,
    CustomerTransactionSerializer,
)

# پیگیریِ باز = تاریخِ پیگیری دارد و هنوز انجام نشده.
_OPEN_FOLLOW_UP = Q(activities__follow_up_at__isnull=False, activities__follow_up_done=False)


class CustomerViewSet(viewsets.ModelViewSet):
    """مدیریتِ مشتریانِ CRM (فقط ادمین)."""

    permission_classes = [IsAdminOrActiveAdminRole]
    admin_sections = ("crm", "crm-funnel")
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["stage", "source", "is_active"]
    search_fields = ["name", "phone", "company", "city"]
    ordering_fields = ["updated_at", "created_at", "name", "next_follow_up_at"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        return Customer.objects.annotate(
            next_follow_up_at=Min("activities__follow_up_at", filter=_OPEN_FOLLOW_UP),
            open_follow_up_count=Count("activities", filter=_OPEN_FOLLOW_UP),
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CustomerDetailSerializer
        return CustomerSerializer

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(created_by=user if getattr(user, "is_authenticated", False) else None)

    def perform_update(self, serializer):
        old_stage = serializer.instance.stage
        instance = serializer.save()
        if instance.stage != old_stage:
            labels = dict(Customer.STAGE_CHOICES)
            CustomerActivity.objects.create(
                customer=instance,
                kind=CustomerActivity.KIND_STAGE,
                body=f"مرحله: {labels.get(old_stage, old_stage)} ← {labels.get(instance.stage, instance.stage)}",
                stage_from=old_stage,
                stage_to=instance.stage,
                created_by=self.request.user if self.request.user.is_authenticated else None,
            )

    @action(detail=False, methods=["get"])
    def funnel(self, request):
        """خلاصهٔ قیفِ فروش + KPIها برای داشبورد (فقط ادمین)."""
        now = timezone.localtime()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        customers = Customer.objects.all()
        total = customers.count()
        by_stage = {row["stage"]: row["count"] for row in customers.values("stage").annotate(count=Count("id"))}
        stages = [
            {"code": code, "label": label, "count": by_stage.get(code, 0)}
            for code, label in Customer.STAGE_CHOICES
        ]
        won_count = sum(by_stage.get(code, 0) for code in Customer.STAGE_CLOSED_WON)
        conversion_rate = round(won_count / total, 4) if total else None

        # KPIهای دفترِ مانده
        T = CustomerTransaction
        total_sales = T.objects.filter(kind=T.KIND_PURCHASE).aggregate(s=Sum("amount"))["s"] or 0
        balanced = customers.annotate(
            _p=Coalesce(Sum("transactions__amount", filter=Q(transactions__kind=T.KIND_PURCHASE)), 0),
            _pay=Coalesce(Sum("transactions__amount", filter=Q(transactions__kind=T.KIND_PAYMENT)), 0),
            _adj=Coalesce(Sum("transactions__amount", filter=Q(transactions__kind=T.KIND_ADJUSTMENT)), 0),
        ).annotate(_bal=F("_p") - F("_pay") + F("_adj"))
        total_outstanding = balanced.filter(_bal__gt=0).aggregate(s=Sum("_bal"))["s"] or 0
        clv = round(total_sales / won_count) if won_count else None

        new_this_month = customers.filter(created_at__gte=month_start).count()
        open_follow_ups = CustomerActivity.objects.filter(
            follow_up_at__isnull=False, follow_up_done=False
        ).count()

        # KPIهای زمانی از تاریخچهٔ تغییرِ مرحله
        won_rows = (
            CustomerActivity.objects.filter(
                kind=CustomerActivity.KIND_STAGE, stage_to=Customer.STAGE_WON
            )
            .values("customer", "customer__created_at")
            .annotate(first_won=Min("occurred_at"))
        )
        deltas = [
            (r["first_won"] - r["customer__created_at"]).total_seconds()
            for r in won_rows
            if r["first_won"] and r["customer__created_at"]
        ]
        avg_cycle_days = round((sum(deltas) / len(deltas)) / 86400, 1) if deltas else None

        reached_proposal = (
            CustomerActivity.objects.filter(kind=CustomerActivity.KIND_STAGE, stage_to=Customer.STAGE_PROPOSAL)
            .values("customer")
            .distinct()
            .count()
        )
        reached_won = (
            CustomerActivity.objects.filter(kind=CustomerActivity.KIND_STAGE, stage_to=Customer.STAGE_WON)
            .values("customer")
            .distinct()
            .count()
        )
        quote_to_close = round(reached_won / reached_proposal, 4) if reached_proposal else None

        return Response(
            {
                "stages": stages,
                "total_customers": total,
                "won_count": won_count,
                "conversion_rate": conversion_rate,
                "total_sales": total_sales,
                "total_outstanding": total_outstanding,
                "clv": clv,
                "new_this_month": new_this_month,
                "open_follow_ups": open_follow_ups,
                "avg_cycle_days": avg_cycle_days,
                "quote_to_close": quote_to_close,
            }
        )


class CrmOpportunityViewSet(viewsets.ModelViewSet):
    """Independent site/manual sales opportunities without changing Customer.stage."""

    permission_classes = [IsAdminOrActiveAdminRole]
    admin_sections = ("crm", "crm-funnel")
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["stage", "source_type", "owner", "customer", "is_active"]
    search_fields = ["title", "customer__name", "customer__phone", "source_id", "need_details"]
    ordering_fields = [
        "updated_at",
        "created_at",
        "expected_value_irr",
        "probability",
        "next_follow_up_at",
    ]
    ordering = ["-updated_at"]

    def get_queryset(self):
        queryset = CrmOpportunity.objects.select_related("customer", "owner", "created_by")
        if self.action == "retrieve":
            queryset = queryset.prefetch_related("stage_history__actor_user")
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CrmOpportunityDetailSerializer
        return CrmOpportunitySerializer

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        opportunity = serializer.save(created_by=user, source_type=CrmOpportunity.SOURCE_MANUAL)
        transition_opportunity(
            opportunity,
            opportunity.stage,
            actor=user,
            event="CRM_OPPORTUNITY_CREATED",
            metadata={"origin": "admin_api"},
        )

    @action(detail=True, methods=["post"])
    def transition(self, request, pk=None):
        opportunity = self.get_object()
        if opportunity.source_type in {
            CrmOpportunity.SOURCE_STORE_ORDER,
            CrmOpportunity.SOURCE_ASSISTANT_INQUIRY,
        }:
            return Response(
                {"detail": "مرحله این فرصت از وضعیت سفارش یا استعلام سایت به‌روزرسانی می‌شود."},
                status=400,
            )
        input_serializer = CrmOpportunityTransitionSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        opportunity, _changed = transition_opportunity(
            opportunity,
            input_serializer.validated_data["stage"],
            actor=request.user,
            event="CRM_MANUAL_TRANSITION",
            reason=input_serializer.validated_data.get("reason", ""),
            metadata={"origin": "admin_api"},
        )
        return Response(CrmOpportunityDetailSerializer(opportunity, context=self.get_serializer_context()).data)

    @action(detail=False, methods=["get"])
    def funnel(self, request):
        return Response(opportunity_funnel_snapshot(self.filter_queryset(self.get_queryset())))


class CrmSyncEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Synchronization audit and retry surface for website-originated CRM events."""

    queryset = CrmSyncEvent.objects.all()
    serializer_class = CrmSyncEventSerializer
    permission_classes = [IsAdminOrActiveAdminRole]
    admin_sections = ("crm", "crm-funnel")
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "source_type", "source_id"]
    ordering_fields = ["created_at", "updated_at", "attempts"]
    ordering = ["-created_at"]

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        sync_event = self.get_object()
        opportunity = process_sync_event(sync_event)
        sync_event.refresh_from_db()
        payload = self.get_serializer(sync_event).data
        payload["opportunity_id"] = opportunity.pk if opportunity else None
        return Response(payload, status=200 if opportunity else 400)


class CustomerTransactionViewSet(viewsets.ModelViewSet):
    """تراکنش‌های دفترِ مشتری (خرید/پرداخت/تعدیل) — فقط ادمین."""

    queryset = CustomerTransaction.objects.select_related("customer").all()
    serializer_class = CustomerTransactionSerializer
    permission_classes = [IsAdminOrActiveAdminRole]
    admin_section = "crm"
    pagination_class = None
    filterset_fields = ["customer", "kind"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)


class CustomerActivityViewSet(viewsets.ModelViewSet):
    """تایم‌لاینِ تعامل‌ها و پیگیری‌های مشتری (تماس/پیام/جلسه/یادداشت) — فقط ادمین."""

    queryset = CustomerActivity.objects.select_related("customer").all()
    serializer_class = CustomerActivitySerializer
    permission_classes = [IsAdminOrActiveAdminRole]
    admin_sections = ("crm", "crm-followups")
    pagination_class = None
    filterset_fields = ["customer", "kind", "follow_up_done"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)

    @action(detail=False, methods=["get"])
    def follow_ups(self, request):
        """داشبوردِ پیگیری‌های باز در سه سطل: سررسیده / امروز / این هفته (۷ روزِ پیشِ‌رو)."""
        now = timezone.localtime()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        week_end = today_start + timedelta(days=7)

        base = (
            CustomerActivity.objects.select_related("customer")
            .filter(follow_up_at__isnull=False, follow_up_done=False)
            .order_by("follow_up_at")
        )
        overdue = base.filter(follow_up_at__lt=today_start)
        today = base.filter(follow_up_at__gte=today_start, follow_up_at__lt=today_end)
        upcoming = base.filter(follow_up_at__gte=today_end, follow_up_at__lt=week_end)

        return Response(
            {
                "overdue": self.get_serializer(overdue, many=True).data,
                "today": self.get_serializer(today, many=True).data,
                "upcoming": self.get_serializer(upcoming, many=True).data,
                "counts": {
                    "overdue": overdue.count(),
                    "today": today.count(),
                    "upcoming": upcoming.count(),
                },
            }
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """پیگیریِ این فعالیت را «انجام‌شده» علامت می‌زند (از داشبورد حذف، ولی روی تایم‌لاین می‌ماند)."""
        activity = self.get_object()
        if not activity.follow_up_at:
            return Response(
                {"detail": "این فعالیت پیگیریِ زمان‌بندی‌شده‌ای ندارد."},
                status=400,
            )
        if not activity.follow_up_done:
            activity.follow_up_done = True
            activity.follow_up_done_at = timezone.now()
            activity.save(update_fields=["follow_up_done", "follow_up_done_at", "updated_at"])
        return Response(self.get_serializer(activity).data)
