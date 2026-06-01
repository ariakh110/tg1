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

from .models import OfflinePayment, OfflinePaymentStatus


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
            total_amount=500_000,
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

    def test_marketplace_buyer_can_initiate_after_offer_selection(self):
        seller = User.objects.create_user(username="satna-seller", password="pass")
        market_order = Order.objects.create(
            type=OrderType.BUY,
            status=OrderStatus.OFFER_SELECTED,
            buyer=self.buyer,
            assigned_provider=seller,
            title="خرید ورق",
            price_agreed_amount=700_000,
        )
        offer = OrderOffer.objects.create(
            order=market_order,
            offered_by=seller,
            price_total_amount=700_000,
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
