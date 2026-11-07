from datetime import timedelta

from django.db.models import Count, F, Min, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrActiveAdminRole

from .automation import _single_active_sales_owner, process_automation_run
from .models import (
    CrmAutomationRun,
    CrmContactChannel,
    CrmFollowUp,
    CrmOpportunity,
    CrmSyncEvent,
    CrmTask,
    Customer,
    CustomerActivity,
    CustomerTransaction,
)
from .opportunities import opportunity_funnel_snapshot, process_sync_event, transition_opportunity
from .serializers import (
    CrmOpportunityDetailSerializer,
    CrmOpportunitySerializer,
    CrmOpportunityTransitionSerializer,
    CrmAutomationRunSerializer,
    CrmContactChannelSerializer,
    CrmFollowUpSerializer,
    CrmSyncEventSerializer,
    CrmTaskSerializer,
    CustomerActivitySerializer,
    CustomerDetailSerializer,
    CustomerSerializer,
    CustomerTransactionSerializer,
)

# پیگیریِ باز = تاریخِ پیگیری دارد و هنوز انجام نشده.
_OPEN_FOLLOW_UP = Q(activities__follow_up_at__isnull=False, activities__follow_up_done=False)
_OPEN_LEGACY_FOLLOW_UP = _OPEN_FOLLOW_UP & Q(activities__crm_follow_up__isnull=True)


class CrmCustomerPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class CustomerViewSet(viewsets.ModelViewSet):
    """مدیریتِ مشتریانِ CRM (فقط ادمین)."""

    permission_classes = [IsAdminOrActiveAdminRole]
    admin_sections = ("crm", "crm-funnel")
    pagination_class = CrmCustomerPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["stage", "source", "is_active", "product_interests"]
    search_fields = ["name", "phone", "company", "city"]
    ordering_fields = ["updated_at", "created_at", "name", "next_follow_up_at"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        queryset = Customer.objects.prefetch_related("product_interests").annotate(
            next_follow_up_at=Coalesce(
                Min("crm_follow_ups__due_at", filter=Q(crm_follow_ups__status=CrmFollowUp.STATUS_PENDING)),
                Min("activities__follow_up_at", filter=_OPEN_LEGACY_FOLLOW_UP),
            ),
            open_follow_up_count=(
                Count("crm_follow_ups", filter=Q(crm_follow_ups__status=CrmFollowUp.STATUS_PENDING), distinct=True)
                + Count("activities", filter=_OPEN_LEGACY_FOLLOW_UP, distinct=True)
            ),
        )
        if self.action == "retrieve":
            queryset = queryset.prefetch_related(
                "transactions", "activities", "opportunities", "contact_channels", "crm_follow_ups", "crm_tasks"
            )
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CustomerDetailSerializer
        return CustomerSerializer

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(created_by=user if getattr(user, "is_authenticated", False) else None)

    @action(detail=True, methods=["put"], url_path="contact-channels")
    def contact_channels(self, request, pk=None):
        customer = self.get_object()
        data = request.data if isinstance(request.data, dict) else {}
        channel = str(data.get("channel") or "").strip().lower()
        consent = str(data.get("consent") or "").strip().lower()
        valid_channels = {code for code, _label in CrmContactChannel.CHANNEL_CHOICES}
        valid_consents = {code for code, _label in CrmContactChannel.CONSENT_CHOICES}
        if channel not in valid_channels or consent not in valid_consents:
            return Response(
                {"detail": "کانال یا وضعیت رضایت معتبر نیست."}, status=status.HTTP_400_BAD_REQUEST
            )
        consented_at = timezone.now() if consent == CrmContactChannel.CONSENT_GRANTED else None
        contact_channel, _created = CrmContactChannel.objects.update_or_create(
            customer=customer,
            channel=channel,
            defaults={
                "consent": consent,
                "source": str(data.get("source") or "manual").strip()[:80] or "manual",
                "consented_at": consented_at,
                "updated_by": request.user if request.user.is_authenticated else None,
            },
        )
        return Response(CrmContactChannelSerializer(contact_channel).data)

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
        open_follow_ups = CrmFollowUp.objects.filter(status=CrmFollowUp.STATUS_PENDING).count() + CustomerActivity.objects.filter(
            follow_up_at__isnull=False, follow_up_done=False, crm_follow_up__isnull=True
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
        opportunity = serializer.save(
            created_by=user,
            owner=_single_active_sales_owner(),
            source_type=CrmOpportunity.SOURCE_MANUAL,
        )
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


class _DueAtActionSerializer(serializers.Serializer):
    due_at = serializers.DateTimeField()

    def validate_due_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("موعد تازه باید در آینده باشد.")
        return value


class _TaskResultSerializer(serializers.Serializer):
    result = serializers.CharField(required=False, allow_blank=True, max_length=4000, default="")


def _sync_activity_follow_up(activity, actor=None):
    existing = CrmFollowUp.objects.filter(source_activity=activity).first()
    if not activity.follow_up_at or activity.follow_up_done:
        if existing and existing.status == CrmFollowUp.STATUS_PENDING:
            existing.status = (
                CrmFollowUp.STATUS_COMPLETED if activity.follow_up_done else CrmFollowUp.STATUS_CANCELLED
            )
            existing.completed_at = activity.follow_up_done_at if activity.follow_up_done else None
            existing.save(update_fields=["status", "completed_at", "updated_at"])
        return existing

    channel_by_kind = {
        CustomerActivity.KIND_CALL: CrmFollowUp.CHANNEL_CALL,
        CustomerActivity.KIND_MESSAGE: CrmFollowUp.CHANNEL_SMS,
        CustomerActivity.KIND_MEETING: CrmFollowUp.CHANNEL_MEETING,
    }
    owner = actor if getattr(actor, "is_authenticated", False) else _single_active_sales_owner()
    follow_up, _created = CrmFollowUp.objects.update_or_create(
        source_activity=activity,
        defaults={
            "customer": activity.customer,
            "opportunity": activity.opportunity,
            "owner": owner,
            "title": (activity.follow_up_note or "پیگیری مشتری")[:255],
            "channel": channel_by_kind.get(activity.kind, CrmFollowUp.CHANNEL_OTHER),
            "due_at": activity.follow_up_at,
            "status": CrmFollowUp.STATUS_PENDING,
            "completed_at": None,
            "created_by": actor if getattr(actor, "is_authenticated", False) else None,
        },
    )
    if not follow_up.idempotency_key:
        follow_up.idempotency_key = f"activity:{activity.pk}:follow-up"[:180]
        follow_up.save(update_fields=["idempotency_key", "updated_at"])
    return follow_up


class CrmTaskViewSet(viewsets.ModelViewSet):
    serializer_class = CrmTaskSerializer
    permission_classes = [IsAdminOrActiveAdminRole]
    admin_sections = ("crm", "crm-sales")
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["customer", "opportunity", "status", "owner", "trigger"]
    ordering_fields = ["created_at", "due_at", "updated_at"]
    ordering = ["due_at", "created_at", "id"]

    def get_queryset(self):
        return CrmTask.objects.select_related("customer", "opportunity", "owner", "created_by")

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(owner=_single_active_sales_owner(), created_by=user)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        if task.status != CrmTask.STATUS_OPEN:
            return Response({"detail": "این کار باز نیست."}, status=status.HTTP_400_BAD_REQUEST)
        payload = _TaskResultSerializer(data=request.data if isinstance(request.data, dict) else {})
        payload.is_valid(raise_exception=True)
        task.status = CrmTask.STATUS_COMPLETED
        task.result = payload.validated_data["result"]
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "result", "completed_at", "updated_at"])
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=["post"])
    def snooze(self, request, pk=None):
        task = self.get_object()
        if task.status != CrmTask.STATUS_OPEN:
            return Response({"detail": "فقط کار باز را می‌توان جابه‌جا کرد."}, status=status.HTTP_400_BAD_REQUEST)
        payload = _DueAtActionSerializer(data=request.data if isinstance(request.data, dict) else {})
        payload.is_valid(raise_exception=True)
        task.due_at = payload.validated_data["due_at"]
        task.save(update_fields=["due_at", "updated_at"])
        return Response(self.get_serializer(task).data)


class CrmFollowUpViewSet(viewsets.ModelViewSet):
    serializer_class = CrmFollowUpSerializer
    permission_classes = [IsAdminOrActiveAdminRole]
    admin_sections = ("crm", "crm-sales", "crm-followups")
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["customer", "opportunity", "status", "owner", "channel"]
    ordering_fields = ["created_at", "due_at", "updated_at"]
    ordering = ["due_at", "created_at", "id"]

    def get_queryset(self):
        return CrmFollowUp.objects.select_related(
            "customer", "opportunity", "owner", "source_activity", "created_by"
        )

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(owner=_single_active_sales_owner(), created_by=user)

    def perform_update(self, serializer):
        follow_up = serializer.save()
        if follow_up.source_activity_id:
            CustomerActivity.objects.filter(pk=follow_up.source_activity_id).update(
                opportunity_id=follow_up.opportunity_id,
                follow_up_at=follow_up.due_at,
                follow_up_note=follow_up.title,
            )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        follow_up = self.get_object()
        if follow_up.status != CrmFollowUp.STATUS_PENDING:
            return Response({"detail": "این پیگیری باز نیست."}, status=status.HTTP_400_BAD_REQUEST)
        payload = _TaskResultSerializer(data=request.data if isinstance(request.data, dict) else {})
        payload.is_valid(raise_exception=True)
        follow_up.status = CrmFollowUp.STATUS_COMPLETED
        follow_up.result = payload.validated_data["result"]
        follow_up.completed_at = timezone.now()
        follow_up.save(update_fields=["status", "result", "completed_at", "updated_at"])
        if follow_up.source_activity_id:
            CustomerActivity.objects.filter(pk=follow_up.source_activity_id).update(
                follow_up_done=True, follow_up_done_at=follow_up.completed_at
            )
        return Response(self.get_serializer(follow_up).data)

    @action(detail=True, methods=["post"])
    def snooze(self, request, pk=None):
        follow_up = self.get_object()
        if follow_up.status != CrmFollowUp.STATUS_PENDING:
            return Response({"detail": "فقط پیگیری باز را می‌توان جابه‌جا کرد."}, status=status.HTTP_400_BAD_REQUEST)
        payload = _DueAtActionSerializer(data=request.data if isinstance(request.data, dict) else {})
        payload.is_valid(raise_exception=True)
        follow_up.due_at = payload.validated_data["due_at"]
        follow_up.save(update_fields=["due_at", "updated_at"])
        if follow_up.source_activity_id:
            CustomerActivity.objects.filter(pk=follow_up.source_activity_id).update(follow_up_at=follow_up.due_at)
        return Response(self.get_serializer(follow_up).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        follow_up = self.get_object()
        if follow_up.status != CrmFollowUp.STATUS_PENDING:
            return Response({"detail": "این پیگیری باز نیست."}, status=status.HTTP_400_BAD_REQUEST)
        follow_up.status = CrmFollowUp.STATUS_CANCELLED
        follow_up.save(update_fields=["status", "updated_at"])
        if follow_up.source_activity_id:
            CustomerActivity.objects.filter(pk=follow_up.source_activity_id).update(
                follow_up_done=True, follow_up_done_at=timezone.now()
            )
        return Response(self.get_serializer(follow_up).data)


class CrmAutomationRunViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CrmAutomationRunSerializer
    permission_classes = [IsAdminOrActiveAdminRole]
    admin_sections = ("crm", "crm-sales")
    pagination_class = None
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["status", "trigger"]
    ordering_fields = ["created_at", "updated_at", "attempts"]
    ordering = ["-created_at", "-id"]

    def get_queryset(self):
        return CrmAutomationRun.objects.select_related("customer", "opportunity")

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        run = self.get_object()
        if run.status != CrmAutomationRun.STATUS_FAILED:
            return Response({"detail": "فقط اجرای ناموفق را می‌توان دوباره امتحان کرد."}, status=400)
        run.status = CrmAutomationRun.STATUS_PENDING
        run.save(update_fields=["status", "updated_at"])
        run = process_automation_run(run)
        return Response(self.get_serializer(run).data, status=200 if run.status == CrmAutomationRun.STATUS_SUCCEEDED else 400)


class CrmWorkQueueView(APIView):
    permission_classes = [IsAdminOrActiveAdminRole]
    admin_sections = ("crm", "crm-sales", "crm-followups")

    @staticmethod
    def _bucket(due_at, now, *, needs_action=False):
        if needs_action:
            return "needs_action"
        if not due_at:
            return "unscheduled"
        local_due = timezone.localtime(due_at)
        today = now.date()
        if local_due.date() < today:
            return "overdue"
        if local_due.date() == today:
            return "today"
        return "upcoming"

    def get(self, request):
        now = timezone.localtime()
        buckets = {
            name: []
            for name in ("overdue", "today", "new_leads", "needs_action", "unscheduled", "upcoming")
        }

        tasks = CrmTask.objects.filter(status=CrmTask.STATUS_OPEN).select_related(
            "customer", "opportunity", "owner"
        )
        for task in tasks:
            row = dict(CrmTaskSerializer(task).data)
            row["item_type"] = "task"
            row["bucket"] = (
                "new_leads"
                if task.trigger == CrmAutomationRun.TRIGGER_CUSTOMER_CREATED and not task.due_at
                else self._bucket(task.due_at, now)
            )
            buckets[row["bucket"]].append(row)

        follow_ups = CrmFollowUp.objects.filter(status=CrmFollowUp.STATUS_PENDING).select_related(
            "customer", "opportunity", "owner", "source_activity"
        )
        for follow_up in follow_ups:
            row = dict(CrmFollowUpSerializer(follow_up).data)
            row["item_type"] = "follow_up"
            row["bucket"] = self._bucket(follow_up.due_at, now)
            buckets[row["bucket"]].append(row)

        legacy = CustomerActivity.objects.filter(
            follow_up_at__isnull=False, follow_up_done=False, crm_follow_up__isnull=True
        ).select_related("customer", "opportunity")
        for activity in legacy:
            row = dict(CustomerActivitySerializer(activity).data)
            row.update({"item_type": "legacy_follow_up", "title": activity.follow_up_note or "پیگیری مشتری"})
            row["bucket"] = self._bucket(activity.follow_up_at, now)
            buckets[row["bucket"]].append(row)

        open_opportunities = CrmOpportunity.objects.filter(
            is_active=True,
            stage__in=CrmOpportunity.OPEN_STAGES,
        ).filter(Q(next_action="") | Q(next_action__isnull=True)).select_related("customer")
        for opportunity in open_opportunities:
            has_task = CrmTask.objects.filter(opportunity=opportunity, status=CrmTask.STATUS_OPEN).exists()
            has_follow_up = CrmFollowUp.objects.filter(opportunity=opportunity, status=CrmFollowUp.STATUS_PENDING).exists()
            if has_task or has_follow_up:
                continue
            buckets["needs_action"].append(
                {
                    "id": opportunity.pk,
                    "item_type": "opportunity",
                    "bucket": "needs_action",
                    "customer": opportunity.customer_id,
                    "customer_name": opportunity.customer.name if opportunity.customer_id else "",
                    "customer_phone": opportunity.customer.phone if opportunity.customer_id else "",
                    "opportunity": opportunity.pk,
                    "opportunity_title": opportunity.title,
                    "title": f"برای فرصت «{opportunity.title}» اقدام بعدی تعیین نشده",
                    "due_at": opportunity.next_follow_up_at,
                    "source_type": opportunity.source_type,
                }
            )

        errors = CrmAutomationRun.objects.filter(status=CrmAutomationRun.STATUS_FAILED).select_related(
            "customer", "opportunity"
        )[:50]
        error_rows = CrmAutomationRunSerializer(errors, many=True).data
        counts = {key: len(value) for key, value in buckets.items()}
        counts["automation_errors"] = len(error_rows)
        return Response({**buckets, "automation_errors": error_rows, "counts": counts})


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

    queryset = CustomerActivity.objects.select_related("customer", "opportunity").all()
    serializer_class = CustomerActivitySerializer
    permission_classes = [IsAdminOrActiveAdminRole]
    admin_sections = ("crm", "crm-followups")
    pagination_class = None
    filterset_fields = ["customer", "kind", "follow_up_done"]

    def perform_create(self, serializer):
        actor = self.request.user if self.request.user.is_authenticated else None
        activity = serializer.save(created_by=actor)
        _sync_activity_follow_up(activity, actor)

    def perform_update(self, serializer):
        actor = self.request.user if self.request.user.is_authenticated else None
        activity = serializer.save()
        _sync_activity_follow_up(activity, actor)

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
            follow_up = CrmFollowUp.objects.filter(source_activity=activity).first()
            if follow_up and follow_up.status == CrmFollowUp.STATUS_PENDING:
                follow_up.status = CrmFollowUp.STATUS_COMPLETED
                follow_up.completed_at = activity.follow_up_done_at
                follow_up.save(update_fields=["status", "completed_at", "updated_at"])
        return Response(self.get_serializer(activity).data)
