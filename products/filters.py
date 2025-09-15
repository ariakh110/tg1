from django_filters import rest_framework as filters
from .models import Product, Offer

class ProductFilter(filters.FilterSet):
    # filter on category id and active
    category = filters.NumberFilter(field_name='category', lookup_expr='exact')
    is_active = filters.BooleanFilter(field_name='is_active')

    # filters on specifications (related one-to-one)
    steel_grade = filters.CharFilter(field_name='specifications__steel_grade', lookup_expr='iexact')
    min_thickness = filters.NumberFilter(field_name='specifications__thickness_mm', lookup_expr='gte')
    max_thickness = filters.NumberFilter(field_name='specifications__thickness_mm', lookup_expr='lte')

    class Meta:
        model = Product
        fields = ['category', 'is_active', 'steel_grade', 'min_thickness', 'max_thickness']


class OfferFilter(filters.FilterSet):
    product = filters.NumberFilter(field_name='product', lookup_expr='exact')
    seller = filters.NumberFilter(field_name='seller', lookup_expr='exact')
    is_active = filters.BooleanFilter(field_name='is_active')

    # price-range (checks pricing_tiers related field; matches offers that have at least one tier in range)
    min_price = filters.NumberFilter(field_name='pricing_tiers__unit_price', lookup_expr='gte')
    max_price = filters.NumberFilter(field_name='pricing_tiers__unit_price', lookup_expr='lte')

    class Meta:
        model = Offer
        fields = ['product', 'seller', 'is_active', 'min_price', 'max_price']