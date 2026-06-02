import json
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import Order, OrderOffer, OrderStatus, OrderType, OfferStatus
from sales.models import StoreOrder, StoreOrderStatus, StorePayment, StorePaymentStatus

from .models import (
    NotificationStatus,
    OfflinePayment,
    OfflinePaymentNotification,
    OfflinePaymentStatus,
    SatnaBankAccount,
    SatnaBankAccountAuditLog,
)
from .tasks import check_payment_deadlines, send_payment_deadline_reminders


User = get_user_model()
TEST_MEDIA_ROOT = tempfile.mkdtemp()
TEST_ACCOUNTS = json.dumps(
    [
        {
            "id": "IBAN_01",
            "bank_name": "بانک ملت",
            "iban": "IR000000000000000000000000",
            "account_holder": "شرکت تست",
        }
    ]
)


@override_settings(
    MEDIA_ROOT=TEST_MEDIA_ROOT,
    OFFLINE_PAYMENT_BANK_ACCOUNTS_JSON=TEST_ACCOUNTS,
    OFFLINE_PAYMENT_PRIMARY_IBAN_ID="IBAN_01",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class OfflinePaymentAPITests(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.buyer = User.objects.create_user(username="satna-buyer", email="buyer@example.com", password="pass")
        self.other = User.objects.create_user(username="satna-other", password="pass")
        self.admin = User.objects.create_user(username="satna-admin", password="pass", is_staff=True)
        self.order = StoreOrder.objects.create(
            buyer=self.buyer,
            status=StoreOrderStatus.PAYMENT_PENDING,
            payment_status=StorePaymentStatus.PENDING,
            total_amount=1_500_000_000,
            settlement_term_days=1,
            price_valid_until=timezone.now() + timezone.timedelta(hours=1),
        )

    def initiate(self):
        self.client.force_authenticate(self.buyer)
        response = self.client.post(
            "/api/v1/offline-payments/",
            {"source_type": "store_order", "source_id": str(self.order.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return response

    def upload(self, payment_id, reference="123456", filename="receipt.png", content_type="image/png"):
        self.client.force_authenticate(self.buyer)
        return self.client.post(
            f"/api/v1/offline-payments/{payment_id}/upload-receipt/",
            {
                "reference_number": reference,
                "receipt_file": SimpleUploadedFile(filename, b"receipt-content", content_type=content_type),
            },
            format="multipart",
        )

    def review(self, payment_id, decision, note=""):
        self.client.force_authenticate(self.admin)
        return self.client.patch(
            f"/api/v1/admin/offline-payments/{payment_id}/review/",
            {"decision": decision, "admin_note": note},
            format="json",
        )

    def create_bank_account(self, iban="IR111111111111111111111111", **overrides):
        self.client.force_authenticate(self.admin)
        payload = {
            "bank_name": "بانک ملت",
            "account_holder": "شرکت تست",
            "account_number": "123456789",
            "iban": iban,
            **overrides,
        }
        return self.client.post("/api/v1/admin/offline-payments/bank-accounts/", payload, format="json")

    def test_buyer_can_initiate_upload_and_read_protected_receipt(self):
        response = self.initiate()
        payment_id = response.data["id"]
        self.assertEqual(response.data["status"], OfflinePaymentStatus.PENDING_RECEIPT)
        self.assertEqual(response.data["bank_account"]["id"], "IBAN_01")

        upload = self.upload(payment_id)
        self.assertEqual(upload.status_code, status.HTTP_201_CREATED, upload.data)
        self.assertEqual(upload.data["status"], OfflinePaymentStatus.PENDING_REVIEW)

        receipt = self.client.get(f"/api/v1/offline-payments/{payment_id}/receipt/")
        self.assertEqual(receipt.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.other)
        forbidden = self.client.get(f"/api/v1/offline-payments/{payment_id}/receipt/")
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(OFFLINE_PAYMENT_BANK_ACCOUNTS_JSON="[]")
    def test_bank_accounts_endpoint_reports_missing_configuration_in_persian(self):
        self.client.force_authenticate(self.buyer)

        response = self.client.get("/api/v1/offline-payments/bank-accounts/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "اطلاعات حساب مقصد ساتنا تنظیم نشده است. با پشتیبانی تماس بگیرید.")

    @override_settings(OFFLINE_PAYMENT_BANK_ACCOUNTS_JSON="[]")
    def test_admin_can_create_multiple_accounts_and_change_primary_account(self):
        first = self.create_bank_account()
        second = self.create_bank_account(
            iban="IR222222222222222222222222",
            bank_name="بانک تجارت",
            account_number="987654321",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        self.assertTrue(first.data["is_primary"])
        self.assertEqual(second.status_code, status.HTTP_201_CREATED, second.data)
        self.assertFalse(second.data["is_primary"])

        promoted = self.client.patch(
            f"/api/v1/admin/offline-payments/bank-accounts/{second.data['id']}/",
            {"is_primary": True},
            format="json",
        )

        self.assertEqual(promoted.status_code, status.HTTP_200_OK, promoted.data)
        self.assertTrue(promoted.data["is_primary"])
        self.assertFalse(SatnaBankAccount.objects.get(code=first.data["id"]).is_primary)
        self.assertEqual(SatnaBankAccountAuditLog.objects.count(), 3)

        self.client.force_authenticate(self.buyer)
        public_accounts = self.client.get("/api/v1/offline-payments/bank-accounts/")
        self.assertEqual(public_accounts.status_code, status.HTTP_200_OK, public_accounts.data)
        self.assertEqual(len(public_accounts.data), 2)
        self.assertEqual(next(row for row in public_accounts.data if row["is_primary"])["id"], second.data["id"])

    def test_regular_user_cannot_manage_bank_accounts(self):
        self.client.force_authenticate(self.buyer)

        response = self.client.post(
            "/api/v1/admin/offline-payments/bank-accounts/",
            {
                "bank_name": "بانک ملت",
                "account_holder": "شرکت تست",
                "account_number": "123456789",
                "iban": "IR111111111111111111111111",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(OFFLINE_PAYMENT_BANK_ACCOUNTS_JSON="[]")
    def test_payment_keeps_bank_account_snapshot_after_admin_edit(self):
        account = self.create_bank_account()
        payment_id = self.initiate().data["id"]

        self.client.force_authenticate(self.admin)
        updated = self.client.patch(
            f"/api/v1/admin/offline-payments/bank-accounts/{account.data['id']}/",
            {"bank_name": "بانک ویرایش شده", "iban": "IR333333333333333333333333"},
            format="json",
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.data)

        self.client.force_authenticate(self.buyer)
        payment = self.client.get(f"/api/v1/offline-payments/{payment_id}/status/")

        self.assertEqual(payment.status_code, status.HTTP_200_OK, payment.data)
        self.assertEqual(payment.data["bank_account"]["bank_name"], "بانک ملت")
        self.assertEqual(payment.data["bank_account"]["iban"], "IR111111111111111111111111")

    def test_upload_rejects_invalid_reference_and_extension(self):
        payment_id = self.initiate().data["id"]

        bad_reference = self.upload(payment_id, reference="SATNA-123")
        self.assertEqual(bad_reference.status_code, status.HTTP_400_BAD_REQUEST)
        bad_extension = self.upload(payment_id, filename="receipt.txt", content_type="text/plain")
        self.assertEqual(bad_extension.status_code, status.HTTP_400_BAD_REQUEST)

    def test_third_rejection_locks_upload_and_admin_can_unlock(self):
        payment_id = self.initiate().data["id"]
        for attempt in range(3):
            upload = self.upload(payment_id, reference=f"12345{attempt}")
            self.assertEqual(upload.status_code, status.HTTP_201_CREATED, upload.data)
            review = self.review(payment_id, "reject", f"رد شماره {attempt + 1}")
            self.assertEqual(review.status_code, status.HTTP_200_OK, review.data)

        payment = OfflinePayment.objects.get(pk=payment_id)
        self.assertEqual(payment.status, OfflinePaymentStatus.LOCKED)
        self.assertEqual(payment.rejection_count, 3)
        blocked = self.upload(payment_id, reference="999999")
        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.force_authenticate(self.admin)
        unlocked = self.client.patch(
            f"/api/v1/admin/offline-payments/{payment_id}/unlock/",
            {"admin_note": "بررسی تلفنی انجام شد"},
            format="json",
        )
        self.assertEqual(unlocked.status_code, status.HTTP_200_OK, unlocked.data)
        self.assertEqual(unlocked.data["status"], OfflinePaymentStatus.REJECTED)
        self.assertEqual(unlocked.data["rejection_count"], 0)

    def test_admin_approval_creates_store_payment_and_marks_order_paid(self):
        payment_id = self.initiate().data["id"]
        self.assertEqual(self.upload(payment_id).status_code, status.HTTP_201_CREATED)

        approved = self.review(payment_id, "approve")

        self.assertEqual(approved.status_code, status.HTTP_200_OK, approved.data)
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, StorePaymentStatus.PAID)
        self.assertEqual(self.order.status, StoreOrderStatus.PAID)
        self.assertEqual(StorePayment.objects.filter(provider_reference=f"satna:{payment_id}").count(), 1)

    def test_satna_rejects_amount_below_one_billion_toman(self):
        self.order.total_amount = 999_999_999
        self.order.save(update_fields=["total_amount"])
        self.client.force_authenticate(self.buyer)

        response = self.client.post(
            "/api/v1/offline-payments/",
            {"source_type": "store_order", "source_id": str(self.order.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "مبلغ پرداخت ساتنا باید حداقل 1,000,000,000 تومان باشد.")

    def test_satna_allows_amount_above_previous_upper_limit(self):
        self.order.total_amount = 3_333_505_000
        self.order.save(update_fields=["total_amount"])

        response = self.initiate()

        self.assertEqual(response.data["amount"], 3_333_505_000)

    def test_deadline_task_expires_payment_and_notifies_only_once(self):
        payment_id = self.initiate().data["id"]
        payment = OfflinePayment.objects.get(pk=payment_id)
        payment.payment_deadline = timezone.now() - timezone.timedelta(minutes=1)
        payment.save(update_fields=["payment_deadline"])

        first = check_payment_deadlines()
        second = check_payment_deadlines()

        payment.refresh_from_db()
        self.assertEqual(payment.status, OfflinePaymentStatus.EXPIRED)
        self.assertEqual(first, {"expired": 1})
        self.assertEqual(second, {"expired": 0})
        self.assertEqual(
            OfflinePaymentNotification.objects.filter(
                payment=payment,
                event="payment_expired",
                status=NotificationStatus.SENT,
            ).count(),
            1,
        )

    def test_reminder_task_notifies_only_once_within_two_hour_window(self):
        payment_id = self.initiate().data["id"]
        payment = OfflinePayment.objects.get(pk=payment_id)
        payment.payment_deadline = timezone.now() + timezone.timedelta(minutes=90)
        payment.save(update_fields=["payment_deadline"])

        first = send_payment_deadline_reminders()
        second = send_payment_deadline_reminders()

        self.assertEqual(first, {"reminded": 1})
        self.assertEqual(second, {"reminded": 0})
        self.assertEqual(
            OfflinePaymentNotification.objects.filter(
                payment=payment,
                event="payment_reminder",
                status=NotificationStatus.SENT,
            ).count(),
            1,
        )
        self.assertTrue(payment.audit_logs.filter(action="PAYMENT_REMINDER_SENT").exists())

    def test_celery_beat_schedule_registers_satna_periodic_tasks(self):
        from django.conf import settings

        tasks = {row["task"] for row in settings.CELERY_BEAT_SCHEDULE.values()}

        self.assertIn("offline_payments.tasks.check_payment_deadlines", tasks)
        self.assertIn("offline_payments.tasks.send_payment_deadline_reminders", tasks)

    def test_marketplace_buyer_can_initiate_after_offer_selection(self):
        seller = User.objects.create_user(username="satna-seller", password="pass")
        market_order = Order.objects.create(
            type=OrderType.BUY,
            status=OrderStatus.OFFER_SELECTED,
            buyer=self.buyer,
            assigned_provider=seller,
            title="خرید ورق",
            price_agreed_amount=1_200_000_000,
        )
        offer = OrderOffer.objects.create(
            order=market_order,
            offered_by=seller,
            price_total_amount=1_200_000_000,
            status=OfferStatus.ACCEPTED,
        )
        market_order.selected_offer = offer
        market_order.save(update_fields=["selected_offer"])
        self.client.force_authenticate(self.buyer)

        response = self.client.post(
            "/api/v1/offline-payments/",
            {"source_type": "marketplace_order", "source_id": str(market_order.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["source_type"], "marketplace_order")
