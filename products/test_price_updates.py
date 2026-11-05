from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from products.models import (Product, ProductSpecification, Seller, Offer, PricingTier,
                             DeliveryLocation, ProductAuditLog)


class PriceOnlyTests(APITestCase):
    def setUp(self):
        users = get_user_model()
        self.admin = users.objects.create_user('amount-admin', is_staff=True)
        self.other = users.objects.create_user('amount-other')
        self.seller = Seller.objects.create(user=self.other, company_name='Seller A',
                                            business_type='Trading', location='Test')
        second = users.objects.create_user('amount-second')
        self.seller2 = Seller.objects.create(user=second, company_name='Seller B',
                                             business_type='Trading', location='Elsewhere')
        self.product = Product.objects.create(name='Keep name', slug='keep-slug',
            description='<p>Keep content</p>', seo_title='Keep SEO', availability_status='out_of_stock')
        self.spec = ProductSpecification.objects.create(product=self.product, material_type='rebar',
            steel_grade='A3', diameter_mm='12', length_mm='12000', factory='keep-factory')
        self.offer = Offer.objects.create(product=self.product, seller=self.seller)
        self.tier = PricingTier.objects.create(offer=self.offer, tier_name='Custom condition',
            unit_price='50000.25', price_basis='ton', minimum_quantity=7, maximum_quantity=99,
            condition_label='Keep condition', dimension_width_mm='100', dimension_length_mm='200',
            is_negotiable=True)
        self.offer2 = Offer.objects.create(product=self.product, seller=self.seller2)
        self.tier2 = PricingTier.objects.create(offer=self.offer2, tier_name='Other seller',
            unit_price='40000', price_basis='kg', minimum_quantity=2)
        DeliveryLocation.objects.create(offer=self.offer, incoterm='EXW', country='Iran',
                                        province='Test', city='Keep city', address='Keep address')
        self.client.force_authenticate(self.admin)

    def snapshot(self):
        return {model.__name__: list(model.objects.order_by('pk').values()) for model in (
            Product, ProductSpecification, Seller, Offer, PricingTier, DeliveryLocation, ProductAuditLog)}

    def post(self, rows):
        return self.client.post('/api/products/admin-bulk-prices/', {'prices': rows}, format='json')

    def test_changes_only_exact_amount_and_verification_metadata(self):
        before = self.snapshot()
        response = self.post([{'tier_id': self.tier.pk, 'price': '52000.50', 'expected_price': '50000.25'}])
        self.assertEqual(response.status_code, 200, response.data)
        after = self.snapshot()
        for name in ('Product', 'ProductSpecification', 'Seller', 'Offer', 'DeliveryLocation'):
            self.assertEqual(after[name], before[name], name)
        old = next(r for r in before['PricingTier'] if r['id'] == self.tier.pk)
        new = next(r for r in after['PricingTier'] if r['id'] == self.tier.pk)
        self.assertEqual({k for k in old if old[k] != new[k]}, {'unit_price', 'price_verified_at'})
        self.assertEqual(new['unit_price'], Decimal('52000.50'))
        self.assertEqual(after['PricingTier'][1], before['PricingTier'][1])
        self.assertEqual(len(after['PricingTier']), 2)
        self.assertEqual(ProductAuditLog.objects.filter(action='PRODUCT_PRICE_UPDATED').count(), 1)

    def test_invalid_batch_is_atomic_and_does_not_clear_or_rewrite(self):
        for bad in ('', None, '0', '-1', 'NaN', 'Infinity', '1.234', '1,2', '12345678901'):
            with self.subTest(price=bad):
                before = self.snapshot()
                response = self.post([{'tier_id': self.tier.pk, 'price': '52000'},
                                      {'tier_id': self.tier2.pk, 'price': bad}])
                self.assertEqual(response.status_code, 400, response.data)
                self.assertEqual(self.snapshot(), before)

    def test_stale_duplicate_missing_and_extra_fields_are_rejected(self):
        rows = [
            [{'tier_id': self.tier.pk, 'price': '52000', 'expected_price': '3'}],
            [{'tier_id': self.tier.pk, 'price': '52000'}, {'tier_id': self.tier.pk, 'price': '53000'}],
            [{'tier_id': 999999, 'price': '52000'}],
            [{'tier_id': self.tier.pk, 'price': '52000', 'name': 'Do not rename'}],
            [{'tier_id': self.tier.pk, 'price': '52000', 'price_basis': 'kg'}],
        ]
        for batch in rows:
            with self.subTest(batch=batch):
                before = self.snapshot()
                self.assertEqual(self.post(batch).status_code, 400)
                self.assertEqual(self.snapshot(), before)

    def test_legacy_product_id_is_allowed_only_for_one_existing_tier(self):
        before = self.snapshot()
        self.assertEqual(self.post([{'product_id': self.product.pk, 'price': '53000'}]).status_code, 400)
        self.assertEqual(self.snapshot(), before)
        self.tier2.delete()
        response = self.post([{'product_id': self.product.pk, 'price': '53000'}])
        self.assertEqual(response.status_code, 200, response.data)
        self.tier.refresh_from_db()
        self.assertEqual(self.tier.unit_price, Decimal('53000'))
        self.assertEqual(self.tier.price_basis, 'ton')

    def test_unpriced_product_does_not_create_any_offer_or_tier(self):
        product = Product.objects.create(name='Unpriced')
        before = self.snapshot()
        self.assertEqual(self.post([{'product_id': product.pk, 'price': '53000'}]).status_code, 400)
        self.assertEqual(self.snapshot(), before)

    def test_admin_rows_identify_exact_tier_seller_basis_and_conditions(self):
        response = self.client.get('/api/products/admin-price-rows/', {'page_size': 100})
        self.assertEqual(response.status_code, 200, response.data)
        rows = response.data['results']
        self.assertEqual({r['tier_id'] for r in rows}, {self.tier.pk, self.tier2.pk})
        row = next(r for r in rows if r['tier_id'] == self.tier.pk)
        self.assertEqual(row['seller_name'], 'Seller A')
        self.assertEqual(row['price_basis'], 'ton')
        self.assertEqual(row['condition_label'], 'Keep condition')
        self.assertEqual(row['unit_price'], '50000.25')

    def test_non_admin_cannot_read_or_write_editor_rows(self):
        self.client.force_authenticate(self.other)
        before = self.snapshot()
        self.assertEqual(self.client.get('/api/products/admin-price-rows/').status_code, 403)
        self.assertEqual(self.post([{'tier_id': self.tier.pk, 'price': '53000'}]).status_code, 403)
        self.assertEqual(self.snapshot(), before)

    def test_admin_rows_preserve_distinguishing_dimension_and_quantity_conditions(self):
        twin = PricingTier.objects.create(offer=self.offer, tier_name=self.tier.tier_name,
            unit_price=self.tier.unit_price, price_basis='ton', minimum_quantity=10,
            maximum_quantity=100, condition_label=self.tier.condition_label,
            dimension_width_mm='120', dimension_length_mm='240', is_negotiable=False)
        response = self.client.get('/api/products/admin-price-rows/')
        self.assertEqual(response.status_code, 200)
        rows = {row['tier_id']: row for row in response.data['results']}
        first, second = rows[self.tier.pk], rows[twin.pk]
        self.assertEqual(first['dimension_width_mm'], '100.00')
        self.assertEqual(first['dimension_length_mm'], '200.00')
        self.assertEqual(first['minimum_quantity'], 7)
        self.assertEqual(first['maximum_quantity'], 99)
        self.assertTrue(first['is_negotiable'])
        self.assertEqual(second['dimension_width_mm'], '120.00')
        self.assertEqual(second['dimension_length_mm'], '240.00')
        self.assertEqual(second['minimum_quantity'], 10)
        self.assertFalse(second['is_negotiable'])

    def test_write_failure_rolls_back_all_prices_and_audits(self):
        before = self.snapshot()
        original = PricingTier.save
        def fail_second(instance, *args, **kwargs):
            if instance.pk == self.tier2.pk:
                raise RuntimeError('Injected pricing failure')
            return original(instance, *args, **kwargs)
        with patch.object(PricingTier, 'save', fail_second):
            with self.assertRaises(RuntimeError):
                self.post([{'tier_id': self.tier.pk, 'price': '53000'},
                           {'tier_id': self.tier2.pk, 'price': '54000'}])
        self.assertEqual(self.snapshot(), before)
