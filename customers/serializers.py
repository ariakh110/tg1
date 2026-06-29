from rest_framework import serializers

from .models import Customer, CustomerActivity, CustomerTransaction


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


class CustomerDetailSerializer(CustomerSerializer):
    transactions = CustomerTransactionSerializer(many=True, read_only=True)
    activities = CustomerActivitySerializer(many=True, read_only=True)

    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields + ["transactions", "activities"]
