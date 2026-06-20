from rest_framework import serializers

from .models import Customer, CustomerTransaction


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
            "balance",
            "transaction_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "balance", "transaction_count", "created_at", "updated_at"]


class CustomerDetailSerializer(CustomerSerializer):
    transactions = CustomerTransactionSerializer(many=True, read_only=True)

    class Meta(CustomerSerializer.Meta):
        fields = CustomerSerializer.Meta.fields + ["transactions"]
