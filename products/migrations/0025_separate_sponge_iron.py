"""Frozen, one-time regroup only: do not alter official values or raw payloads."""
import re
from django.db import migrations


def regroup(apps,schema_editor):
    Trade=apps.get_model('products','CommodityExchangeTrade')
    for row in Trade.objects.only('id','goods_name','symbol','product_group','hall').iterator(chunk_size=500):
        name=(row.goods_name+' '+row.symbol).translate(str.maketrans({'ي':'ی','ك':'ک','\u200c':' ','_':' ','-':' '})).casefold()
        context=(row.goods_name+' '+row.hall).translate(str.maketrans({'ي':'ی','ك':'ک','\u200c':' '})).casefold()
        denied = re.search(r'پلی[\s-]*(?:اتیلن|پروپیلن)|پتروشیمی|پلیمر|کشاورزی|polyethylene|polypropylene|polymer|petrochem|agricultur', context)
        if not denied and re.search(r'اسفنجی|(?<!\w)(?:sponge iron|dri|hbi)(?!\w)',name) and row.product_group!='آهن اسفنجی':
            Trade.objects.filter(pk=row.pk).update(product_group='آهن اسفنجی')


class Migration(migrations.Migration):
    dependencies=[('products','0024_marketdatasyncstate_last_success_at_and_more')]
    operations=[migrations.RunPython(regroup,migrations.RunPython.noop)]
