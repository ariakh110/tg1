from rest_framework import serializers
from products.models import ProductCategory

from .models import (
    CrmOpportunity,
    CrmOpportunityStageHistory,
    CrmSyncEvent,
    Customer,
    CustomerActivity,
    CustomerTransaction,
)


class CustomerActivitySerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_phone = serializers.CharField(source="customer.phone", read_only=True)

    class Meta:
        model = CustomerActivity
        fields = [
            "id",
            "customer",
            "customer_name",
            "customer_phone",
            "kind",
            "kind_display",
            "body",
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
            "kind_display",
            "follow_up_done_at",
            "stage_from",
            "stage_to",
            "created_at",
            "updated_at",
        ]


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

    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields + ["transactions", "activities", "opportunities"]
