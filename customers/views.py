from rest_framework import filters, viewsets

from accounts.permissions import IsAdminOrActiveAdminRole

from .models import Customer, CustomerTransaction
from .serializers import (
    CustomerDetailSerializer,
    CustomerSerializer,
    CustomerTransactionSerializer,
)


class CustomerViewSet(viewsets.ModelViewSet):
    """مدیریتِ مشتریانِ CRM (فقط ادمین)."""

    queryset = Customer.objects.all()
    permission_classes = [IsAdminOrActiveAdminRole]
    pagination_class = None
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "phone", "company", "city"]
    ordering_fields = ["updated_at", "created_at", "name"]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CustomerDetailSerializer
        return CustomerSerializer


class CustomerTransactionViewSet(viewsets.ModelViewSet):
    """تراکنش‌های دفترِ مشتری (خرید/پرداخت/تعدیل) — فقط ادمین."""

    queryset = CustomerTransaction.objects.select_related("customer").all()
    serializer_class = CustomerTransactionSerializer
    permission_classes = [IsAdminOrActiveAdminRole]
    pagination_class = None
    filterset_fields = ["customer", "kind"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user if self.request.user.is_authenticated else None)
