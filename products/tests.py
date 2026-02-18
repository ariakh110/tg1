from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import RoleCode, UserRole

from .models import Offer, Product, ProductCategory, Seller

User = get_user_model()


class SellerProfileTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="seller_user", password="pass1234")

    def test_create_seller_profile_is_idempotent(self):
        self.client.force_authenticate(self.user)
        payload = {
            "company_name": "Alpha Steel",
            "business_type": "Trading",
            "location": "Tehran",
        }
        first = self.client.post("/api/sellers/", payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        seller_id = first.data["id"]

        second = self.client.post("/api/sellers/", payload, format="json")
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.data["id"], seller_id)


class ProductAssetPermissionTests(APITestCase):
    def setUp(self):
        self.seller_owner_user = User.objects.create_user(
            username="seller_owner", password="pass1234"
        )
        self.seller_other_user = User.objects.create_user(
            username="seller_other", password="pass1234"
        )

        UserRole.objects.update_or_create(
            user=self.seller_owner_user,
            role=RoleCode.SELLER,
            defaults={"is_active": True, "activated_at": timezone.now()},
        )
        UserRole.objects.update_or_create(
            user=self.seller_other_user,
            role=RoleCode.SELLER,
            defaults={"is_active": True, "activated_at": timezone.now()},
        )

        self.owner_seller = Seller.objects.create(
            user=self.seller_owner_user,
            company_name="Owner Co",
            business_type="Trading",
            location="Isfahan",
            is_verified=True,
        )
        self.other_seller = Seller.objects.create(
            user=self.seller_other_user,
            company_name="Other Co",
            business_type="Trading",
            location="Shiraz",
            is_verified=True,
        )

        category = ProductCategory.objects.create(name="Permission Steel")
        self.product = Product.objects.create(
            category=category,
            name="Hot Rolled Coil",
            short_description="HRC",
            description="HRC product",
        )
        Offer.objects.create(product=self.product, seller=self.owner_seller, is_active=True)

    def test_only_offer_owner_can_upload_product_image(self):
        image = SimpleUploadedFile(
            "sample.jpg",
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b",
            content_type="image/jpeg",
        )

        self.client.force_authenticate(self.seller_other_user)
        forbidden = self.client.post(
            "/api/product-images/",
            {"product": self.product.id, "image": image},
            format="multipart",
        )
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        image_ok = SimpleUploadedFile(
            "sample2.jpg",
            b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b",
            content_type="image/jpeg",
        )
        self.client.force_authenticate(self.seller_owner_user)
        allowed = self.client.post(
            "/api/product-images/",
            {"product": self.product.id, "image": image_ok},
            format="multipart",
        )
        self.assertEqual(allowed.status_code, status.HTTP_201_CREATED)
