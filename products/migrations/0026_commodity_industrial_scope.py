"""Frozen historical industrial classification, version 2026-11-01. Never import live taxonomy here."""
import re

TRANSLATION = str.maketrans('يك۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩','یک01234567890123456789')


def normalize_commodity_text(value):
    return re.sub(r'\s+', ' ', re.sub(r'[\u200c-\u200f\ufeff]', ' ', str(value or '').translate(TRANSLATION))).strip().casefold()


INDUSTRIAL_GROUPS = {
    'آهن اسفنجی': ('اسفنجی','sponge iron','dri','hbi'),
    'آلومینیوم': ('آلومینیوم','آلومینیم','آلومینا','aluminum','aluminium'),
    'مس': ('مس','مسی','copper','برنج','برنجی','brass'),
    'سرب و روی': ('سرب','روی','zinc','lead'),
    'نیکل و قلع': ('نیکل','قلع','nickel','tin'),
    'فلزات گران‌بها': ('طلا','نقره','پلاتین','gold','silver','platinum'),
    'فروآلیاژها': ('فروسیلیس','فرو سیلیس','فرومنگنز','فرو منگنز','فروکروم','فرو کروم','فروآلیاژ','ferroalloy'),
    'میلگرد': ('میلگرد','rebar'),
    'ورق و کلاف': ('ورق','کلاف','coil','sheet','hrc','crc'),
    'شمش و اسلب': ('شمش','بلوم','بیلت','اسلب','billet','bloom','slab'),
    'تیرآهن و مقاطع': ('تیرآهن','تیر آهن','نبشی','ناودانی','مفتول','ریل','beam','angle','channel','wire'),
    'زنجیره سنگ‌آهن': ('سنگ آهن','سنگ‌آهن','گندله','کنسانتره','pellet','iron ore'),
    'قراضه و فولاد': ('قراضه','فولاد','آهن','steel','scrap'),
    'سیمان و کلینکر': ('سیمان','کلینکر','cement','clinker'),
    'شیشه': ('شیشه','glass'),
    'کاشی و سرامیک': ('کاشی','سرامیک','سرامیکی'),
    'مواد معدنی': ('سنگ آهک','آهک','دولومیت','کک','زغال','زغالسنگ','سیلیس','بوکسیت','کائولن','خاک نسوز','باریت'),
    'سایر صنعتی و معدنی': (),
}
NON_INDUSTRIAL = ('پلی اتیلن','پلی‌اتیلن','پلی پروپیلن','پلیمر','پتروشیمی','قیر','نفت','گاز','بنزین','لوبکات','وکیوم','گندم','جو','ذرت','زعفران','پسته','خرما','شکر','شیر','polyethylene','polypropylene','polymer','petrochemical','bitumen','petroleum','wheat','rice','corn')


def contains(text, words):
    return any(re.search(r'(?<!\w)'+re.escape(normalize_commodity_text(word))+r'(?!\w)', text) for word in words)


def classify_industrial_product(row):
    goods = normalize_commodity_text(row.get('GoodsName'))
    hall = normalize_commodity_text(' '.join(str(row.get(key) or '') for key in ('Talar','PacketName','MainCatName','CategoryName')))
    brass_shape = contains(goods, ('شمش','ورق','تسمه','مفتول','میله','لوله','billet','sheet','brass'))
    if contains(goods, ('برنج',)) and not brass_shape:
        return None
    if contains(goods, NON_INDUSTRIAL) or contains(hall, ('پتروشیمی','کشاورزی','فرآورده های نفتی','فرآورده‌های نفتی','petrochemical','petrochemicals','agriculture','agricultural','petroleum')):
        return None
    searchable = goods+' '+normalize_commodity_text(row.get('Symbol')).replace('_',' ').replace('-',' ')
    # روی is also a preposition; packaging is not evidence of zinc.
    searchable = re.sub(r'(?<!\w)روی\s+(?:پالت|بندیل|کامیون|تریلر|واگن|سکو|زمین)(?!\w)', ' ', searchable)
    for group, words in INDUSTRIAL_GROUPS.items():
        if contains(searchable, words):
            return group
    if 'صنعتی' in hall or 'معدنی' in hall:
        return 'سایر صنعتی و معدنی'
    return None


from django.db import migrations, models


def classify_history(apps, schema_editor):
    Trade = apps.get_model('products', 'CommodityExchangeTrade')
    alias = schema_editor.connection.alias if schema_editor else 'default'
    manager = Trade.objects.using(alias)
    pending = []
    for row in manager.all().iterator(chunk_size=500):
        raw = row.raw if isinstance(row.raw, dict) else {}
        group = classify_industrial_product({**raw, 'GoodsName': row.goods_name,
            'Symbol': row.symbol, 'Talar': row.hall or raw.get('Talar', '')})
        row.is_industrial = bool(group)
        if group:
            row.product_group = group
        pending.append(row)
        if len(pending) == 500:
            manager.bulk_update(pending, ['is_industrial', 'product_group'], batch_size=500)
            pending = []
    if pending:
        manager.bulk_update(pending, ['is_industrial', 'product_group'], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [('products', '0025_separate_sponge_iron')]
    operations = [
        migrations.AddField(model_name='commodityexchangetrade', name='is_industrial',
                            field=models.BooleanField(default=True, db_index=True)),
        migrations.RunPython(classify_history, migrations.RunPython.noop),
    ]
