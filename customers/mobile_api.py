"""Role-scoped CRM endpoints for the standalone mobile companion."""

import re
from urllib.parse import urlsplit
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import RoleCode, UserRole
from accounts.permissions import IsAdminOrActiveAdminRole, IsFullAdminUser

from .models import (
    CrmFollowUp,
    CrmCustomerMobilePreference,
    CrmMobileCallCapture,
    CrmMobileCallPolicy,
    CrmMobileCallPolicyRevision,
    CrmOpportunity,
    CrmTask,
    Customer,
    CustomerActivity,
    CustomerAssignmentHistory,
)
from .serializers import CustomerProfileSerializer
from .services import normalize_phone

MOBILE_CRM_ROLES = (RoleCode.ADMIN, RoleCode.MARKETER, RoleCode.CRM_SALES)
POLICY_LOCKED_ROLES = (RoleCode.BUYER, RoleCode.SELLER)


def effective_mobile_role(user):
    if not user or not user.is_authenticated or not user.is_active:
        return None
    if user.is_superuser:
        return RoleCode.ADMIN
    roles = set(UserRole.objects.filter(user=user, is_active=True).values_list("role", flat=True))
    # CRM_SALES is deliberately the least-privilege choice when a user has
    # multiple active roles, including Django staff access.
    if RoleCode.CRM_SALES in roles:
        return RoleCode.CRM_SALES
    if user.is_staff or RoleCode.ADMIN in roles:
        return RoleCode.ADMIN
    for role in (RoleCode.MARKETER,):
        if role in roles:
            return role
    return None


def _customer_scope(user, role_code=None):
    role_code = role_code or effective_mobile_role(user)
    customers = Customer.objects.all()
    if role_code == RoleCode.CRM_SALES:
        customers = customers.filter(assigned_to=user)
    return customers


def _ensure_policy(role_code):
    default_mode = CrmMobileCallPolicy.MODE_OFF if role_code in POLICY_LOCKED_ROLES else CrmMobileCallPolicy.MODE_ASK
    policy, _created = CrmMobileCallPolicy.objects.get_or_create(
        role_code=role_code,
        defaults={"mode": default_mode, "default_action": CrmMobileCallPolicy.ACTION_DISCARD},
    )
    CrmMobileCallPolicyRevision.objects.get_or_create(
        policy=policy,
        revision=policy.revision,
        defaults={"mode": policy.mode, "default_action": policy.default_action},
    )
    return policy


def _policy_data(policy):
    return {
        "role_code": policy.role_code,
        "mode": policy.mode,
        "default_action": policy.default_action,
        "revision": policy.revision,
        "updated_at": policy.updated_at,
    }


class IsMobileCRMUser(IsAuthenticated):
    message = "An active CRM role is required."

    def has_permission(self, request, view):
        return super().has_permission(request, view) and effective_mobile_role(request.user) in MOBILE_CRM_ROLES


class MobileRoleAPIView(APIView):
    permission_classes = [IsMobileCRMUser]

    @property
    def role_code(self):
        return effective_mobile_role(self.request.user)


class MobileMeView(MobileRoleAPIView):
    def get(self, request):
        policy = _ensure_policy(self.role_code)
        return Response({
            "user_id": request.user.pk,
            "display_name": (request.user.get_full_name() or "").strip() or request.user.get_username(),
            "role_code": self.role_code,
            "policy": _policy_data(policy),
        })


class MobilePolicyView(MobileRoleAPIView):
    def get(self, request):
        return Response(_policy_data(_ensure_policy(self.role_code)))


class MobileCustomerListView(MobileRoleAPIView):
    class Pagination(PageNumberPagination):
        page_size = 30
        page_size_query_param = "page_size"
        max_page_size = 100

    def get(self, request):
        queryset = (
            _customer_scope(request.user, self.role_code)
            .annotate(
                mobile_is_favorite=Exists(
                    CrmCustomerMobilePreference.objects.filter(
                        customer_id=OuterRef("pk"), user=request.user, is_favorite=True
                    )
                )
            )
            .select_related("assigned_to")
            .order_by("name", "id")
        )
        if request.query_params.get("favorites", "").lower() in {"1", "true", "yes"}:
            queryset = queryset.filter(mobile_is_favorite=True)
        query = (request.query_params.get("q") or "").strip()
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(phone__icontains=query)
                | Q(company__icontains=query)
            )
        paginator = self.Pagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        rows = [self._summary(customer) for customer in page]
        return paginator.get_paginated_response(rows)

    @staticmethod
    def _summary(customer):
        return {
            "id": customer.pk,
            "name": customer.name,
            "phone": customer.phone,
            "company": customer.company,
            "job_title": customer.job_title,
            "decision_role": customer.decision_role,
            "city": customer.city,
            "stage": customer.stage,
            "stage_display": customer.get_stage_display(),
            "balance": customer.balance,
            "assigned_to": customer.assigned_to_id,
            "extra_phones": customer.extra_phones or [],
            "is_favorite": bool(getattr(customer, "mobile_is_favorite", False)),
        }


class MobileCustomerDetailView(MobileRoleAPIView):
    def patch(self, request, pk):
        with transaction.atomic():
            customer = get_object_or_404(
                _customer_scope(request.user, self.role_code).select_for_update(), pk=pk
            )
            profile = CustomerProfileSerializer(customer, data=request.data, partial=True)
            profile.is_valid(raise_exception=True)
            profile.save()
        return Response(profile.data)

    def get(self, request, pk):
        customer = get_object_or_404(
            _customer_scope(request.user, self.role_code).annotate(
                mobile_is_favorite=Exists(
                    CrmCustomerMobilePreference.objects.filter(
                        customer_id=OuterRef("pk"), user=request.user, is_favorite=True
                    )
                )
            ),
            pk=pk,
        )
        mobile_preferences = CrmCustomerMobilePreference.objects.filter(
            customer=customer, user=request.user
        ).first()
        own_only = self.role_code == RoleCode.CRM_SALES
        transactions = customer.transactions.order_by("-occurred_at", "-created_at", "-id")[:100]
        activities = customer.activities.select_related("created_by").order_by("-occurred_at", "-id")[:100]
        tasks = customer.crm_tasks.select_related("owner", "customer").order_by("due_at", "created_at", "id")
        follow_ups = customer.crm_follow_ups.select_related("owner", "customer").order_by("due_at", "created_at", "id")
        opportunities = customer.opportunities.select_related("owner", "customer").order_by("-updated_at", "-id")
        if own_only:
            tasks = tasks.filter(owner=request.user)
            follow_ups = follow_ups.filter(owner=request.user)
            opportunities = opportunities.filter(owner=request.user)
        return Response({
            **MobileCustomerListView._summary(customer),
            "province": customer.province,
            "note": customer.note,
            "source": customer.source,
            "mobile_links": {
                "bale": mobile_preferences.bale_chat_url if mobile_preferences else "",
                "rubika": mobile_preferences.rubika_chat_url if mobile_preferences else "",
            },
            "created_at": customer.created_at,
            "updated_at": customer.updated_at,
            "transactions": [self._transaction(row) for row in transactions],
            "activities": [self._activity(row) for row in activities],
            "tasks": [self._task(row) for row in tasks],
            "follow_ups": [self._follow_up(row) for row in follow_ups],
            "opportunities": [self._opportunity(row) for row in opportunities],
        })

    @staticmethod
    def _transaction(row):
        return {
            "id": row.pk,
            "kind": row.kind,
            "kind_display": row.get_kind_display(),
            "amount": row.amount,
            "description": row.description,
            "occurred_at": row.occurred_at,
            "created_at": row.created_at,
        }

    @staticmethod
    def _activity(row):
        return {
            "id": row.pk,
            "kind": row.kind,
            "channel": row.channel,
            "direction": row.direction,
            "result": row.result,
            "body": row.body,
            "occurred_at": row.occurred_at,
            "follow_up_at": row.follow_up_at,
            "follow_up_note": row.follow_up_note,
            "created_by": row.created_by_id,
        }

    @staticmethod
    def _task(row):
        return {
            "id": row.pk,
            "customer": row.customer_id,
            "customer_name": row.customer.name if row.customer_id else "",
            "opportunity": row.opportunity_id,
            "source_order_id": row.source_order_id,
            "title": row.title,
            "description": row.description,
            "due_at": row.due_at,
            "status": row.status,
            "result": row.result,
            "owner": row.owner_id,
        }

    @staticmethod
    def _follow_up(row):
        return {
            "id": row.pk,
            "customer": row.customer_id,
            "customer_name": row.customer.name if row.customer_id else "",
            "opportunity": row.opportunity_id,
            "title": row.title,
            "channel": row.channel,
            "due_at": row.due_at,
            "status": row.status,
            "result": row.result,
            "owner": row.owner_id,
        }

    @staticmethod
    def _opportunity(row):
        return {
            "id": row.pk,
            "customer": row.customer_id,
            "customer_name": row.customer.name if row.customer_id else "",
            "title": row.title,
            "source_type": row.source_type,
            "source_id": row.source_id,
            "source_status": row.source_status,
            "stage": row.stage,
            "stage_display": row.get_stage_display(),
            "need_details": row.need_details,
            "next_action": row.next_action,
            "next_follow_up_at": row.next_follow_up_at,
            "owner": row.owner_id,
        }


class MobileWorkView(MobileRoleAPIView):
    def get(self, request):
        customer_filter = Customer.objects.all()
        if self.role_code == RoleCode.CRM_SALES:
            customer_filter = customer_filter.filter(assigned_to=request.user)
        owned_work_scope = Q(customer__isnull=True) | Q(customer__in=customer_filter)
        tasks = CrmTask.objects.filter(
            owner=request.user, status=CrmTask.STATUS_OPEN
        ).filter(owned_work_scope).select_related("customer")
        follow_ups = CrmFollowUp.objects.filter(
            owner=request.user, status=CrmFollowUp.STATUS_PENDING
        ).filter(owned_work_scope).select_related("customer")
        opportunities = CrmOpportunity.objects.filter(
            owner=request.user,
            stage__in=CrmOpportunity.OPEN_STAGES,
        ).filter(owned_work_scope).select_related("customer")
        return Response({
            "tasks": [MobileCustomerDetailView._task(row) for row in tasks.order_by("due_at", "created_at", "id")],
            "follow_ups": [MobileCustomerDetailView._follow_up(row) for row in follow_ups.order_by("due_at", "created_at", "id")],
            "opportunities": [MobileCustomerDetailView._opportunity(row) for row in opportunities.order_by("-updated_at", "-id")],
        })


class MobileTaskCreateSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    opportunity_id = serializers.IntegerField(required=False, allow_null=True)
    title = serializers.CharField(max_length=240)
    description = serializers.CharField(required=False, allow_blank=True, max_length=4000, default="")
    due_at = serializers.DateTimeField(required=False, allow_null=True)


class MobileTaskCreateView(MobileRoleAPIView):
    def post(self, request):
        payload = MobileTaskCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        customers = _customer_scope(request.user, self.role_code)
        customer = customers.filter(pk=data["customer_id"]).first()
        if not customer:
            raise NotFound()
        opportunity = None
        if data.get("opportunity_id") is not None:
            opportunity = CrmOpportunity.objects.filter(
                pk=data["opportunity_id"], customer=customer
            ).first()
            if not opportunity or (
                self.role_code == RoleCode.CRM_SALES and opportunity.owner_id != request.user.pk
            ):
                raise NotFound()
        task = CrmTask.objects.create(
            customer=customer,
            opportunity=opportunity,
            owner=request.user,
            created_by=request.user,
            title=data["title"].strip(),
            description=data.get("description", "").strip(),
            due_at=data.get("due_at"),
            trigger="mobile.manual",
        )
        return Response(MobileCustomerDetailView._task(task), status=status.HTTP_201_CREATED)


class MobileTaskActionView(MobileRoleAPIView):
    def post(self, request, pk, action_name):
        customer_filter = Customer.objects.all()
        if self.role_code == RoleCode.CRM_SALES:
            customer_filter = customer_filter.filter(assigned_to=request.user)
        task = get_object_or_404(
            CrmTask.objects.filter(owner=request.user)
            .filter(Q(customer__isnull=True) | Q(customer__in=customer_filter)),
            pk=pk,
        )
        if task.status != CrmTask.STATUS_OPEN:
            return Response({"detail": "این کار باز نیست."}, status=status.HTTP_409_CONFLICT)
        if action_name == "complete":
            result = serializers.CharField(required=False, allow_blank=True, max_length=4000).run_validation(
                request.data.get("result", "")
            )
            task.status = CrmTask.STATUS_COMPLETED
            task.result = result
            task.completed_at = timezone.now()
            task.save(update_fields=["status", "result", "completed_at", "updated_at"])
        elif action_name == "snooze":
            due_at = serializers.DateTimeField().run_validation(request.data.get("due_at"))
            task.due_at = due_at
            task.save(update_fields=["due_at", "updated_at"])
        else:
            return Response({"detail": "عملیات نامعتبر است."}, status=status.HTTP_404_NOT_FOUND)
        return Response(MobileCustomerDetailView._task(task))


class MobileCustomerPreferenceSerializer(serializers.Serializer):
    is_favorite = serializers.BooleanField(required=False)
    bale_chat_url = serializers.CharField(max_length=500, required=False, allow_blank=True)
    rubika_chat_url = serializers.CharField(max_length=500, required=False, allow_blank=True)

    @staticmethod
    def _safe_chat_url(value, default_host, allowed_hosts):
        value = (value or "").strip()
        if not value:
            return ""
        if value.startswith("@"):
            value = value[1:]
        if not re.match(r"^https?://", value, flags=re.IGNORECASE):
            host = value.split("/", 1)[0].lower()
            value = f"https://{value}" if host in allowed_hosts else f"https://{default_host}/{value.lstrip('/')}"
        parsed = urlsplit(value)
        try:
            port = parsed.port
        except ValueError as error:
            raise serializers.ValidationError("شمارهٔ درگاه در لینک معتبر نیست.") from error
        if (
            parsed.scheme.lower() != "https"
            or parsed.hostname not in allowed_hosts
            or parsed.username
            or parsed.password
            or port not in (None, 443)
        ):
            raise serializers.ValidationError("لینک باید HTTPS و متعلق به پیام‌رسان انتخاب‌شده باشد.")
        return value

    def validate_bale_chat_url(self, value):
        return self._safe_chat_url(value, "ble.ir", {"ble.ir", "web.bale.ai"})

    def validate_rubika_chat_url(self, value):
        return self._safe_chat_url(value, "rubika.ir", {"rubika.ir", "web.rubika.ir"})

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("حداقل یک تنظیم را ارسال کنید.")
        return attrs


class MobileCustomerPreferenceView(MobileRoleAPIView):
    def patch(self, request, pk):
        customer = get_object_or_404(_customer_scope(request.user, self.role_code), pk=pk)
        serializer = MobileCustomerPreferenceSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        preference, _created = CrmCustomerMobilePreference.objects.get_or_create(
            customer=customer,
            user=request.user,
        )
        for field, value in serializer.validated_data.items():
            setattr(preference, field, value)
        if (
            not preference.is_favorite
            and not preference.bale_chat_url
            and not preference.rubika_chat_url
        ):
            preference.delete()
            return Response({"is_favorite": False, "bale_chat_url": "", "rubika_chat_url": ""})
        preference.save(update_fields=[*serializer.validated_data.keys(), "updated_at"])
        return Response({
            "is_favorite": preference.is_favorite,
            "bale_chat_url": preference.bale_chat_url,
            "rubika_chat_url": preference.rubika_chat_url,
        })


class MobileActivityCreateSerializer(serializers.Serializer):
    event_uuid = serializers.UUIDField()
    customer_id = serializers.IntegerField()
    channel = serializers.ChoiceField(choices=CustomerActivity.CHANNEL_CHOICES)
    direction = serializers.ChoiceField(
        choices=[("inbound", "دریافتی"), ("outbound", "ارسالی")], default="outbound"
    )
    result = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    body = serializers.CharField(min_length=1, max_length=4000, trim_whitespace=True)
    occurred_at = serializers.DateTimeField(required=False)
    follow_up_at = serializers.DateTimeField(required=False, allow_null=True)
    follow_up_note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class MobileActivityCreateView(MobileRoleAPIView):
    def post(self, request):
        serializer = MobileActivityCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        customer = get_object_or_404(
            _customer_scope(request.user, self.role_code), pk=data["customer_id"]
        )
        event_uuid = data["event_uuid"]
        defaults = {
            "customer": customer,
            "created_by": request.user,
            "kind": CustomerActivity.KIND_CALL
            if data["channel"] == CustomerActivity.CHANNEL_PHONE
            else CustomerActivity.KIND_MESSAGE,
            "channel": data["channel"],
            "direction": data["direction"],
            "result": data.get("result", "").strip(),
            "body": data["body"].strip(),
            "occurred_at": data.get("occurred_at") or timezone.now(),
            "follow_up_at": data.get("follow_up_at"),
            "follow_up_note": data.get("follow_up_note", "").strip(),
        }
        if defaults["follow_up_at"] and not defaults["follow_up_note"]:
            defaults["follow_up_note"] = "پیگیری مشتری"

        with transaction.atomic():
            activity, created = CustomerActivity.objects.get_or_create(
                mobile_event_uuid=event_uuid,
                defaults=defaults,
            )
            if activity.created_by_id != request.user.pk:
                raise NotFound()
            if activity.customer_id != customer.pk:
                raise NotFound()
            follow_up = None
            if created and activity.follow_up_at:
                follow_up_channel = {
                    CustomerActivity.CHANNEL_PHONE: CrmFollowUp.CHANNEL_CALL,
                    CustomerActivity.CHANNEL_WHATSAPP: CrmFollowUp.CHANNEL_WHATSAPP,
                    CustomerActivity.CHANNEL_TELEGRAM: CrmFollowUp.CHANNEL_TELEGRAM,
                    CustomerActivity.CHANNEL_BALE: CrmFollowUp.CHANNEL_BALE,
                    CustomerActivity.CHANNEL_RUBIKA: CrmFollowUp.CHANNEL_RUBIKA,
                    CustomerActivity.CHANNEL_OTHER: CrmFollowUp.CHANNEL_OTHER,
                }[activity.channel]
                follow_up, _follow_created = CrmFollowUp.objects.get_or_create(
                    idempotency_key=f"mobile-activity:{event_uuid}",
                    defaults={
                        "customer": customer,
                        "owner": request.user,
                        "source_activity": activity,
                        "title": activity.follow_up_note,
                        "channel": follow_up_channel,
                        "due_at": activity.follow_up_at,
                        "created_by": request.user,
                    },
                )
            elif activity.follow_up_at:
                follow_up = CrmFollowUp.objects.filter(source_activity=activity).first()

        return Response(
            {
                "activity": MobileCustomerDetailView._activity(activity),
                "follow_up_id": follow_up.pk if follow_up else None,
                "replayed": not created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MobileCallCaptureSerializer(serializers.Serializer):
    event_uuid = serializers.UUIDField()
    source = serializers.ChoiceField(choices=[("MANUAL", "MANUAL"), ("CALL_LOG", "CALL_LOG")], default="MANUAL")
    role_code = serializers.ChoiceField(choices=[(role, role) for role in MOBILE_CRM_ROLES])
    policy_revision = serializers.IntegerField(min_value=1)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    customer_id = serializers.IntegerField(required=False, allow_null=True)
    customer_profile = CustomerProfileSerializer(required=False, partial=True)
    direction = serializers.ChoiceField(choices=CrmMobileCallCapture.DIRECTION_CHOICES)
    outcome = serializers.CharField(max_length=32, required=False, allow_blank=True, default="other")
    duration_seconds = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    call_at = serializers.DateTimeField()
    consented_at = serializers.DateTimeField()
    summary = serializers.CharField(min_length=1, max_length=4000, trim_whitespace=True)
    next_action = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    next_due_at = serializers.DateTimeField(required=False, allow_null=True)


def _consent_revision(policy, revision_number, consented_at):
    revision = CrmMobileCallPolicyRevision.objects.filter(
        policy=policy, revision=revision_number
    ).first()
    if not revision or revision.mode != CrmMobileCallPolicy.MODE_ASK:
        raise serializers.ValidationError({"policy_revision": "سیاست ثبت تماس برای این رضایت معتبر نیست."})
    now = timezone.now()
    if consented_at > now or revision.created_at > consented_at:
        raise serializers.ValidationError({"consented_at": "زمان تأیید تماس معتبر نیست."})
    superseded_before_consent = CrmMobileCallPolicyRevision.objects.filter(
        policy=policy, revision__gt=revision_number, created_at__lte=consented_at
    ).exists()
    if superseded_before_consent:
        raise serializers.ValidationError({"policy_revision": "نسخهٔ سیاست هنگام تأیید دیگر فعال نبود."})
    return revision


def _valid_iranian_mobile(value):
    digits = str(value or "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
    normalized = normalize_phone(digits)
    return normalized if re.fullmatch(r"09[0-9]{9}", normalized or "") else ""


def _add_customer_assignment(customer, assignee, actor, reason):
    previous = customer.assigned_to
    if customer.assigned_to_id == (assignee.pk if assignee else None):
        return
    customer.assigned_to = assignee
    customer.save(update_fields=["assigned_to", "updated_at"])
    CustomerAssignmentHistory.objects.create(
        customer=customer,
        previous_assignee=previous,
        assignee=assignee,
        changed_by=actor,
        reason=reason[:255],
    )


def _materialize_capture(capture, customer, task_owner):
    activity = CustomerActivity.objects.create(
        customer=customer,
        kind=CustomerActivity.KIND_CALL,
        channel=CustomerActivity.CHANNEL_PHONE,
        direction=capture.direction,
        result=capture.outcome[:120],
        body=capture.summary,
        occurred_at=capture.call_at,
        created_by=capture.actor,
    )
    task = None
    if capture.next_action.strip():
        task, _created = CrmTask.objects.get_or_create(
            idempotency_key=f"mobile-call:{capture.event_uuid}",
            defaults={
                "customer": customer,
                "owner": task_owner,
                "created_by": capture.actor,
                "title": capture.next_action.strip(),
                "description": capture.summary,
                "due_at": capture.next_due_at,
                "trigger": "mobile.call.capture",
            },
        )
    capture.customer = customer
    capture.activity = activity
    capture.task = task
    capture.status = CrmMobileCallCapture.STATUS_LINKED
    capture.customer_profile = {}
    capture.save(update_fields=["customer", "activity", "task", "status", "customer_profile"])


def _capture_response(capture, replayed=False):
    data = {
        "event_uuid": str(capture.event_uuid),
        "status": capture.status,
        "received_at": capture.received_at,
        "replayed": replayed,
    }
    if capture.status == CrmMobileCallCapture.STATUS_LINKED and capture.customer_id:
        data["customer_id"] = capture.customer_id
        data["activity_id"] = capture.activity_id
        data["task_id"] = capture.task_id
    return data


class MobileCallCaptureView(MobileRoleAPIView):
    def post(self, request):
        serializer = MobileCallCaptureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        event_uuid = data["event_uuid"]
        existing = CrmMobileCallCapture.objects.filter(event_uuid=event_uuid).first()
        if existing:
            if existing.actor_id != request.user.pk:
                raise NotFound()
            return Response(_capture_response(existing, replayed=True), status=status.HTTP_200_OK)
        if data["role_code"] != self.role_code:
            raise PermissionDenied("نقش CRM کاربر تغییر کرده است؛ برنامه را همگام کنید.")
        if data["call_at"] > data["consented_at"]:
            raise serializers.ValidationError({"call_at": "زمان تماس نمی‌تواند پس از زمان تأیید باشد."})
        policy = _ensure_policy(self.role_code)
        if policy.mode == CrmMobileCallPolicy.MODE_OFF:
            # A prior ASK consent may sync after OFF; the immutable revision check below decides.
            pass
        revision = _consent_revision(policy, data["policy_revision"], data["consented_at"])
        phone = _valid_iranian_mobile(data.get("phone", "")) or (data.get("phone", "")[:32])
        profile = data.get("customer_profile", {})
        with transaction.atomic():
            capture, created = CrmMobileCallCapture.objects.get_or_create(
                event_uuid=event_uuid,
                defaults={
                    "actor": request.user,
                    "role_code": self.role_code,
                    "policy_revision": revision,
                    "source": data.get("source", "MANUAL"),
                    "phone": phone,
                    "customer_profile": profile if data.get("customer_id") is None else {},
                    "direction": data["direction"],
                    "outcome": data.get("outcome", "other"),
                    "duration_seconds": data.get("duration_seconds"),
                    "call_at": data["call_at"],
                    "consented_at": data["consented_at"],
                    "summary": data["summary"].strip(),
                    "next_action": data.get("next_action", "").strip(),
                    "next_due_at": data.get("next_due_at"),
                    "status": CrmMobileCallCapture.STATUS_PENDING_REVIEW,
                },
            )
            if not created:
                if capture.actor_id != request.user.pk:
                    raise NotFound()
                return Response(_capture_response(capture, replayed=True), status=status.HTTP_200_OK)

            scoped = _customer_scope(request.user, self.role_code).select_for_update()
            customer = None
            if data.get("customer_id") is not None:
                customer = scoped.filter(pk=data["customer_id"]).first()
            elif _valid_iranian_mobile(data.get("phone", "")):
                normalized = _valid_iranian_mobile(data["phone"])
                existing_customer = Customer.objects.filter(phone=normalized).first()
                if existing_customer:
                    customer = scoped.filter(pk=existing_customer.pk).first()
                else:
                    assignee = request.user if self.role_code == RoleCode.CRM_SALES else None
                    customer, created_customer = Customer.objects.get_or_create(
                        phone=normalized,
                        defaults={
                            "name": normalized,
                            **profile,
                            "source": Customer.SOURCE_INCOMING_CALL,
                            "assigned_to": assignee,
                            "created_by": request.user,
                        },
                    )
                    if created_customer and assignee:
                        CustomerAssignmentHistory.objects.create(
                            customer=customer,
                            assignee=assignee,
                            changed_by=request.user,
                            reason="سرنخ جدید از ثبت تماس موبایل",
                        )
                    if not created_customer:
                        customer = scoped.filter(pk=customer.pk).first()
            if customer:
                placeholder = (
                    re.fullmatch(r"[\d+ ()-]+", customer.name)
                    and _valid_iranian_mobile(customer.name) == customer.phone
                )
                if profile and placeholder:
                    fields_to_fill = {
                        key: value for key, value in profile.items()
                        if key == "name" or not getattr(customer, key)
                        or (key == "decision_role" and customer.decision_role == Customer.DecisionRole.UNKNOWN)
                    }
                    CustomerProfileSerializer().update(customer, fields_to_fill)
                _materialize_capture(capture, customer, request.user)
        return Response(_capture_response(capture), status=status.HTTP_201_CREATED)


class MobileCallCaptureStatusView(MobileRoleAPIView):
    def get(self, request, event_uuid):
        capture = get_object_or_404(
            CrmMobileCallCapture.objects.filter(actor=request.user), event_uuid=event_uuid
        )
        return Response(_capture_response(capture))


class MobileAdminPolicyListView(APIView):
    permission_classes = [IsAuthenticated, IsFullAdminUser]

    def get(self, request):
        roles = (RoleCode.ADMIN, RoleCode.MARKETER, RoleCode.CRM_SALES, *POLICY_LOCKED_ROLES)
        payload = []
        for role in roles:
            policy = _ensure_policy(role)
            payload.append({**_policy_data(policy), "can_edit": role not in POLICY_LOCKED_ROLES})
        return Response(payload)


class MobileAdminPolicyUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsFullAdminUser]

    def put(self, request, role_code):
        if role_code not in MOBILE_CRM_ROLES:
            raise PermissionDenied("سیاست این نقش قفل است.")
        mode = request.data.get("mode")
        default_action = request.data.get("default_action")
        if mode not in {CrmMobileCallPolicy.MODE_ASK, CrmMobileCallPolicy.MODE_OFF}:
            raise serializers.ValidationError({"mode": "مقدار باید ASK یا OFF باشد."})
        if default_action not in {CrmMobileCallPolicy.ACTION_REGISTER, CrmMobileCallPolicy.ACTION_DISCARD}:
            raise serializers.ValidationError({"default_action": "مقدار باید REGISTER یا DISCARD باشد."})
        with transaction.atomic():
            policy = _ensure_policy(role_code)
            policy = CrmMobileCallPolicy.objects.select_for_update().get(pk=policy.pk)
            if policy.mode != mode or policy.default_action != default_action:
                policy.revision += 1
                policy.mode = mode
                policy.default_action = default_action
                policy.updated_by = request.user
                policy.save(update_fields=["revision", "mode", "default_action", "updated_by", "updated_at"])
                CrmMobileCallPolicyRevision.objects.create(
                    policy=policy,
                    revision=policy.revision,
                    mode=mode,
                    default_action=default_action,
                    changed_by=request.user,
                )
        return Response(_policy_data(policy))


class MobileReviewQueueView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrActiveAdminRole]
    admin_sections = ("crm",)

    def get(self, request):
        rows = CrmMobileCallCapture.objects.filter(
            status=CrmMobileCallCapture.STATUS_PENDING_REVIEW
        ).select_related("actor", "policy_revision").order_by("created_at", "id")[:200]
        return Response([
            {
                "event_uuid": str(row.event_uuid),
                "phone": row.phone,
                "customer_profile": row.customer_profile,
                "direction": row.direction,
                "outcome": row.outcome,
                "duration_seconds": row.duration_seconds,
                "call_at": row.call_at,
                "summary": row.summary,
                "next_action": row.next_action,
                "next_due_at": row.next_due_at,
                "actor_id": row.actor_id,
                "actor_name": (row.actor.get_full_name() or "").strip() or row.actor.get_username(),
                "received_at": row.received_at,
            }
            for row in rows
        ])


class MobileReviewResolveSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(required=False, allow_null=True)
    assignee_id = serializers.IntegerField()
    create_customer = serializers.BooleanField(required=False, default=False)


class MobileReviewResolveView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrActiveAdminRole]
    admin_sections = ("crm",)

    def post(self, request, event_uuid):
        payload = MobileReviewResolveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        from django.contrib.auth import get_user_model

        User = get_user_model()
        assignee = User.objects.filter(
            pk=data["assignee_id"], is_active=True,
            roles__role=RoleCode.CRM_SALES, roles__is_active=True,
        ).distinct().first()
        if not assignee:
            raise serializers.ValidationError({"assignee_id": "کارشناس CRM فعال پیدا نشد."})
        with transaction.atomic():
            capture = get_object_or_404(
                CrmMobileCallCapture.objects.select_for_update(),
                event_uuid=event_uuid,
                status=CrmMobileCallCapture.STATUS_PENDING_REVIEW,
            )
            if data.get("create_customer"):
                phone = _valid_iranian_mobile(capture.phone)
                if not phone:
                    raise serializers.ValidationError({"create_customer": "شمارهٔ معتبر برای ساخت سرنخ لازم است."})
                customer = Customer.objects.filter(phone=phone).first()
                if customer:
                    raise serializers.ValidationError({"create_customer": "این شماره به مشتری موجود تعلق دارد؛ همان مشتری را انتخاب کنید."})
                customer, created_customer = Customer.objects.get_or_create(
                    phone=phone,
                    defaults={
                        "name": phone,
                        **capture.customer_profile,
                        "source": Customer.SOURCE_INCOMING_CALL,
                        "created_by": capture.actor,
                        "assigned_to": assignee,
                    },
                )
                if not created_customer:
                    raise serializers.ValidationError({"create_customer": "این شماره به مشتری موجود تعلق دارد؛ همان مشتری را انتخاب کنید."})
                CustomerAssignmentHistory.objects.create(
                    customer=customer, assignee=assignee, changed_by=request.user,
                    reason="اتصال تماس موبایل بررسی‌شده",
                )
            else:
                customer_id = data.get("customer_id")
                if not customer_id:
                    raise serializers.ValidationError({"customer_id": "مشتری یا ساخت سرنخ را انتخاب کنید."})
                customer = get_object_or_404(Customer.objects.select_for_update(), pk=customer_id)
                _add_customer_assignment(customer, assignee, request.user, "اتصال تماس موبایل بررسی‌شده")
            _materialize_capture(capture, customer, assignee)
            capture.resolved_by = request.user
            capture.resolved_at = timezone.now()
            capture.save(update_fields=["resolved_by", "resolved_at"])
        return Response({"event_uuid": str(capture.event_uuid), "status": capture.status, "customer_id": customer.pk})


class MobileReviewRejectView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrActiveAdminRole]
    admin_sections = ("crm",)

    def post(self, request, event_uuid):
        with transaction.atomic():
            capture = get_object_or_404(
                CrmMobileCallCapture.objects.select_for_update(),
                event_uuid=event_uuid,
                status=CrmMobileCallCapture.STATUS_PENDING_REVIEW,
            )
            capture.phone = ""
            capture.customer_profile = {}
            capture.direction = ""
            capture.outcome = ""
            capture.duration_seconds = None
            capture.call_at = capture.received_at
            capture.summary = ""
            capture.next_action = ""
            capture.next_due_at = None
            capture.status = CrmMobileCallCapture.STATUS_REJECTED
            capture.resolved_by = request.user
            capture.resolved_at = timezone.now()
            capture.save(update_fields=[
                "phone", "customer_profile", "direction", "outcome", "duration_seconds", "call_at", "summary",
                "next_action", "next_due_at", "status", "resolved_by", "resolved_at",
            ])
        return Response({"event_uuid": str(capture.event_uuid), "status": capture.status})
