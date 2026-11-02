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
  for name in ['پلی اتیلن','گندم','قیر','پسته','polyethylene sheet','rice sheet']:
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

 def test_map_missing_producer_is_an_exact_filter(self):
  known=self.row(70,'ورق',date(2026,11,1),'ورق و کلاف');unknown=self.row(71,'ورق بدون نام',date(2026,11,1),'ورق و کلاف');unknown.producer_name='';unknown.save()
  result=self.client.get('/api/commodity-exchange/trades/',{'producer_name':'__unknown__'}).data
  self.assertEqual(result['count'],1);self.assertEqual(result['results'][0]['source_report_id'],71)

 def test_summary_producers_contract_is_a_list_for_populated_and_empty_scopes(self):
  self.row(90,'ورق',date(2026,11,1),'ورق و کلاف')
  for query in ['', '?date=all', '?date=2026-10-01']:
   data=self.client.get('/api/commodity-exchange/summary/'+query).data
   self.assertIsInstance(data['producers'],list)
   self.assertEqual(data['producers'],[] if '2026-10-01' in query else ['فولاد كوير'])
 def test_ambiguous_persian_words_keep_industrial_material_context(self):
  for name,expected in [('شمش برنج','مس'),('ورق برنجی','مس'),('میلگرد روی پالت','میلگرد'),('شمش روی','سرب و روی'),('ورق روی اندود','سرب و روی')]:
   self.assertEqual(classify_steel_product({'GoodsName':name,'Talar':'تالار صنعتی و معدنی'}),expected,name)
  for name in ['برنج','برنج طارم','ورق پلی اتیلن اسفنجی']:
   self.assertIsNone(classify_steel_product({'GoodsName':name,'Talar':'تالار صنعتی و معدنی'}),name)
 def test_sponge_backfill_rejects_explicit_nonindustrial_goods(self):
  row=self.row(91,'ورق پلی اتیلن اسفنجی',date(2026,10,1),'ورق و کلاف');row.hall='تالار پتروشیمی';row.save()
  import_module('products.migrations.0025_separate_sponge_iron').regroup(apps,None)
  row.refresh_from_db();self.assertEqual(row.product_group,'ورق و کلاف')
 def test_legacy_nonindustrial_rows_are_retained_but_hidden_in_every_public_scope(self):
  old=self.row(92,'ورق پلی اتیلن اسفنجی',date(2026,11,2),'ورق و کلاف');old.hall='تالار پتروشیمی';old.save()
  valid=self.row(93,'شمش فولاد',date(2026,11,1),'شمش و اسلب');valid.hall='تالار صنعتی و معدنی';valid.save()
  original=deepcopy(old.raw)
  migration=import_module('products.migrations.0026_commodity_industrial_scope')
  migration.classify_history(apps,None);migration.classify_history(apps,None)
  old.refresh_from_db();valid.refresh_from_db()
  self.assertFalse(old.is_industrial);self.assertEqual(old.raw,original);self.assertEqual(valid.product_group,'شمش و اسلب')
  self.assertEqual(CommodityExchangeTrade.objects.count(),2)
  for query in ['', '?date=all']:
   data=self.client.get('/api/commodity-exchange/summary/'+query).data
   self.assertEqual(data['records'],1);self.assertEqual(data['latest_trade_date'],'2026-11-01')
   self.assertEqual([x['date'] for x in data['available_dates']],['2026-11-01'])
  data=self.client.get('/api/commodity-exchange/trades/').data
  self.assertEqual(data['count'],1);self.assertEqual(data['results'][0]['source_report_id'],93)
  data=self.client.get('/api/commodity-exchange/symbols/'+old.symbol+'/history/').data
  self.assertEqual(data.get('points',[]),[])
