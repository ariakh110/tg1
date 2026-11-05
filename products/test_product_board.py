from rest_framework.test import APITestCase
from products.models import Product, ProductCategory, ProductSpecification, SpecificationAttribute, SpecificationValue


class ProductBoardPayloadTests(APITestCase):
    def test_public_board_receives_stored_nominal_size_without_inventing_height(self):
        category = ProductCategory.objects.create(name='Board channel', code='board-channel', product_kind='channel')
        product = Product.objects.create(name='Channel nominal 6.5', category=category, slug='board-channel')
        ProductSpecification.objects.create(product=product, material_type='channel', length_mm=12000)
        attribute = SpecificationAttribute.objects.create(name='سایز اسمی ناودانی', unit='')
        SpecificationValue.objects.create(product=product, attribute=attribute, value='6.5')
        response = self.client.get('/api/products/', {'category': category.pk})
        self.assertEqual(response.status_code, 200)
        row = response.data['results'][0]
        self.assertIn('dynamic_specs', row)
        self.assertEqual(row['dynamic_specs'][0]['attribute']['name'], 'سایز اسمی ناودانی')
        self.assertEqual(row['dynamic_specs'][0]['value'], '6.5')
        self.assertIsNone(row['specification']['height_mm'])
