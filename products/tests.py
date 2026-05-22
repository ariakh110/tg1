from django.contrib.auth import get_user_model
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import RoleCode, UserRole

from .models import (
    DeliveryLocation,
    Offer,
    PricingTier,
    Product,
    ProductAuditLog,
    ProductAttributeOption,
    ProductCategory,
    ProductSpecification,
    Seller,
)
from .serializers import ProductSpecificationSerializer

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


class ProductTaxonomyTests(APITestCase):
    def make_product(self, category, name="ورق تست"):
        return Product.objects.create(
            category=category,
            name=name,
            short_description=name,
            description=name,
        )

    def test_category_endpoint_exposes_backend_taxonomy_metadata(self):
        black_sheet = ProductCategory.objects.get(code="sheet-black")

        res = self.client.get("/api/categories/", {"code": "sheet-black"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        item = res.data["results"][0]
        self.assertEqual(item["name"], "ورق سیاه")
        self.assertEqual(item["resolved_product_kind"], "sheet")
        self.assertEqual(item["merged_spec_defaults"]["steel_grade"], "ST37")
        self.assertIn("thickness_mm", item["merged_required_spec_fields"])
        self.assertEqual(item["children_count"], black_sheet.get_children().count())

    def test_spec_serializer_applies_category_defaults_and_required_fields(self):
        category = ProductCategory.objects.get(code="sheet-black-mobarakeh")
        product = self.make_product(category, "ورق ۲ میل مبارکه")

        missing = ProductSpecificationSerializer(
            data={"product": product.id, "width_mm": "1000"}
        )
        self.assertFalse(missing.is_valid())
        self.assertIn("thickness_mm", missing.errors)

        serializer = ProductSpecificationSerializer(
            data={
                "product": product.id,
                "thickness_mm": "2",
                "width_mm": "1000",
                "length_mm": "6000",
                "factory": "mobarakeh",
                "cut_type": "cut",
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        spec = serializer.save()

        self.assertEqual(spec.material_type, "sheet")
        self.assertEqual(spec.steel_grade, "ST37")
        self.assertEqual(spec.surface_finish, "black")
        self.assertEqual(spec.manufacturing_process, "sheet")
        self.assertEqual(spec.factory, "mobarakeh")
        self.assertEqual(spec.cut_type, "cut")

        patch = ProductSpecificationSerializer(
            spec,
            data={"width_mm": "1250"},
            partial=True,
        )
        self.assertTrue(patch.is_valid(), patch.errors)

    def test_non_sheet_category_can_define_specs_without_steel_grade(self):
        category = ProductCategory.objects.get(code="profile-box")
        product = self.make_product(category, "قوطی تست")

        serializer = ProductSpecificationSerializer(
            data={
                "product": product.id,
                "width_mm": "40",
                "height_mm": "40",
                "thickness_mm": "2",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        spec = serializer.save()
        self.assertEqual(spec.material_type, "profile")
        self.assertEqual(spec.steel_grade, "")

    def test_product_filters_include_category_descendants_and_spec_defaults(self):
        mobarakeh = ProductCategory.objects.get(code="sheet-black-mobarakeh")
        sheet = ProductCategory.objects.get(code="sheet")
        oiled = ProductCategory.objects.get(code="sheet-oiled")
        black_product = self.make_product(mobarakeh, "ورق سیاه مبارکه تست")
        parent_registered_product = self.make_product(sheet, "ورق سیاه ثبت شده روی دسته مادر")
        oiled_product = self.make_product(oiled, "ورق روغنی تست")
        ProductSpecification.objects.create(
            product=black_product,
            material_type="sheet",
            steel_grade="ST37",
            surface_finish="black",
            manufacturing_process="sheet",
            factory="mobarakeh",
            cut_type="cut",
            thickness_mm="2",
            width_mm="1000",
            length_mm="6000",
        )
        ProductSpecification.objects.create(
            product=parent_registered_product,
            material_type="sheet",
            steel_grade="ST37",
            surface_finish="black",
            manufacturing_process="sheet",
            factory="mobarakeh",
            cut_type="cut",
            thickness_mm="2",
            width_mm="1250",
            length_mm="6000",
        )
        ProductSpecification.objects.create(
            product=oiled_product,
            material_type="sheet",
            steel_grade="ST12",
            surface_finish="oiled",
            manufacturing_process="sheet",
            factory="mobarakeh",
            cut_type="cut",
            thickness_mm="1",
            width_mm="1000",
            length_mm="6000",
        )

        res = self.client.get(
            "/api/products/",
            {"category_code": "sheet-black", "steel_grade": "ST37", "surface_finish": "black"},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        names = {item["name"] for item in res.data["results"]}
        self.assertIn(black_product.name, names)
        self.assertIn(parent_registered_product.name, names)
        self.assertNotIn(oiled_product.name, names)

    def test_public_product_list_excludes_inactive_products(self):
        category = ProductCategory.objects.get(code="sheet-black-mobarakeh")
        active = self.make_product(category, "ورق فعال")
        inactive = Product.objects.create(
            category=category,
            name="ورق غیر فعال",
            short_description="ورق غیر فعال",
            description="ورق غیر فعال",
            is_active=False,
        )

        res = self.client.get("/api/products/", {"category_code": "sheet-black"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in res.data["results"]}
        self.assertIn(active.id, ids)
        self.assertNotIn(inactive.id, ids)

    def test_active_category_endpoint_exposes_only_matching_product_types(self):
        root = ProductCategory.objects.create(
            name="دسته تست",
            code="test-root",
            product_kind="sheet",
            spec_defaults={"material_type": "sheet"},
        )
        active_category = ProductCategory.objects.create(
            name="دسته فعال تست",
            code="test-active",
            parent=root,
            product_kind="sheet",
            spec_defaults={"surface_finish": "black"},
        )
        inactive_category = ProductCategory.objects.create(
            name="دسته غیر فعال تست",
            code="test-inactive",
            parent=root,
            product_kind="sheet",
            spec_defaults={"surface_finish": "oiled"},
        )
        unrelated_root = ProductCategory.objects.create(name="دسته بی محصول", code="test-empty-root")
        product_on_root = self.make_product(root, "ورق فعال دسته مادر")
        ProductSpecification.objects.create(
            product=product_on_root,
            material_type="sheet",
            steel_grade="ST37",
            surface_finish="black",
            manufacturing_process="sheet",
            factory="mobarakeh",
            cut_type="cut",
            thickness_mm="2",
            width_mm="1000",
            length_mm="6000",
        )
        Product.objects.create(
            category=inactive_category,
            name="ورق غیرفعال دسته",
            short_description="ورق غیرفعال دسته",
            description="ورق غیرفعال دسته",
            is_active=False,
        )

        res = self.client.get("/api/categories/active-with-products/")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        codes = {item["code"] for item in res.data["results"]}
        self.assertIn("test-root", codes)
        self.assertIn("test-active", codes)
        self.assertNotIn("test-inactive", codes)
        self.assertNotIn(unrelated_root.code, codes)

    def test_active_category_endpoint_includes_acid_washed_sheet_when_matching_product_exists(self):
        sheet = ProductCategory.objects.get(code="sheet")
        product = self.make_product(sheet, "ورق اسیدشویی تست")
        ProductSpecification.objects.create(
            product=product,
            material_type="sheet",
            steel_grade="ST37",
            surface_finish="acid_washed",
            manufacturing_process="sheet",
            factory="mobarakeh",
            cut_type="cut",
            thickness_mm="2",
            width_mm="1250",
            length_mm="6000",
        )

        res = self.client.get("/api/categories/active-with-products/")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        codes = {item["code"] for item in res.data["results"]}
        self.assertIn("sheet", codes)
        self.assertIn("sheet-acid-washed", codes)

    def test_sheet_grade_options_depend_on_sheet_type(self):
        black = ProductAttributeOption.objects.get(group="surface_finish", value="black")
        alloy = ProductAttributeOption.objects.get(group="surface_finish", value="alloy")

        black_res = self.client.get("/api/attribute-options/", {"group": "steel_grade", "parent": black.id})
        alloy_res = self.client.get("/api/attribute-options/", {"group": "steel_grade", "parent": alloy.id})

        self.assertEqual(black_res.status_code, status.HTTP_200_OK)
        self.assertEqual(alloy_res.status_code, status.HTTP_200_OK)
        black_values = {item["value"] for item in black_res.data["results"]}
        alloy_values = {item["value"] for item in alloy_res.data["results"]}
        self.assertIn("ST37", black_values)
        self.assertNotIn("CK45", black_values)
        self.assertNotIn("ST52", black_values)
        self.assertIn("CK45", alloy_values)
        self.assertIn("ST52", alloy_values)

    def test_sheet_spec_rejects_grade_not_allowed_for_selected_sheet_type(self):
        sheet = ProductCategory.objects.get(code="sheet")
        product = self.make_product(sheet, "ورق سیاه با گرید نامعتبر")

        serializer = ProductSpecificationSerializer(
            data={
                "product": product.id,
                "material_type": "sheet",
                "steel_grade": "CK45",
                "surface_finish": "black",
                "manufacturing_process": "sheet",
                "factory": "mobarakeh",
                "cut_type": "cut",
                "thickness_mm": "2",
                "width_mm": "1000",
                "length_mm": "6000",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("steel_grade", serializer.errors)

    def test_billet_category_and_grades_are_seeded(self):
        billet = ProductCategory.objects.get(code="billet")
        grades = set(
            ProductAttributeOption.objects.filter(group="steel_grade", product_kind="billet")
            .values_list("value", flat=True)
        )

        self.assertEqual(billet.resolved_product_kind(), "billet")
        self.assertIn("3SP", grades)
        self.assertIn("5SP", grades)

    def test_product_list_returns_min_price_and_origin_for_market_rows(self):
        user = User.objects.create_user(username="origin_seller", password="pass1234")
        seller = Seller.objects.create(
            user=user,
            company_name="فولاد مبارکه",
            business_type="Factory",
            location="اصفهان",
            is_verified=True,
        )
        category = ProductCategory.objects.get(code="sheet-black-mobarakeh")
        product = self.make_product(category, "ورق سیاه ۲ میل مبارکه")
        ProductSpecification.objects.create(
            product=product,
            material_type="sheet",
            steel_grade="ST37",
            surface_finish="black",
            manufacturing_process="sheet",
            factory="mobarakeh",
            cut_type="cut",
            thickness_mm="2",
            width_mm="1000",
            length_mm="6000",
        )
        offer = Offer.objects.create(product=product, seller=seller)
        PricingTier.objects.create(
            offer=offer,
            tier_name="قیمت روز",
            unit_price="42000",
            minimum_quantity=1,
        )
        DeliveryLocation.objects.create(
            offer=offer,
            incoterm="EXW",
            country="ایران",
            province="اصفهان",
            city="مبارکه",
            address="کارخانه",
        )

        res = self.client.get("/api/products/", {"category": category.parent_id})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        item = next(row for row in res.data["results"] if row["id"] == product.id)
        self.assertEqual(item["min_price"], "42000.00")
        delivery = item["offers"][0]["delivery_options"][0]
        self.assertEqual(delivery["province"], "اصفهان")
        self.assertEqual(delivery["city"], "مبارکه")
        self.assertEqual(delivery["address"], "کارخانه")

    def test_attribute_options_endpoint_filters_backend_combo_options(self):
        province = ProductAttributeOption.objects.get(group="province", value="isfahan")

        res = self.client.get(
            "/api/attribute-options/",
            {"group": "city", "parent": province.id},
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        labels = {item["label"] for item in res.data["results"]}
        self.assertIn("مبارکه", labels)


class AdminProductImportTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="product_admin",
            password="pass1234",
            is_staff=True,
        )
        self.seller_user = User.objects.create_user(username="price_seller", password="pass1234")
        self.seller = Seller.objects.create(
            user=self.seller_user,
            company_name="کاوه متال",
            business_type="Trading",
            location="تهران",
            is_verified=True,
        )

    def test_admin_can_create_product_with_price_and_origin(self):
        self.client.force_authenticate(self.admin)

        res = self.client.post(
            "/api/products/admin-upsert/",
            {
                "name": "ورق سیاه ۲ میل مبارکه ادمین",
                "category_code": "sheet",
                "seller_id": self.seller.id,
                "price": "45000",
                "steel_grade": "ST37",
                "manufacturing_process": "sheet",
                "surface_finish": "black",
                "factory": "mobarakeh",
                "cut_type": "cut",
                "thickness_mm": "2",
                "width_mm": "1000",
                "length_mm": "6000",
                "province": "اصفهان",
                "city": "مبارکه",
                "address": "کارخانه",
            },
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        product = Product.objects.get(id=res.data["product_id"])
        self.assertEqual(product.category.code, "sheet")
        self.assertEqual(product.specifications.steel_grade, "ST37")
        self.assertEqual(product.specifications.factory, "mobarakeh")
        offer = product.offers.get(seller=self.seller)
        self.assertEqual(str(offer.pricing_tiers.get(tier_name="قیمت روز").unit_price), "45000.00")
        self.assertEqual(offer.delivery_options.get().city, "مبارکه")

    def test_admin_can_create_coil_without_length_or_price(self):
        self.client.force_authenticate(self.admin)

        res = self.client.post(
            "/api/products/admin-upsert/",
            {
                "name": "رول سیاه مبارکه بدون قیمت",
                "category_code": "sheet",
                "steel_grade": "ST37",
                "manufacturing_process": "coil",
                "surface_finish": "black",
                "factory": "mobarakeh",
                "thickness_mm": "2",
                "width_mm": "1250",
            },
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        product = Product.objects.get(id=res.data["product_id"])
        self.assertEqual(product.specifications.manufacturing_process, "coil")
        self.assertIsNone(product.specifications.length_mm)
        self.assertFalse(product.offers.exists())

    def test_admin_product_rejects_unknown_factory_option(self):
        self.client.force_authenticate(self.admin)

        res = self.client.post(
            "/api/products/admin-upsert/",
            {
                "name": "ورق کارخانه نامعتبر",
                "category_code": "sheet",
                "steel_grade": "ST37",
                "manufacturing_process": "sheet",
                "surface_finish": "black",
                "factory": "unknown_factory",
                "thickness_mm": "2",
                "width_mm": "1250",
                "length_mm": "6000",
            },
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("factory", res.data["detail"])

    def test_admin_bulk_xlsx_updates_existing_product_price(self):
        from openpyxl import Workbook

        category = ProductCategory.objects.get(code="sheet-black-mobarakeh")
        product = Product.objects.create(
            category=category,
            name="ورق سیاه فایل اکسل",
            short_description="ورق سیاه فایل اکسل",
            description="ورق سیاه فایل اکسل",
        )
        ProductSpecification.objects.create(
            product=product,
            material_type="sheet",
            steel_grade="ST37",
            surface_finish="black",
            manufacturing_process="sheet",
            factory="mobarakeh",
            cut_type="cut",
            thickness_mm="2",
            width_mm="1000",
            length_mm="6000",
        )
        offer = Offer.objects.create(product=product, seller=self.seller)
        PricingTier.objects.create(
            offer=offer,
            tier_name="قیمت روز",
            unit_price="41000",
            minimum_quantity=1,
        )

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["شناسه محصول", "شناسه فروشنده", "قیمت جدید", "استان", "شهر"])
        sheet.append([product.id, self.seller.id, 47000, "اصفهان", "مبارکه"])
        payload = BytesIO()
        workbook.save(payload)
        payload.seek(0)
        upload = SimpleUploadedFile(
            "prices.xlsx",
            payload.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        self.client.force_authenticate(self.admin)
        res = self.client.post(
            "/api/products/admin-bulk-upsert/",
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(res.data["updated_prices"], 1)
        tier = PricingTier.objects.get(offer=offer, tier_name="قیمت روز")
        tier.refresh_from_db()
        self.assertEqual(str(tier.unit_price), "47000.00")
        self.assertEqual(offer.delivery_options.get().province, "اصفهان")

    def test_admin_can_download_product_import_template(self):
        self.client.force_authenticate(self.admin)

        res = self.client.get("/api/products/admin-import-template/")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("kavehmetal-products-template.xlsx", res["Content-Disposition"])

    def test_admin_products_list_includes_inactive_products_with_filters(self):
        category = ProductCategory.objects.get(code="sheet-black-mobarakeh")
        active = Product.objects.create(
            category=category,
            name="محصول فعال ادمین",
            short_description="محصول فعال ادمین",
            description="محصول فعال ادمین",
            is_active=True,
        )
        inactive = Product.objects.create(
            category=category,
            name="محصول غیرفعال ادمین",
            short_description="محصول غیرفعال ادمین",
            description="محصول غیرفعال ادمین",
            is_active=False,
        )
        self.client.force_authenticate(self.admin)

        default_res = self.client.get("/api/products/admin-products/")
        all_res = self.client.get("/api/products/admin-products/", {"is_active": "all"})
        inactive_res = self.client.get("/api/products/admin-products/", {"is_active": "false"})

        self.assertEqual(default_res.status_code, status.HTTP_200_OK)
        default_ids = {item["id"] for item in default_res.data["results"]}
        self.assertIn(active.id, default_ids)
        self.assertIn(inactive.id, default_ids)
        self.assertEqual(all_res.status_code, status.HTTP_200_OK)
        all_ids = {item["id"] for item in all_res.data["results"]}
        self.assertIn(active.id, all_ids)
        self.assertIn(inactive.id, all_ids)
        self.assertEqual(inactive_res.status_code, status.HTTP_200_OK)
        inactive_ids = {item["id"] for item in inactive_res.data["results"]}
        self.assertIn(inactive.id, inactive_ids)
        self.assertNotIn(active.id, inactive_ids)

    def test_admin_can_deactivate_reactivate_and_activity_is_logged(self):
        category = ProductCategory.objects.get(code="sheet-black-mobarakeh")
        product = Product.objects.create(
            category=category,
            name="محصول وضعیت ادمین",
            short_description="محصول وضعیت ادمین",
            description="محصول وضعیت ادمین",
            is_active=True,
        )
        self.client.force_authenticate(self.admin)

        deactivated = self.client.post(f"/api/products/{product.id}/deactivate/")
        product.refresh_from_db()
        activity = self.client.get("/api/v1/admin/dashboard/activities/", {"limit": 20})
        is_deactivated = not product.is_active
        activated = self.client.post(f"/api/products/{product.id}/activate/")
        product.refresh_from_db()

        self.assertEqual(deactivated.status_code, status.HTTP_200_OK, deactivated.data)
        self.assertTrue(is_deactivated)
        self.assertTrue(ProductAuditLog.objects.filter(product=product, action="PRODUCT_DEACTIVATED").exists())
        self.assertEqual(activity.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any(item["kind"] == "PRODUCT_AUDIT" for item in activity.data["results"])
        )
        self.assertEqual(activated.status_code, status.HTTP_200_OK, activated.data)
        self.assertTrue(product.is_active)
        self.assertTrue(ProductAuditLog.objects.filter(product=product, action="PRODUCT_ACTIVATED").exists())

    def test_admin_can_delete_product_and_keep_audit_log(self):
        category = ProductCategory.objects.get(code="sheet-black-mobarakeh")
        product = Product.objects.create(
            category=category,
            name="محصول حذف ادمین",
            short_description="محصول حذف ادمین",
            description="محصول حذف ادمین",
            is_active=True,
        )
        product_id = product.id
        self.client.force_authenticate(self.admin)

        res = self.client.delete(f"/api/products/{product_id}/")

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(id=product_id).exists())
        log = ProductAuditLog.objects.get(action="PRODUCT_DELETED", product_name="محصول حذف ادمین")
        self.assertIsNone(log.product_id)
        self.assertEqual(log.payload["product_id"], product_id)

    def test_admin_taxonomy_create_actions_are_logged(self):
        self.client.force_authenticate(self.admin)
        sheet = ProductCategory.objects.get(code="sheet")
        black = ProductAttributeOption.objects.get(group="surface_finish", value="black")

        category_res = self.client.post(
            "/api/categories/",
            {
                "name": "ورق تست لاگ",
                "code": "sheet-log-test",
                "parent": sheet.id,
                "product_kind": "sheet",
                "spec_defaults": {"material_type": "sheet", "surface_finish": "black"},
                "required_spec_fields": ["steel_grade", "thickness_mm", "width_mm"],
                "sort_order": 999,
                "is_active": True,
            },
            format="json",
        )
        option_res = self.client.post(
            "/api/attribute-options/",
            {
                "group": "steel_grade",
                "value": "LOGTEST",
                "label": "گرید تست لاگ",
                "product_kind": "sheet",
                "parent": black.id,
                "sort_order": 999,
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(category_res.status_code, status.HTTP_201_CREATED, category_res.data)
        self.assertEqual(option_res.status_code, status.HTTP_201_CREATED, option_res.data)
        self.assertTrue(
            ProductAuditLog.objects.filter(
                action="PRODUCT_CATEGORY_CREATED",
                product_name="ورق تست لاگ",
            ).exists()
        )
        self.assertTrue(
            ProductAuditLog.objects.filter(
                action="TAXONOMY_OPTION_CREATED",
                product_name="گرید تست لاگ",
            ).exists()
        )

    def test_non_admin_cannot_use_admin_product_import(self):
        user = User.objects.create_user(username="regular_user", password="pass1234")
        self.client.force_authenticate(user)

        res = self.client.post(
            "/api/products/admin-upsert/",
            {
                "name": "نباید ثبت شود",
                "category_code": "sheet-black-mobarakeh",
                "seller_id": self.seller.id,
                "price": "45000",
            },
            format="json",
        )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
