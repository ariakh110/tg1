import csv

from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminOrActiveAdminRole

from .models import OfflinePayment, SatnaBankAccount
from .serializers import (
    AdminSatnaBankAccountSerializer,
    BankAccountSerializer,
    OfflinePaymentInitiateSerializer,
    OfflinePaymentSerializer,
    ReceiptApprovalReversalSerializer,
    ReceiptUploadSerializer,
    ReviewSerializer,
    UnlockSerializer,
)
from .services import bank_accounts, expire_if_due, primary_bank_account, satna_financial_report


REPORT_CSV_COLUMNS = (
    "receipt_id",
    "payment_id",
    "source_type",
    "source_id",
    "source_title",
    "buyer_username",
    "buyer_email",
    "receipt_amount",
    "currency",
    "reference_number",
    "approved_at",
    "payment_created_at",
    "payment_status",
    "payment_amount",
    "bank_account_id",
    "bank_name",
    "iban",
    "account_holder",
)


def serialize_payment(payment, request):
    return OfflinePaymentSerializer(payment, context={"request": request}).data


class BankAccountListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        primary = primary_bank_account()
        rows = [{**row, "is_primary": row["id"] == primary["id"]} for row in bank_accounts()]
        return Response(BankAccountSerializer(rows, many=True).data)


class OfflinePaymentListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        payments = (
            OfflinePayment.objects.filter(user=request.user)
            .select_related("store_order", "marketplace_order")
            .prefetch_related("store_order__items", "receipts", "audit_logs__actor_user")
        )
        for payment in payments:
            expire_if_due(payment)
        return Response(OfflinePaymentSerializer(payments, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = OfflinePaymentInitiateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        return Response(serialize_payment(payment, request), status=status.HTTP_201_CREATED)


class OfflinePaymentStatusAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        payment = get_object_or_404(
            OfflinePayment.objects.select_related("store_order", "marketplace_order").prefetch_related(
                "store_order__items", "receipts", "audit_logs__actor_user"
            ),
            pk=pk,
            user=request.user,
        )
        expire_if_due(payment)
        return Response(serialize_payment(payment, request))


class ReceiptUploadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        payment = get_object_or_404(OfflinePayment, pk=pk, user=request.user)
        serializer = ReceiptUploadSerializer(data=request.data, context={"request": request, "payment": payment})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        return Response(serialize_payment(payment, request), status=status.HTTP_201_CREATED)


class ReceiptFileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, receipt_id=None):
        payment = get_object_or_404(OfflinePayment.objects.prefetch_related("receipts"), pk=pk)
        is_admin = IsAdminOrActiveAdminRole().has_permission(request, self)
        if payment.user_id != request.user.id and not is_admin:
            return Response({"detail": "دسترسی به این فیش مجاز نیست."}, status=status.HTTP_403_FORBIDDEN)
        receipt = payment.receipts.filter(pk=receipt_id).first() if receipt_id else payment.receipts.first()
        if not receipt:
            return Response({"detail": "فیشی بارگذاری نشده است."}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(receipt.file.open("rb"), as_attachment=False, filename=receipt.file.name.rsplit("/", 1)[-1])


class AdminOfflinePaymentListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def get(self, request):
        payments = (
            OfflinePayment.objects.select_related("user", "store_order", "marketplace_order")
            .prefetch_related("store_order__items", "receipts", "audit_logs__actor_user")
            .order_by("-created_at")
        )
        payment_status = (request.query_params.get("status") or "").strip()
        if payment_status:
            payments = payments.filter(status=payment_status)
        for payment in payments:
            expire_if_due(payment)
        return Response(OfflinePaymentSerializer(payments, many=True, context={"request": request}).data)


class AdminOfflinePaymentFinancialReportAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def get(self, request):
        report = satna_financial_report(request.query_params)
        export = (request.query_params.get("export") or request.query_params.get("format") or "").strip().lower()
        if export == "csv":
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="satna-financial-report.csv"'
            response.write("\ufeff")
            writer = csv.writer(response)
            writer.writerow(REPORT_CSV_COLUMNS)
            for row in report["rows"]:
                writer.writerow([row.get(column, "") for column in REPORT_CSV_COLUMNS])
            return response
        return Response(report)


class AdminSatnaBankAccountListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def get(self, request):
        accounts = SatnaBankAccount.objects.all()
        return Response(AdminSatnaBankAccountSerializer(accounts, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = AdminSatnaBankAccountSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminSatnaBankAccountDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def patch(self, request, code):
        account = get_object_or_404(SatnaBankAccount, code=code)
        serializer = AdminSatnaBankAccountSerializer(
            account,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdminOfflinePaymentReviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def patch(self, request, pk):
        payment = get_object_or_404(OfflinePayment, pk=pk)
        serializer = ReviewSerializer(data=request.data, context={"request": request, "payment": payment})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        return Response(serialize_payment(payment, request))


class AdminOfflinePaymentReceiptReversalAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def patch(self, request, pk, receipt_id):
        payment = get_object_or_404(OfflinePayment, pk=pk)
        serializer = ReceiptApprovalReversalSerializer(
            data=request.data,
            context={"request": request, "payment": payment, "receipt_id": receipt_id},
        )
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        return Response(serialize_payment(payment, request))


class AdminOfflinePaymentUnlockAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActiveAdminRole]

    def patch(self, request, pk):
        payment = get_object_or_404(OfflinePayment, pk=pk)
        serializer = UnlockSerializer(data=request.data, context={"request": request, "payment": payment})
        serializer.is_valid(raise_exception=True)
        payment = serializer.save()
        return Response(serialize_payment(payment, request))
