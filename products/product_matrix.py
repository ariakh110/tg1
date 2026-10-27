"""Read-only preview and atomic, create-only sheet/coil matrices."""
from decimal import Decimal, InvalidOperation
import re

from django.db import transaction
from django.db.models import Q, CharField
from rest_framework.exceptions import ValidationError

from .admin_import import SPEC_FIELDS, build_product_name, upsert_product_row
from .models import Product, ProductCategory, ProductSpecification, ProductAuditLog, Seller, PricingBasis, DeliveryLocation
from .serializers import ProductSpecificationSerializer

MAX_ROWS = 100
COMMON_FIELDS = {'category_code','seller_id','manufacturing_process','surface_finish','steel_grade','factory',
                 'cut_type','price_basis','province','city','address','naming_mode'}
ROW_FIELDS = {'key','thickness_mm','width_mm','length_mm','length_type','price','availability_status','name'}
DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩','01234567890123456789')


class MatrixError(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__('Invalid product matrix')


def number(value, field, *, digits=10, optional=False):
    if optional and value in ('',None):
        return None
    text = str(value).translate(DIGITS).replace('٫','.').replace('٬',',').strip()
    if not re.fullmatch(r'(?:\d+|[1-9]\d{0,2}(?:,\d{3})+)(?:\.\d{1,2})?',text):
        raise ValueError(f'{field}: عدد مثبت با حداکثر دو رقم اعشار وارد کنید.')
    text=text.replace(',','')
    try:
        result=Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f'{field}: عدد نامعتبر است.') from exc
    if not result.is_finite() or result <= 0 or result >= Decimal(10) ** (digits-2):
        raise ValueError(f'{field}: عدد خارج از محدوده است.')
    return result


def _existing(category, spec):
    candidates=Product.objects.filter(category=category)
    for field in sorted(SPEC_FIELDS):
        value=spec[field]
        lookup='specifications__'+field
        if value in ('',None) and isinstance(ProductSpecification._meta.get_field(field), CharField):
            candidates=candidates.filter(Q(**{lookup:''}) | Q(**{lookup+'__isnull':True}))
        elif isinstance(value,str):
            candidates=candidates.filter(**{lookup+'__iexact':value})
        else:
            candidates=candidates.filter(**{lookup:value})
    matches=list(candidates.order_by('id')[:2])
    if len(matches)>1:
        raise ValueError('چند محصول با مشخصات یکسان وجود دارد؛ ابتدا موارد تکراری را بررسی کنید.')
    return matches[0] if matches else None


def _prepare(data, *, lock=False):
    if not isinstance(data,dict) or set(data)-{'common','rows'}:
        raise MatrixError({'detail':'ساختار درخواست ماتریس معتبر نیست.'})
    common,rows=data.get('common'),data.get('rows')
    if not isinstance(common,dict) or set(common)-COMMON_FIELDS:
        raise MatrixError({'detail':'فیلد مشترک ناشناخته یا نامعتبر است.'})
    if not isinstance(rows,list) or not 1<=len(rows)<=MAX_ROWS:
        raise MatrixError({'detail':'بین ۱ تا ۱۰۰ ردیف انتخاب کنید.'})
    if any(not isinstance(value,(str,int)) or isinstance(value,bool) for value in common.values()):
        raise MatrixError({'detail':'مقادیر مشترک باید متن یا شناسه معتبر باشند.'})
    common={key:str(value).strip() for key,value in common.items()}
    naming_mode=common.pop('naming_mode','auto')
    if naming_mode not in ('auto','manual'):
        raise MatrixError({'detail':'روش نام‌گذاری باید خودکار یا دستی باشد.'})
    for field in ('province','city','address'):
        limit=DeliveryLocation._meta.get_field(field).max_length
        if len(common.get(field,''))>limit:
            label={'province':'استان','city':'شهر','address':'آدرس'}[field]
            raise MatrixError({'detail':f'{label} تحویل حداکثر {limit} نویسه باشد.'})
    if len(common.get('seller_id',''))>20 or len(common.get('category_code',''))>100:
        raise MatrixError({'detail':'شناسه فروشنده یا دسته بیش از حد طولانی است.'})
    categories=ProductCategory.objects.select_for_update() if lock else ProductCategory.objects
    category=categories.filter(code=common.get('category_code'),is_active=True).first()
    if not category or category.resolved_product_kind()!='sheet':
        raise MatrixError({'detail':'یک دسته فعال ورق یا رول انتخاب کنید.'})
    basis=common.get('price_basis','kg')
    if basis not in PricingBasis.values:
        raise MatrixError({'detail':'مبنای قیمت معتبر نیست.'})
    seller_id=common.get('seller_id')
    if seller_id and (not seller_id.isascii() or not seller_id.isdigit() or not Seller.objects.filter(pk=seller_id).exists()):
        raise MatrixError({'detail':'فروشنده معتبر نیست.'})
    common['price_basis']=basis
    result=[]; prepared=[]; seen=set(); keys=set()
    for index,entry in enumerate(rows):
        key=entry.get('key') if isinstance(entry,dict) else None
        item={'key':key if isinstance(key,str) else str(index),'status':'error'}
        try:
            if not isinstance(entry,dict) or set(entry)-ROW_FIELDS:
                raise ValueError('فیلد ردیف ناشناخته یا نامعتبر است.')
            if not isinstance(key,str) or not key.strip() or len(key)>160 or key in keys:
                raise ValueError('شناسه ردیف خالی یا تکراری است.')
            keys.add(key)
            spec_input={field:common[field] for field in SPEC_FIELDS if field in common}
            spec_input.update(thickness_mm=number(entry.get('thickness_mm'),'ضخامت'),width_mm=number(entry.get('width_mm'),'عرض'))
            process=spec_input.get('manufacturing_process') or category.merged_spec_defaults().get('manufacturing_process')
            length_type=entry.get('length_type','fixed')
            if length_type not in ('fixed','over'):
                raise ValueError('نوع طول معتبر نیست.')
            if process=='coil':
                if length_type!='fixed' or entry.get('length_mm') not in ('',None):
                    raise ValueError('برای رول طول ثابت یا متغیر وارد نکنید.')
                spec_input.update(length_mm=None,length_type='fixed',cut_type='')
            else:
                spec_input.update(length_mm=number(entry.get('length_mm'),'طول'),length_type=length_type)
            instance=ProductSpecification(product=Product(category=category))
            serializer=ProductSpecificationSerializer(instance,data=spec_input,partial=True)
            serializer.is_valid(raise_exception=True)
            spec={field:serializer.validated_data.get(field,getattr(instance,field)) for field in SPEC_FIELDS}
            identity=tuple(str(spec[field] or '').casefold() for field in sorted(SPEC_FIELDS))
            if identity in seen:
                raise ValueError('این ترکیب ابعاد در ماتریس تکراری است.')
            seen.add(identity)
            price=number(entry.get('price'),'قیمت',digits=12,optional=True)
            availability=entry.get('availability_status','in_stock')
            if not isinstance(availability,str) or availability not in dict(Product.AVAILABILITY_CHOICES):
                raise ValueError('وضعیت موجودی معتبر نیست.')
            if price is None and availability!='out_of_stock':
                availability='inquiry'
            if (price is not None or any(common.get(field) for field in ('province','city','address'))) and not seller_id:
                raise ValueError('برای قیمت یا محل تحویل، فروشنده انتخاب کنید.')
            row={**common,**spec,'availability_status':availability}
            if price is not None:
                row['price']=price
            if naming_mode=='manual':
                name=entry.get('name')
                if not isinstance(name,str) or not name.strip():
                    raise ValueError('نام محصول را در حالت دستی وارد کنید.')
                name=name.strip()
            else:
                name=build_product_name(row,category)
                if spec.get('steel_grade'):
                    name+=' '+spec['steel_grade']
            if len(name)>Product._meta.get_field('name').max_length:
                raise ValueError('نام محصول حداکثر ۲۵۵ نویسه باشد.')
            row['name']=name
            existing=_existing(category,spec)
            item.update(name=existing.name if existing else row['name'],status='exists' if existing else 'new')
            if existing:
                item['product_id']=existing.pk
            prepared.append((item,row))
        except (ValueError,ValidationError) as exc:
            item['errors']=exc.detail if isinstance(exc,ValidationError) else str(exc)
        result.append(item)
    report={'valid':all(item['status']!='error' for item in result),'rows':result,
            'new_count':sum(item['status']=='new' for item in result),'existing_count':sum(item['status']=='exists' for item in result)}
    return report,prepared


def preview_product_matrix(data):
    report,_=_prepare(data)
    return report


def create_product_matrix(data, actor):
    with transaction.atomic():
        report,prepared=_prepare(data,lock=True)
        if not report['valid']:
            raise MatrixError(report)
        created=0
        for item,row in prepared:
            if item['status']=='exists':
                continue
            outcome=upsert_product_row(row,create_missing=True,force_create=True)
            item.update(status='created',product_id=outcome['product_id'])
            ProductAuditLog.objects.create(product_id=outcome['product_id'],product_name=outcome['product_name'],
                                           action='PRODUCT_MATRIX_CREATED',actor_user=actor,
                                           payload={'source':'admin_matrix','row_key':item['key']})
            created+=1
        report['created_count']=created
        return report
