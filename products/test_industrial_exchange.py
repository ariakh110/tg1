from datetime import date,timedelta
from unittest.mock import patch
from copy import deepcopy
from importlib import import_module
from django.apps import apps
from rest_framework.test import APITestCase
from products.models import CommodityExchangeTrade,MarketDataSyncState
from products.external_markets import classify_steel_product,sync_ime_market

class IndustrialExchangeTests(APITestCase):
 def row(self,pk,name,day,group,volume=1):
  return CommodityExchangeTrade.objects.create(source_report_id=pk,goods_name=name,symbol=f'SYM-{pk}',producer_name='فولاد كوير',product_group=group,trade_date=day,trade_date_jalali=day.isoformat(),traded_volume=volume,currency='ریال',unit='تن',raw={'original':'keep'})
 def test_normalized_industrial_classification_and_exclusions(self):
  cases=[('آهن‌اسفنجي','آهن اسفنجی'),('اسفنجی بریکت','آهن اسفنجی'),('Sponge Iron DRI','آهن اسفنجی'),('ورق آلومینیوم','آلومینیوم'),('کنسانتره مس','مس'),('شمش سرب و روی','سرب و روی'),('سیمان پرتلند','سیمان و کلینکر'),('فروسیلیس','فروآلیاژها'),('میلگرد A3','میلگرد')]
  for text,expected in cases:
   self.assertEqual(classify_steel_product({'GoodsName':text,'Talar':'تالار صنعتی و معدنی'}),expected,text)
  for name in ['پلی اتیلن','گندم','قیر','پسته']:
   self.assertIsNone(classify_steel_product({'GoodsName':name,'Talar':'تالار صنعتی'}),name)
  self.assertEqual(classify_steel_product({'GoodsName':'کالای صنعتی ناشناخته','Talar':'تالار صنعتی و معدنی'}),'سایر صنعتی و معدنی')
  self.assertIsNone(classify_steel_product({'GoodsName':'کالای ناشناخته','Talar':'تالار پتروشیمی'}))
 def test_sync_retains_nonferrous_and_sponge_and_preserves_raw(self):
  names=['آهن اسفنجی','شمش آلومینیوم','کاتد مس','سیمان','پلی اتیلن']
  raw=[{'xTalarReportPK':100+n,'GoodsName':name,'Symbol':f'RAW-{n}','Talar':'تالار صنعتی و معدنی','date':'2026/11/01','Quantity':'3','Price':'123','Unit':'تن'} for n,name in enumerate(names)]
  with patch('products.external_markets._post_json',return_value={'d':raw}):
   self.assertEqual(sync_ime_market('1405/08/10','1405/08/10'),4)
  self.assertEqual(CommodityExchangeTrade.objects.count(),4)
  self.assertEqual(CommodityExchangeTrade.objects.get(source_report_id=100).raw,raw[0])
  self.assertEqual(MarketDataSyncState.objects.get(key='ime').metadata['excluded_rows'],2)
 def test_empty_group_remains_discoverable_and_all_date_scope(self):
  today=date(2026,11,1);older=today-timedelta(days=3)
  self.row(1,'آهن اسفنجی',older,'آهن اسفنجی');self.row(2,'ورق سیاه',today,'ورق و کلاف')
  data=self.client.get('/api/commodity-exchange/summary/').data
  sponge=next(row for row in data['available_groups'] if row['name']=='آهن اسفنجی')
  self.assertEqual(sponge['latest_date'],older.isoformat());self.assertEqual(sponge['records'],0)
  all_data=self.client.get('/api/commodity-exchange/summary/?date=all').data
  self.assertEqual(all_data['records'],2);self.assertEqual(all_data['date_scope'],'all');self.assertIsNone(all_data['selected_date'])
 def test_normalized_search_status_and_invalid_dates(self):
  self.row(1,'آهن‌اسفنجي',date(2026,11,1),'آهن اسفنجی',1)
  self.row(2,'ورق',date(2026,11,1),'ورق و کلاف',0)
  self.row(3,'ورق روغنی',date(2026,11,1),'ورق و کلاف',None)
  for term in ['اسفنجی','آهن اسفنجی','کویر']:
   r=self.client.get('/api/commodity-exchange/trades/',{'search':term});self.assertEqual(r.status_code,200);self.assertGreater(r.data['count'],0,term)
  self.assertEqual(self.client.get('/api/commodity-exchange/trades/?trade_status=traded').data['count'],1)
  self.assertEqual(self.client.get('/api/commodity-exchange/trades/?trade_status=untraded').data['count'],2)
  for query in ['date_from=broken','date_to=2026-40-01','date_from=2026-11-02&date_to=2026-11-01','trade_status=wrong']:
   self.assertEqual(self.client.get('/api/commodity-exchange/trades/?'+query).status_code,400,query)
 def test_backfill_regroups_old_sponge_without_touching_official_values(self):
  row=self.row(10,'آهن‌اسفنجي بریکت',date(2026,10,10),'زنجیره سنگ‌آهن',12)
  original=(deepcopy(row.raw),row.traded_volume,row.trade_date,row.symbol)
  migrate=import_module('products.migrations.0025_separate_sponge_iron').regroup
  migrate(apps,None);migrate(apps,None);row.refresh_from_db()
  self.assertEqual(row.product_group,'آهن اسفنجی');self.assertEqual((row.raw,row.traded_volume,row.trade_date,row.symbol),original)
