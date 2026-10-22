import tempfile
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.core.cache import caches
from rest_framework.test import APITestCase
from accounts.models import UserRole, RoleCode
from assistant.models import AssistantSettings
from products.models import Product, ProductCategory, Seller, Offer, ProductDocument


class SecurityRegressionTests(APITestCase):
    def setUp(self):
        self.media=tempfile.TemporaryDirectory(prefix="probe-media-", dir=None)
        self.settings_override=override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.addCleanup(self.media.cleanup)
        self.addCleanup(self.settings_override.disable)
        self.attacker=get_user_model().objects.create_user("audit-seller", password="test-only")
        UserRole.objects.create(user=self.attacker, role=RoleCode.SELLER, is_active=True)
        self.seller=Seller.objects.create(user=self.attacker, company_name="Audit", business_type="Trading", location="Test")
        self.category=ProductCategory.objects.create(name="Audit generic", code="ecc-audit-generic")
        self.own=Product.objects.create(name="Audit own", category=self.category)
        self.foreign=Product.objects.create(name="Audit foreign", category=self.category)
        Offer.objects.create(product=self.own, seller=self.seller)
        other=get_user_model().objects.create_user("audit-other-seller",password="test-only")
        other_seller=Seller.objects.create(user=other,company_name="Other",business_type="Trading",location="Test")
        Offer.objects.create(product=self.foreign,seller=other_seller)
        caches["authentication"].clear()
        self.client.force_authenticate(self.attacker)

    def test_document_upload_rejects_active_html(self):
        response=self.client.post("/api/product-documents/", {"product":self.own.id,"title":"Audit HTML", "file":SimpleUploadedFile("ecc-audit.html", b"<html><script>window.__eccAudit=1</script></html>",content_type="text/html")},format="multipart")
        self.assertEqual(response.status_code,400,"Active HTML accepted as a public product document")

    def test_document_cannot_be_reassigned_to_foreign_product(self):
        document=ProductDocument.objects.create(product=self.own,title="Audit PDF",file=SimpleUploadedFile("audit.pdf",b"%PDF-1.4 audit"))
        response=self.client.patch(f"/api/product-documents/{document.id}/",{"product":self.foreign.id},format="json")
        document.refresh_from_db()
        self.assertIn(response.status_code,[400,403,404],"Seller can move a document onto an unowned product")

    def test_seller_cannot_create_foreign_product_spec(self):
        response=self.client.post("/api/specifications/",{"product":self.foreign.id},format="json")
        self.assertIn(response.status_code,[400,403,404],"Seller can create specifications for an unowned product")

    def test_landing_public_html_is_sanitized(self):
        staff=get_user_model().objects.create_user("audit-editor",password="test-only",is_staff=True)
        self.client.force_authenticate(staff)
        response=self.client.post("/api/blog/admin/landings/",{"family":"audit","slug":"ecc-audit","title":"Audit", "body":"<img src=x onerror=window.__eccAudit=1>","is_active":True},format="json")
        self.assertEqual(response.status_code,201,response.data)
        self.client.force_authenticate(None)
        result=self.client.get("/api/blog/landings/?family=audit&slug=ecc-audit")
        body=result.data[0]["body"]
        self.assertNotIn("onerror",body,"Stored event handler is returned to the public landing page")

    @patch("assistant.views.run_chat",return_value="audit reply")
    def test_public_assistant_limits_request_bursts(self,chat):
        cfg=AssistantSettings.load();cfg.is_enabled=True;cfg.save()
        self.client.force_authenticate(None)
        statuses=[self.client.post("/api/assistant/chat/",{"message":"audit","session_key":"ecc-audit-session"},format="json").status_code for _ in range(12)]
        self.assertIn(429,statuses,"Public AI endpoint has no application-level request burst limit")

    def test_valid_pdf_upload_and_title_edit_remain_allowed(self):
        response = self.client.post("/api/product-documents/", {
            "product": self.own.pk, "title": "Technical document",
            "file": SimpleUploadedFile("technical.pdf", b"%PDF-1.7 test document"),
        }, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        response = self.client.patch(f"/api/product-documents/{response.data['id']}/", {"title": "Updated"})
        self.assertEqual(response.status_code, 200, response.data)

    def test_document_signature_and_size_are_checked(self):
        from products.document_validation import validate_product_document, MAX_DOCUMENT_SIZE
        from rest_framework.exceptions import ValidationError
        for name, content in [("fake.pdf", b"<html>bad</html>"), ("active.svg", b"<svg/>"), ("empty.pdf", b"")]:
            with self.subTest(name=name), self.assertRaises(ValidationError):
                validate_product_document(SimpleUploadedFile(name, content))
        upload = SimpleUploadedFile("large.pdf", b"%PDF-1.7")
        upload.size = MAX_DOCUMENT_SIZE + 1
        with self.assertRaises(ValidationError):
            validate_product_document(upload)
        for name, content in [("drawing.dwg", b"AC1032test"), ("drawing.dxf", b"0\nSECTION\n2\nHEADER\n")]:
            upload = SimpleUploadedFile(name, content)
            self.assertIs(validate_product_document(upload), upload)
            self.assertEqual(upload.tell(), 0)

    def test_owner_can_create_and_edit_specs_but_not_reparent(self):
        response = self.client.post("/api/specifications/", {"product": self.own.pk})
        self.assertEqual(response.status_code, 201, response.data)
        url = f"/api/specifications/{response.data['id']}/"
        self.assertEqual(self.client.patch(url, {"thickness_mm": "5.00"}).status_code, 200)
        self.assertEqual(self.client.patch(url, {"product": self.foreign.pk}).status_code, 400)
        from products.models import ProductSpecification
        spec = ProductSpecification.objects.create(product=self.foreign)
        self.assertEqual(self.client.patch(f"/api/specifications/{spec.pk}/", {"thickness_mm": "6.00"}).status_code, 403)

    def test_staff_can_manage_foreign_specs(self):
        staff = get_user_model().objects.create_user("spec-admin", is_staff=True)
        self.client.force_authenticate(staff)
        response = self.client.post("/api/specifications/", {"product": self.foreign.pk})
        self.assertEqual(response.status_code, 201, response.data)

    def test_legacy_landing_is_sanitized_on_read_and_by_cleanup(self):
        from blog.models import Landing
        from blog.serializers import LandingSerializer
        from django.apps import apps
        from django.db import connection
        from importlib import import_module
        landing = Landing.objects.create(family="legacy", slug="legacy", title="Legacy", body='<h2>Title</h2><img src="/safe.png" onerror="bad()"><a href="javascript:bad()">Link</a>')
        body = LandingSerializer(landing).data["body"]
        self.assertIn("<h2>Title</h2>", body)
        self.assertNotIn("onerror", body)
        self.assertNotIn("javascript:", body)
        migration = import_module("blog.migrations.0013_sanitize_landing_bodies")
        from types import SimpleNamespace
        migration.sanitize_existing_bodies(apps, SimpleNamespace(connection=connection))
        landing.refresh_from_db()
        self.assertEqual(landing.body, body)
        from types import SimpleNamespace
        migration.sanitize_existing_bodies(apps, SimpleNamespace(connection=connection))
        landing.refresh_from_db()
        self.assertEqual(landing.body, body)
