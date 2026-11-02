"""Industrial physical-goods taxonomy; official names/raw values stay unchanged."""
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
    'تیرآهن و مقاطع': ('لوله','پروفیل','tube','pipe','تیرآهن','تیر آهن','نبشی','ناودانی','مفتول','ریل','beam','angle','channel','wire'),
    'زنجیره سنگ‌آهن': ('سنگ آهن','سنگ‌آهن','گندله','کنسانتره','pellet','iron ore'),
    'قراضه و فولاد': ('چدن','cast iron','قراضه','فولاد','آهن','steel','scrap'),
    'سیمان و کلینکر': ('سیمان','سیمانی','بتن','بتنی','کلینکر','cement','clinker'),
    'شیشه': ('شیشه','glass'),
    'کاشی و سرامیک': ('کاشی','سرامیک','سرامیکی'),
    'مواد معدنی': ('سنگ آهک','آهک','دولومیت','کک','زغال','زغالسنگ','سیلیس','بوکسیت','کائولن','خاک نسوز','باریت'),
    'سایر صنعتی و معدنی': (),
}
NON_INDUSTRIAL = ('پلی اتیلن','پلی‌اتیلن','پلی پروپیلن','پلیمر','پتروشیمی','قیر','نفت','گاز','بنزین','لوبکات','وکیوم','گندم','جو','ذرت','زعفران','پسته','خرما','شکر','شیر','PVC','پی وی سی','پلاستیک','پلاستیکی','polyethylene','polypropylene','polymer','petrochemical','bitumen','petroleum','wheat','rice','corn')


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
    # Explicit material in the goods name outranks shape and ticker codes.
    searchable = goods
    # روی is also a preposition; packaging is not evidence of zinc.
    searchable = re.sub(r'(?<!\w)روی\s+(?:پالت|بندیل|کامیون|تریلر|واگن|سکو|زمین)(?!\w)', ' ', searchable)
    material_groups = ('آلومینیوم','مس','سرب و روی','نیکل و قلع','فلزات گران‌بها','سیمان و کلینکر','شیشه','کاشی و سرامیک')
    for group in material_groups:
        if contains(searchable, INDUSTRIAL_GROUPS[group]):
            return group
    ambiguous_shape = contains(searchable, ('لوله','پروفیل','pipe','tube')) and not contains(searchable, ('فولاد','فولادی','آهن','آهنی','steel'))
    if ambiguous_shape:
        return 'سایر صنعتی و معدنی' if ('صنعتی' in hall or 'معدنی' in hall) else None
    for group, words in INDUSTRIAL_GROUPS.items():
        if contains(searchable, words):
            return group
    if 'صنعتی' in hall or 'معدنی' in hall:
        return 'سایر صنعتی و معدنی'
    return None
