from rest_framework import serializers
from products.models import ProductCategory

from .models import (
    CrmAutomationRun,
    CrmContactChannel,
    CrmFollowUp,
    CrmOpportunity,
    CrmOpportunityStageHistory,
    CrmSyncEvent,
    CrmTask,
    Customer,
    CustomerActivity,
    CustomerTransaction,
)
from .services import normalize_phone


class CustomerActivitySerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    opportunity_title = serializers.CharField(source="opportunity.title", read_only=True, default="")

    class Meta:
        model = CustomerActivity
        fields = [
            "id",
            "customer",
            "customer_name",
            "customer_phone",
            "opportunity",
            "opportunity_title",
            "kind",
            "kind_display",
            "body",
            "direction",
            "result",
            "external_message_key",
            "occurred_at",
            "follow_up_at",
            "follow_up_note",
            "follow_up_done",
            "follow_up_done_at",
            "stage_from",
            "stage_to",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "customer_name",
            "customer_phone",
            "opportunity_title",
            "kind_display",
            "follow_up_done_at",
            "stage_from",
            "stage_to",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        opportunity = attrs.get("opportunity", getattr(self.instance, "opportunity", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if opportunity and customer and opportunity.customer_id not in (None, customer.pk):
            raise serializers.ValidationError({"opportunity": "این فرصت به مشتری دیگری متصل است."})
        return attrs


class CustomerTransactionSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = CustomerTransaction
        fields = [
            "id",
            "customer",
            "customer_name",
            "kind",
            "kind_display",
            "amount",
            "description",
            "occurred_at",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "customer_name", "kind_display"]

    def validate(self, attrs):
        kind = attrs.get("kind", getattr(self.instance, "kind", CustomerTransaction.KIND_PURCHASE))
        amount = attrs.get("amount", getattr(self.instance, "amount", None))
        if amount is None:
            raise serializers.ValidationError({"amount": "مبلغ لازم است."})
        if kind in (CustomerTransaction.KIND_PURCHASE, CustomerTransaction.KIND_PAYMENT) and amount <= 0:
            raise serializers.ValidationError({"amount": "مبلغِ خرید/پرداخت باید مثبت باشد."})
        return attrs


class CustomerSerializer(serializers.ModelSerializer):
    balance = serializers.IntegerField(read_only=True)
    transaction_count = serializers.IntegerField(source="transactions.count", read_only=True)
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    # از annotate شدنِ کوئری در ویوست می‌آیند؛ روی نمونهٔ تکی ممکن است نباشند.
    next_follow_up_at = serializers.DateTimeField(read_only=True, required=False, allow_null=True)
    open_follow_up_count = serializers.IntegerField(read_only=True, required=False)
    product_interests = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=ProductCategory.objects.all(),
        required=False,
    )
    product_interest_details = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "phone",
            "company",
            "city",
            "province",
            "note",
            "extra_phones",
            "product_interests",
            "product_interest_details",
            "user",
            "is_active",
            "stage",
            "stage_display",
            "source",
            "source_display",
            "balance",
            "transaction_count",
            "next_follow_up_at",
            "open_follow_up_count",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "balance",
            "transaction_count",
            "stage_display",
            "source_display",
            "next_follow_up_at",
            "open_follow_up_count",
            "created_by_name",
            "created_at",
            "updated_at",
        ]

    def validate_phone(self, value):
        normalized = normalize_phone(value)
        if len(normalized) != 11 or not normalized.startswith("09") or not normalized.isascii() or not normalized.isdigit():
            raise serializers.ValidationError("شماره موبایل معتبر وارد کنید.")
        return normalized

    def get_created_by_name(self, obj):
        user = obj.created_by
        if not user:
            return ""
        full = (user.get_full_name() or "").strip()
        return full or user.get_username()

    def get_product_interest_details(self, obj):
        return [
            {
                "id": category.id,
                "name": category.name,
                "code": category.code or "",
                "full_path": " / ".join(item.name for item in category.get_ancestors(include_self=True)),
            }
            for category in obj.product_interests.all()
        ]


class CrmOpportunityStageHistorySerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    from_stage_display = serializers.SerializerMethodField()
    to_stage_display = serializers.SerializerMethodField()

    class Meta:
        model = CrmOpportunityStageHistory
        fields = [
            "id",
            "from_stage",
            "from_stage_display",
            "to_stage",
            "to_stage_display",
            "event",
            "event_key",
            "reason",
            "actor_name",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        user = obj.actor_user
        if not user:
            return "سیستم"
        return (user.get_full_name() or "").strip() or user.get_username()

    def get_from_stage_display(self, obj):
        return dict(CrmOpportunity.STAGE_CHOICES).get(obj.from_stage, obj.from_stage)

    def get_to_stage_display(self, obj):
        return dict(CrmOpportunity.STAGE_CHOICES).get(obj.to_stage, obj.to_stage)


class CrmOpportunitySerializer(serializers.ModelSerializer):
    stage_display = serializers.CharField(source="get_stage_display", read_only=True)
    source_type_display = serializers.CharField(source="get_source_type_display", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="")
    customer_phone = serializers.CharField(source="customer.phone", read_only=True, default="")
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = CrmOpportunity
        fields = [
            "id",
            "customer",
            "customer_name",
            "customer_phone",
            "title",
            "stage",
            "stage_display",
            "source_type",
            "source_type_display",
            "source_id",
            "source_status",
            "owner",
            "owner_name",
            "expected_value_irr",
            "probability",
            "need_details",
            "next_action",
            "next_follow_up_at",
            "lost_reason",
            "metadata",
            "is_active",
            "closed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "stage",
            "stage_display",
            "source_type",
            "source_type_display",
            "source_id",
            "source_status",
            "owner_name",
            "customer_name",
            "customer_phone",
            "lost_reason",
            "metadata",
            "closed_at",
            "created_at",
            "updated_at",
        ]

    def get_owner_name(self, obj):
        user = obj.owner
        if not user:
            return ""
        return (user.get_full_name() or "").strip() or user.get_username()

    def validate_expected_value_irr(self, value):
        if value < 0:
            raise serializers.ValidationError("ارزش فرصت نمی‌تواند منفی باشد.")
        return value

    def validate_probability(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("احتمال موفقیت باید بین صفر تا صد باشد.")
        return value

    def validate(self, attrs):
        instance = self.instance
        if instance and instance.source_type in {
            CrmOpportunity.SOURCE_STORE_ORDER,
            CrmOpportunity.SOURCE_ASSISTANT_INQUIRY,
        }:
            protected = {"customer", "title", "expected_value_irr", "need_details"}
            attempted = sorted(protected & set(attrs))
            if attempted:
                raise serializers.ValidationError(
                    {field: "این فیلد از رکورد منبع سایت همگام می‌شود." for field in attempted}
                )
        return attrs


class CrmOpportunityDetailSerializer(CrmOpportunitySerializer):
    stage_history = CrmOpportunityStageHistorySerializer(many=True, read_only=True)

    class Meta(CrmOpportunitySerializer.Meta):
        fields = CrmOpportunitySerializer.Meta.fields + ["stage_history"]


class CrmContactChannelSerializer(serializers.ModelSerializer):
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    consent_display = serializers.CharField(source="get_consent_display", read_only=True)
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CrmContactChannel
        fields = [
            "id", "channel", "channel_display", "consent", "consent_display", "source",
            "consented_at", "updated_by_name", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_updated_by_name(self, obj):
        user = obj.updated_by
        if not user:
            return ""
        return (user.get_full_name() or "").strip() or user.get_username()


class CrmFollowUpSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)
    opportunity_title = serializers.CharField(source="opportunity.title", read_only=True, default="")
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = CrmFollowUp
        fields = [
            "id", "customer", "customer_name", "customer_phone", "opportunity", "opportunity_title",
            "owner", "owner_name", "source_activity", "title", "channel", "due_at", "status", "result",
            "reminder_metadata", "idempotency_key", "completed_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "customer_name", "customer_phone", "opportunity_title", "owner", "owner_name",
            "source_activity", "status", "result", "reminder_metadata", "idempotency_key",
            "completed_at", "created_at", "updated_at",
        ]

    def get_owner_name(self, obj):
        user = obj.owner
        if not user:
            return ""
        return (user.get_full_name() or "").strip() or user.get_username()

    def validate(self, attrs):
        opportunity = attrs.get("opportunity", getattr(self.instance, "opportunity", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if opportunity and customer and opportunity.customer_id not in (None, customer.pk):
            raise serializers.ValidationError({"opportunity": "این فرصت به مشتری دیگری متصل است."})
        if self.instance and self.instance.source_activity_id:
            if customer and customer.pk != self.instance.customer_id:
                raise serializers.ValidationError({"customer": "مشتری پیگیریِ متصل به فعالیت را نمی‌توان عوض کرد."})
            if "opportunity" in attrs and getattr(opportunity, "pk", None) != self.instance.opportunity_id:
                raise serializers.ValidationError({"opportunity": "فرصت پیگیریِ متصل به فعالیت را نمی‌توان عوض کرد."})
        return attrs


class CrmTaskSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="")
    customer_phone = serializers.CharField(source="customer.phone", read_only=True, default="")
    opportunity_title = serializers.CharField(source="opportunity.title", read_only=True, default="")
    opportunity_source_type = serializers.CharField(source="opportunity.source_type", read_only=True, default="")
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = CrmTask
        fields = [
            "id", "customer", "customer_name", "customer_phone", "opportunity", "opportunity_title",
            "opportunity_source_type", "source_order_id", "owner", "owner_name", "title", "description",
            "trigger", "due_at", "status", "result", "idempotency_key", "completed_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "customer_name", "customer_phone", "opportunity_title", "opportunity_source_type",
            "source_order_id", "owner", "owner_name", "trigger", "status", "result", "idempotency_key",
            "completed_at", "created_at", "updated_at",
        ]

    def get_owner_name(self, obj):
        user = obj.owner
        if not user:
            return ""
        return (user.get_full_name() or "").strip() or user.get_username()

    def validate(self, attrs):
        opportunity = attrs.get("opportunity", getattr(self.instance, "opportunity", None))
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        if opportunity and customer and opportunity.customer_id not in (None, customer.pk):
            raise serializers.ValidationError({"opportunity": "این فرصت به مشتری دیگری متصل است."})
        return attrs


class CrmAutomationRunSerializer(serializers.ModelSerializer):
    trigger_display = serializers.CharField(source="get_trigger_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True, default="")
    opportunity_title = serializers.CharField(source="opportunity.title", read_only=True, default="")

    class Meta:
        model = CrmAutomationRun
        fields = [
            "id", "event_key", "trigger", "trigger_display", "customer", "customer_name", "opportunity",
            "opportunity_title", "status", "status_display", "attempts", "last_error", "payload",
            "processed_at", "created_at", "updated_at",
        ]
        read_only_fields = fields


class CrmOpportunityTransitionSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=CrmOpportunity.STAGE_CHOICES)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["stage"] == CrmOpportunity.STAGE_LOST and not attrs.get("reason", "").strip():
            raise serializers.ValidationError({"reason": "برای فرصت ازدست‌رفته دلیل را وارد کنید."})
        return attrs


class CrmSyncEventSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source="get_source_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = CrmSyncEvent
        fields = [
            "id",
            "source_type",
            "source_type_display",
            "source_id",
            "event_key",
            "status",
            "status_display",
            "attempts",
            "last_error",
            "payload",
            "processed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CustomerDetailSerializer(CustomerSerializer):
    transactions = CustomerTransactionSerializer(many=True, read_only=True)
    activities = CustomerActivitySerializer(many=True, read_only=True)
    opportunities = CrmOpportunitySerializer(many=True, read_only=True)
    contact_channels = CrmContactChannelSerializer(many=True, read_only=True)
    crm_follow_ups = CrmFollowUpSerializer(many=True, read_only=True)
    crm_tasks = CrmTaskSerializer(many=True, read_only=True)

    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields + [
            "transactions", "activities", "opportunities", "contact_channels", "crm_follow_ups", "crm_tasks",
        ]
