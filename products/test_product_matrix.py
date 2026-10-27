from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Product, ProductSpecification, Seller, Offer, PricingTier, ProductAuditLog


class ProductMatrixTests(APITestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user('matrix-admin', is_staff=True)
        self.client.force_authenticate(self.admin)
        self.seller = Seller.objects.create(user=self.admin, company_name='Matrix', business_type='Trading', location='Test')
        self.common = dict(category_code='sheet', seller_id=self.seller.pk, manufacturing_process='sheet',
                           surface_finish='black', factory='kavian', steel_grade='ST37', cut_type='cut', price_basis='kg')
        self.rows = [dict(key='short', thickness_mm='30', width_mm='1500', length_mm='6000', length_type='fixed', price='50000', availability_status='in_stock'),
                     dict(key='long', thickness_mm='30', width_mm='1500', length_mm='7000', length_type='over', price='55000', availability_status='out_of_stock')]

    def request(self, action='preview', rows=None, common=None):
        return self.client.post('/api/products/admin-matrix-'+action+'/', {'common':common or self.common,'rows':rows if rows is not None else self.rows}, format='json')

    def counts(self):
        return [model.objects.count() for model in (Product,ProductSpecification,Seller,Offer,PricingTier,ProductAuditLog)]

    def test_manual_names_and_auto_grade_do_not_change_identity(self):
        automatic=self.request(rows=[self.rows[0]])
        self.assertIn('ST37',automatic.data['rows'][0]['name'])
        manual={**self.common,'naming_mode':'manual'}
        rows=[{**self.rows[0],'name':'  ورق سفارشی کاویان ۳۰ میل  '}]
        response=self.request('create',rows=rows,common=manual)
        self.assertEqual(response.status_code,200,response.data)
        product=Product.objects.get(pk=response.data['rows'][0]['product_id'])
        self.assertEqual(product.name,'ورق سفارشی کاویان ۳۰ میل')
        repeated=self.request('create',rows=[{**rows[0],'name':'Changed'}],common=manual)
        self.assertEqual(repeated.data['created_count'],0)
        product.refresh_from_db(); self.assertEqual(product.name,'ورق سفارشی کاویان ۳۰ میل')

    def test_invalid_manual_names_reject_all_rows(self):
        for name in ['', '   ', 'x'*256, None, 123, ['name']]:
            with self.subTest(name=name):
                before=self.counts()
                response=self.request('create',common={**self.common,'naming_mode':'manual'},
                    rows=[{**self.rows[0],'name':'Valid'},{**self.rows[1],'name':name}])
                self.assertEqual(response.status_code,400,response.data)
                self.assertEqual(self.counts(),before)
        self.assertEqual(self.request(common={**self.common,'naming_mode':'unknown'}).status_code,400)

    def test_oxin_st52_8_through_80_create_and_repeat(self):
        common={**self.common,'surface_finish':'alloy','steel_grade':'ST52','factory':'oxin'}
        rows=[{**self.rows[0],'key':str(t),'thickness_mm':str(t)} for t in range(8,81)]
        preview=self.request(rows=rows,common=common)
        self.assertEqual(preview.status_code,200,preview.data)
        self.assertTrue(preview.data['valid'],preview.data)
        self.assertEqual(preview.data['new_count'],73)
        self.assertIn('ST52',preview.data['rows'][0]['name'])
        response=self.request('create',rows=rows,common=common)
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['created_count'],73)
        self.assertEqual(Product.objects.filter(specifications__factory='oxin',specifications__steel_grade='ST52').count(),73)
        repeated=self.request('create',rows=rows,common=common)
        self.assertEqual(repeated.data['created_count'],0)
        self.assertEqual(repeated.data['existing_count'],73)

    def test_oxin_st52_user_dimensions_two_fixed_lengths(self):
        thicknesses=[8,10,12,15,20,25,30,35,40,45,50,55,60,65,70,75,80]
        common={**self.common,'surface_finish':'alloy','steel_grade':'ST52','factory':'oxin'}
        rows=[{**self.rows[0],'key':f'{t}-{length}','thickness_mm':str(t),
               'width_mm':'2000','length_mm':str(length)} for t in thicknesses for length in (6000,12000)]
        response=self.request('create',rows=rows,common=common)
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['created_count'],34)
        self.assertEqual(ProductSpecification.objects.filter(width_mm=2000,length_mm=12000,steel_grade='ST52').count(),17)

    def test_preview_is_read_only_and_reports_two_length_variants(self):
        before=self.counts()
        response=self.request()
        self.assertEqual(response.status_code,200,response.data)
        self.assertTrue(response.data['valid'])
        self.assertEqual(response.data['new_count'],2)
        self.assertEqual(self.counts(),before)

    def test_create_keeps_independent_prices_and_public_length_semantics(self):
        response=self.request('create')
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['created_count'],2)
        ids=[row['product_id'] for row in response.data['rows']]
        self.assertEqual(len(set(ids)),2)
        for pid, row in zip(ids,self.rows):
            product=Product.objects.get(pk=pid)
            self.assertEqual(product.specifications.length_type,row['length_type'])
            self.assertEqual(product.availability_status,row['availability_status'])
            self.assertEqual(PricingTier.objects.get(offer__product=product).unit_price,Decimal(row['price']))
            public=self.client.get(f'/api/products/{pid}/')
            self.assertEqual(public.data['specification']['length_type'],row['length_type'])
        self.assertEqual(ProductAuditLog.objects.filter(action='PRODUCT_MATRIX_CREATED').count(),2)

    def test_repeat_and_existing_custom_name_never_overwrite(self):
        first=self.request('create'); self.assertEqual(first.status_code,200,first.data)
        pid=first.data['rows'][0]['product_id']
        Product.objects.filter(pk=pid).update(name='Custom display name',is_active=False)
        before=self.counts()
        altered=[{**row,'price':'99999','availability_status':'inquiry'} for row in self.rows]
        response=self.request('create',rows=altered)
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['created_count'],0)
        self.assertEqual(response.data['existing_count'],2)
        self.assertEqual(self.counts(),before)
        self.assertEqual(PricingTier.objects.get(offer__product_id=pid).unit_price,Decimal('50000'))
        self.assertFalse(Product.objects.get(pk=pid).is_active)
        self.assertEqual(Product.objects.get(pk=pid).availability_status,'in_stock')

    def test_invalid_later_row_has_no_partial_writes(self):
        before=self.counts()
        response=self.request('create',rows=[self.rows[0],{**self.rows[1],'length_mm':'-7'}])
        self.assertEqual(response.status_code,400,response.data)
        self.assertFalse(response.data['valid'])
        self.assertEqual(response.data['rows'][1]['status'],'error')
        self.assertEqual(self.counts(),before)

    def test_late_exception_rolls_back_all_domain_and_audit_rows(self):
        from .admin_import import upsert_product_row
        calls=0
        def fail_second(*args,**kwargs):
            nonlocal calls
            calls+=1
            if calls==2: raise RuntimeError('private test error')
            return upsert_product_row(*args,**kwargs)
        before=self.counts()
        with patch('products.product_matrix.upsert_product_row',side_effect=fail_second):
            response=self.request('create')
        self.assertEqual(response.status_code,400)
        self.assertNotIn('private test error',str(response.data))
        self.assertEqual(self.counts(),before)

    def test_malformed_numeric_duplicate_and_unknown_fields_rejected(self):
        for change in [{'price':'NaN'},{'width_mm':'Infinity'},{'thickness_mm':'0'}, {'length_mm':'6000.123'},
                       {'product_id':1},{'availability_status':'invented'},{'price':'10000000000'}]:
            with self.subTest(change=change):
                before=self.counts()
                response=self.request('create',rows=[{**self.rows[0],**change}])
                self.assertEqual(response.status_code,400,response.data)
                self.assertEqual(self.counts(),before)
        self.assertEqual(self.request('create',rows=[self.rows[0],{**self.rows[0],'key':'another'}]).status_code,400)
        self.assertEqual(self.request('create',rows=[{**self.rows[0],'key':str(i)} for i in range(101)]).status_code,400)
        self.assertEqual(self.request('create',rows=[]).status_code,400)
        self.assertEqual(self.request('create',common={**self.common,'product_id':1}).status_code,400)

    def test_blank_price_is_inquiry_and_fixed_and_over_same_threshold_differ(self):
        response=self.request('create',rows=[{**self.rows[0],'price':'','length_mm':'7000'},self.rows[1]])
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data['created_count'],2)
        product=Product.objects.get(pk=response.data['rows'][0]['product_id'])
        self.assertEqual(product.availability_status,'inquiry')
        self.assertFalse(PricingTier.objects.filter(offer__product=product).exists())

    def test_unprivileged_and_anonymous_are_denied(self):
        outsider=get_user_model().objects.create_user('matrix-outsider')
        self.client.force_authenticate(outsider)
        self.assertEqual(self.request().status_code,403)
        self.assertEqual(self.request('create').status_code,403)
        self.client.force_authenticate(None)
        self.assertIn(self.request().status_code,[401,403])

    def test_delivery_lengths_are_validated_before_preview_and_commit(self):
        for field,size in [('address',256),('province',101),('city',101)]:
            with self.subTest(field=field):
                before=self.counts()
                common={**self.common,field:'x'*size}
                self.assertEqual(self.request(common=common).status_code,400)
                self.assertEqual(self.request('create',common=common).status_code,400)
                self.assertEqual(self.counts(),before)

    def test_malformed_grouping_in_price_is_not_silently_removed(self):
        for value in ['1,2','50,,000',',50000','50,000,']:
            with self.subTest(value=value):
                response=self.request(rows=[{**self.rows[0],'price':value}])
                self.assertFalse(response.data['valid'],response.data)
        response=self.request('create',rows=[{**self.rows[0],'price':'۵۰٬۰۰۰'}])
        self.assertEqual(response.status_code,200,response.data)

    def test_coil_and_role_section_rules(self):
        from accounts.models import RoleCode,UserRole
        common={**self.common,'manufacturing_process':'coil','cut_type':''}
        response=self.request('create',common=common,rows=[{**self.rows[0],'length_mm':'','length_type':'fixed'}])
        self.assertEqual(response.status_code,200,response.data)
        product=Product.objects.get(pk=response.data['rows'][0]['product_id'])
        self.assertIsNone(product.specifications.length_mm)
        marketer=get_user_model().objects.create_user('matrix-marketer')
        UserRole.objects.create(user=marketer,role=RoleCode.MARKETER,is_active=True)
        self.client.force_authenticate(marketer)
        self.assertEqual(self.request().status_code,403)
        self.assertEqual(self.request('create').status_code,403)
