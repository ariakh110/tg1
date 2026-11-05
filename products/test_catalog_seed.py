"""Pinned catalog import: real DB safety and native API contract tests."""
import io
import json
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model

from products.catalog_seed import SeedError, load_package, seed_sections
from products.models import (
    Product, ProductCategory, ProductSpecification, ProductAttributeOption,
    SpecificationAttribute, SpecificationValue, ProductAuditLog, Offer, PricingTier,
)
from products.views import ProductViewSet


class CatalogSeedTests(TestCase):
    def setUp(self):
        self.package, self.digest = load_package()
        self.baseline = self.counts()

    def counts(self):
        return tuple(model.objects.count() for model in (
            Product, ProductCategory, ProductSpecification, ProductAttributeOption,
            SpecificationAttribute, SpecificationValue, ProductAuditLog, Offer, PricingTier,
        ))

    def existing(self, row=None, slug="existing-physical-product"):
        row = row or self.package['products'][0]
        categories = {}
        for item in self.package['categories']:
            data = {k: v for k, v in item.items() if k != 'parent_code'}
            categories[item['code']] = ProductCategory.objects.create(
                **data, parent=categories.get(item['parent_code']))
        product = Product.objects.create(category=categories[row['category_code']],
                                         name='My edited name', slug=slug, is_active=True)
        ProductSpecification.objects.create(product=product, **row['specifications'])
        for dynamic in row['dynamic_specs']:
            attribute = SpecificationAttribute.objects.create(
                name=dynamic['name'], unit=dynamic['unit'])
            SpecificationValue.objects.create(product=product, attribute=attribute,
                                              value=dynamic['value'])
        return product

    def test_preview_and_default_command_are_read_only(self):
        before = self.counts()
        report = seed_sections()
        self.assertEqual(report['new_count'], 149)
        self.assertEqual(report['quarantined_count'], 3)
        output = io.StringIO()
        call_command('seed_farda_sections', stdout=output)
        self.assertEqual(json.loads(output.getvalue())['new_count'], 149)
        self.assertEqual(before, self.counts())

    def test_apply_creates_native_inactive_price_free_catalog(self):
        report = seed_sections(apply=True, actor='test')
        self.assertEqual(report['created_count'], 149)
        self.assertEqual(tuple(a - b for a, b in zip(self.counts(), self.baseline)),
                         (149, 8, 149, 18, 1, 65, 150, 0, 0))
        self.assertFalse(Product.objects.filter(is_active=True).exists())
        self.assertFalse(ProductCategory.objects.filter(
            code__in=[c['code'] for c in self.package['categories']], is_active=True).exists())
        self.assertEqual(Product.objects.exclude(seo_index_mode='noindex').count(), 0)
        self.assertEqual(Product.objects.exclude(availability_status='inquiry').count(), 0)
        self.assertEqual(ProductSpecification.objects.filter(material_type='angle').count(), 84)
        for spec in ProductSpecification.objects.filter(material_type='channel'):
            self.assertIsNone(spec.height_mm)
            self.assertIsNone(spec.thickness_mm)
            self.assertIsNone(spec.weight_kg_per_unit)
        product = Product.objects.first()
        self.assertIn('<table>', product.description)
        self.assertTrue(product.seo_title and product.page_h1 and product.meta_description)
        self.assertEqual(len(product.seo_faqs), 2)
        self.assertFalse(product.is_search_indexable())
        audit = product.audit_logs.get(action='CATALOG_SEED_CREATED')
        self.assertEqual(audit.payload['actor'], 'test')
        self.assertTrue(audit.payload['source_observations'])

    def test_requires_actor_and_correct_hash_before_any_writes(self):
        with self.assertRaises(SeedError):
            seed_sections(apply=True)
        with self.assertRaises(SeedError):
            seed_sections(apply=True, actor='test', expected_sha256='0' * 64)
        self.assertEqual(self.counts(), self.baseline)
        with self.assertRaises(CommandError):
            call_command('seed_farda_sections', apply=True, stdout=io.StringIO())

    def test_modified_package_bytes_are_rejected(self):
        with patch('products.catalog_seed.Path.read_bytes', return_value=b'{}'):
            with self.assertRaises(SeedError):
                load_package()

    def test_repeat_preserves_edits_activation_and_deletion(self):
        seed_sections(apply=True, actor='test')
        edited, removed = list(Product.objects.order_by('pk')[:2])
        edited.name, edited.slug, edited.is_active = 'Edited', 'new-slug', True
        edited.seo_index_mode = 'index'
        edited.save()
        removed.delete()
        before = self.counts()
        report = seed_sections(apply=True, actor='repeat')
        self.assertTrue(report['already_applied'])
        self.assertEqual(report['created_count'], 0)
        edited.refresh_from_db()
        self.assertEqual((edited.name, edited.slug, edited.is_active), ('Edited', 'new-slug', True))
        self.assertEqual(before, self.counts())

    def test_existing_technical_identity_skipped_without_overwrite(self):
        existing = self.existing()
        report = seed_sections(apply=True, actor='test')
        self.assertEqual(report['created_count'], 148)
        self.assertEqual(report['skipped_count'], 1)
        existing.refresh_from_db()
        self.assertEqual(existing.name, 'My edited name')
        self.assertTrue(existing.is_active)

    def test_duplicate_physical_identity_is_conflict(self):
        product = self.existing()
        duplicate = Product.objects.create(category=product.category, name=product.name,
                                           slug='duplicate')
        ProductSpecification.objects.create(product=duplicate,
            **self.package['products'][0]['specifications'])
        before = self.counts()
        with self.assertRaises(SeedError):
            seed_sections(apply=True, actor='test')
        self.assertEqual(before, self.counts())

    def test_slug_collision_blocks_whole_batch(self):
        Product.objects.create(name='Unrelated', slug=self.package['products'][0]['product']['slug'])
        before = self.counts()
        with self.assertRaises(SeedError):
            seed_sections(apply=True, actor='test')
        self.assertEqual(before, self.counts())

    def test_incompatible_category_blocks_without_changes(self):
        ProductCategory.objects.create(code='angle', name='Other', product_kind='sheet')
        before = self.counts()
        with self.assertRaises(SeedError):
            seed_sections(apply=True, actor='test')
        self.assertEqual(before, self.counts())

    def test_ambiguous_or_disabled_option_blocks_without_changes(self):
        item = self.package['factory_options'][0]
        option = ProductAttributeOption.objects.create(**item, is_active=False)
        with self.assertRaises(SeedError):
            seed_sections(apply=True, actor='test')
        option.is_active = True
        option.save()
        ProductAttributeOption.objects.create(**item)
        with self.assertRaises(SeedError):
            seed_sections(apply=True, actor='test')
        self.assertEqual(Product.objects.count(), 0)

    def test_ambiguous_nominal_attribute_blocks(self):
        name = next(r for r in self.package['products'] if r['dynamic_specs'])['dynamic_specs'][0]['name']
        SpecificationAttribute.objects.create(name=name, unit='')
        SpecificationAttribute.objects.create(name=name, unit='')
        with self.assertRaises(SeedError):
            seed_sections(apply=True, actor='test')
        self.assertEqual(Product.objects.count(), 0)

    def test_duplicate_nominal_values_do_not_create_a_duplicate_product(self):
        row = next(r for r in self.package['products'] if r['dynamic_specs'])
        product = self.existing(row)
        value = product.dynamic_specs.get()
        SpecificationValue.objects.create(product=product, attribute=value.attribute, value=value.value)
        before = self.counts()
        with self.assertRaises(SeedError):
            seed_sections(apply=True, actor='test')
        self.assertEqual(before, self.counts())

    def test_missing_or_incompatible_batch_receipt_requires_manual_review(self):
        seed_sections(apply=True, actor='test')
        receipt = ProductAuditLog.objects.get(action='CATALOG_SEED_BATCH')
        receipt.payload['sha256'] = 'invalid'
        receipt.save()
        with self.assertRaises(SeedError):
            seed_sections()
        receipt.delete()
        with self.assertRaises(SeedError):
            seed_sections(apply=True, actor='test')

    def test_apply_command_and_replay_report_valid_json(self):
        output = io.StringIO()
        call_command('seed_farda_sections', apply=True, actor='test', stdout=output)
        self.assertEqual(json.loads(output.getvalue())['created_count'], 149)
        output = io.StringIO()
        call_command('seed_farda_sections', apply=True, actor='test', stdout=output)
        self.assertTrue(json.loads(output.getvalue())['already_applied'])

    def test_mid_batch_failure_rolls_back_taxonomy_products_and_audits(self):
        original = Product.save
        def fail_second(product, *args, **kwargs):
            if Product.objects.exists():
                raise RuntimeError('injected database write failure')
            return original(product, *args, **kwargs)
        with patch.object(Product, 'save', fail_second):
            with self.assertRaises(RuntimeError):
                seed_sections(apply=True, actor='test')
        self.assertEqual(self.counts(), self.baseline)

    def test_native_public_and_admin_detail_contract(self):
        seed_sections(apply=True, actor='test')
        product = Product.objects.first()
        view = ProductViewSet.as_view({'get': 'retrieve'})
        factory = APIRequestFactory()
        request = factory.get('/api/products/products/' + product.slug + '/')
        self.assertEqual(view(request, pk=product.slug).status_code, 404)
        user = get_user_model().objects.create_superuser(
            username='catalog-admin', email='catalog@example.test', password='test-only-password')
        force_authenticate(request, user=user)
        response = view(request, pk=product.slug)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['seo_title'], product.seo_title)
        self.assertEqual(response.data['page_h1'], product.page_h1)
        self.assertEqual(response.data['offers'], [])
