"""Public iron/steel chain scope; retaining broader private history is intentional."""
from .commodity_categories import classify_industrial_product

STEEL_GROUPS = ('آهن اسفنجی', 'زنجیره سنگ‌آهن', 'شمش و اسلب', 'ورق و کلاف',
                'میلگرد', 'تیرآهن و مقاطع', 'قراضه و فولاد', 'فروآلیاژها')


def steel_trades():
    from .models import CommodityExchangeTrade
    return CommodityExchangeTrade.objects.filter(is_industrial=True, product_group__in=STEEL_GROUPS)


def classify_steel_chain(name, symbol=''):
    group = classify_industrial_product({'GoodsName': name, 'Symbol': symbol})
    if group in STEEL_GROUPS:
        return group
    return None
