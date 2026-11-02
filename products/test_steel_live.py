from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from rest_framework.test import APITestCase
from products.models import CommodityExchangeTrade, MarketDataSyncState

class SteelScopeTests(APITestCase):
 def test_every_public_projection_excludes_nonsteel_history(self):
  day=timezone.localdate()
  for n,name,group in [(1,'شمش فولاد','شمش و اسلب'),(2,'سیمان','سیمان و کلینکر'),(3,'کاتد مس','مس')]:
   CommodityExchangeTrade.objects.create(source_report_id=n,symbol=f'X{n}',goods_name=name,product_group=group,trade_date=day,trade_date_jalali='1405/08/11',traded_volume=1)
  for query in ['', '?date=all']:
   d=self.client.get('/api/commodity-exchange/summary/'+query).data
   self.assertEqual(d['records'],1);self.assertEqual(d['market_scope'],'steel_chain')
   self.assertNotIn('سیمان و کلینکر',[g['name'] for g in d['available_groups']])
  self.assertEqual(self.client.get('/api/commodity-exchange/trades/').data['count'],1)
  self.assertEqual(self.client.get('/api/commodity-exchange/trades/?search=سیمان').data['count'],0)
  self.assertEqual(self.client.get('/api/commodity-exchange/symbols/X2/history/').data['points'],[])
 def test_steel_input_materials_and_sections(self):
  from products.steel_scope import classify_steel_chain
  for name in ['آهن اسفنجی','گندله سنگ آهن','شمش فولادی','ورق گرم','میلگرد','پروفیل فولادی','چدن','فروسیلیس']:
   self.assertIsNotNone(classify_steel_chain(name),name)
  for name in ['سیمان','ورق آلومینیوم','شمش برنج','مس مفتول','کاغذ','ورق پلی اتیلن','لوله پلی اتیلن','پروفیل آلومینیوم','لوله سیمانی','لوله PVC','لوله شیشه']:
   self.assertIsNone(classify_steel_chain(name),name)

 def test_snapshot_validation_filters_nonsteel_preserves_original_values(self):
  from products.ime_live import parse_snapshot
  rows=[self.offer(1),self.offer(2,'سیمان'),self.offer(3,'کاتد مس'),self.offer(4,'آهن اسفنجی')]
  rows[3]['QtySell']=0;rows[3]['TotalBuyQty']=None
  result=parse_snapshot([{'MarketId':1,'MarketName':'صنعتی و معدنی','StartTime':'13:30:00','FinishTime':'15:00:00'}],rows)
  self.assertEqual(len(result['rows']),2);self.assertIsNone(result['session_date'])
  self.assertEqual(result['rows'][0]['seller_price'],'744247.0');self.assertEqual(result['rows'][0]['unit'],'1000 کیلوگرم')
  self.assertEqual(result['rows'][1]['offered_volume'],'0');self.assertIsNone(result['rows'][1]['demand_volume'])
  for bad in [[self.offer(1),self.offer(1)], [{'MarketId':2}], [{'InstrumentId':1}], 'not a list']:
   with self.assertRaises(Exception):parse_snapshot([{'MarketId':1}],bad)
  bad=self.offer(10);bad['CurrentSellPrice']='NaN'
  with self.assertRaises(Exception):parse_snapshot([{'MarketId':1}],[bad])
 def offer(self,n,name='شمش فولاد'):
  return {'InstrumentId':n,'MarketId':1,'InstrumentName':name,'InstrumentSymbol':f'S-{n}','Producer':'کارخانه','Supplier':'عرضه‌کننده','QtySell':10,'TotalBuyQty':20,'CurrentSellPrice':744247.0,'Unit':'1000 کیلوگرم','Currency':'ریال','TradeStatusDesc':'Matched','IsDeleted':False,'Activate':False}
 def test_snapshot_failure_keeps_previous_and_valid_empty_clears_it(self):
  from products.ime_live import sync_ime_live,live_snapshot
  with patch('products.ime_live._get_json',side_effect=[[{'MarketId':1}],[self.offer(1)]]):sync_ime_live()
  previous=live_snapshot()['fetched_at']
  with patch('products.ime_live._get_json',side_effect=ValueError('private detail')):
   with self.assertRaises(Exception):sync_ime_live()
  result=live_snapshot();self.assertEqual(result['count'],1);self.assertEqual(result['fetched_at'],previous);self.assertTrue(result['stale']);self.assertNotIn('private detail',str(result))
  from products.external_markets import _sync_state_start
  _sync_state_start('ime_live')
  self.assertTrue(live_snapshot()['stale']);self.assertTrue(live_snapshot()['error'])
  with patch('products.ime_live._get_json',side_effect=[[{'MarketId':1}],[]]):sync_ime_live()
  self.assertEqual(live_snapshot()['rows'],[]);self.assertTrue(live_snapshot()['has_snapshot'])
  self.assertFalse(CommodityExchangeTrade.objects.exists())
 def test_public_snapshot_is_database_only_and_background_lease_respects_toggle(self):
  from products import tasks
  from core.models import SiteSettings
  with patch('products.ime_live._get_json') as network:
   response=self.client.get('/api/commodity-exchange/live/');self.assertEqual(response.status_code,200);self.assertFalse(response.data['has_snapshot']);network.assert_not_called()
  config=SiteSettings.load();config.ime_auto_refresh=False;config.save()
  with patch('products.tasks.sync_ime_live',return_value=2) as sync:
   tasks.refresh_market('ime_live');sync.assert_not_called()
   config.ime_auto_refresh=True;config.save()
   tasks.refresh_market('ime_live');tasks.refresh_market('ime_live');sync.assert_called_once()
   state=MarketDataSyncState.objects.get(key='ime_live');state.lease_until=timezone.now()+timedelta(minutes=1);state.save()
   self.assertIn('skipped',tasks.refresh_market('ime_live',force=True));sync.assert_called_once()

 def test_http_reader_has_fixed_origin_redirect_guard_and_bounded_response(self):
  from products.ime_live import _get_json,NoRedirect,MAX_BYTES,MARKETS_URL
  with self.assertRaises(Exception):_get_json('https://example.com/')
  self.assertIsNone(NoRedirect().redirect_request(None,None,302,'',{},'https://example.com'))
  with patch('products.ime_live.urllib.request.build_opener') as opener:
   opener.return_value.open.return_value.__enter__.return_value.read.return_value=b'[]'
   self.assertEqual(_get_json(MARKETS_URL),[])
   self.assertEqual(opener.return_value.open.return_value.__enter__.return_value.read.call_args.args,(MAX_BYTES+1,))
 def test_new_steel_shapes_in_legacy_history_are_reclassified_without_raw_edits(self):
  from importlib import import_module
  from django.apps import apps
  day=timezone.localdate()
  row=CommodityExchangeTrade.objects.create(source_report_id=88,symbol='CAST',goods_name='چدن',product_group='سایر صنعتی و معدنی',hall='تالار صنعتی و معدنی',trade_date=day,trade_date_jalali='1405/08/11',raw={'keep':True})
  migrate=import_module('products.migrations.0027_steel_shapes_history').classify_history
  migrate(apps,None);migrate(apps,None);row.refresh_from_db()
  self.assertEqual(row.product_group,'قراضه و فولاد');self.assertEqual(row.raw,{'keep':True})

 def test_manual_board_sync_is_staff_only_and_uses_shared_lease(self):
  from django.contrib.auth import get_user_model
  url='/api/admin/commodity-exchange/live/sync/'
  with patch('products.tasks.sync_ime_live',return_value=1) as upstream:
   self.assertIn(self.client.post(url).status_code,(401,403));upstream.assert_not_called()
   user=get_user_model().objects.create_user('ordinary-board');self.client.force_authenticate(user)
   self.assertEqual(self.client.post(url).status_code,403);upstream.assert_not_called()
   user.is_staff=True;user.save();self.assertEqual(self.client.post(url).status_code,200);upstream.assert_called_once()
   state=MarketDataSyncState.objects.get(key='ime_live');state.lease_until=timezone.now()+timedelta(minutes=1);state.save()
   self.assertEqual(self.client.post(url).status_code,409);upstream.assert_called_once()

 def test_material_name_beats_misleading_symbol_and_shape_in_snapshot_and_history(self):
  from products.ime_live import parse_snapshot
  from products.steel_scope import classify_steel_chain
  from importlib import import_module
  from django.apps import apps
  day=timezone.localdate()
  cases=[('لوله سیمانی','PIPE'),('لوله PVC','PIPE'),('لوله شیشه','PIPE'),('سیمان','STEEL'),('کاتد مس','DRI')]
  for n,(name,symbol) in enumerate(cases,100):
   self.assertIsNone(classify_steel_chain(name,symbol),(name,symbol))
   offer=self.offer(n,name);offer['InstrumentSymbol']=symbol
   self.assertEqual(parse_snapshot([{'MarketId':1}],[offer])['rows'],[])
   CommodityExchangeTrade.objects.create(source_report_id=n,symbol=symbol,goods_name=name,product_group='تیرآهن و مقاطع',hall='تالار صنعتی و معدنی',trade_date=day,trade_date_jalali='1405/08/11')
  import_module('products.migrations.0027_steel_shapes_history').classify_history(apps,None)
  self.assertEqual(self.client.get('/api/commodity-exchange/trades/').data['count'],0)
 def test_installed_timer_can_meet_minute_board_cadence(self):
  from pathlib import Path
  import re
  text=(Path(__file__).resolve().parents[1]/'ops/manual_deploy/install_market_timer.sh').read_text()
  value,unit=re.search(r'OnUnitActiveSec=(\d+)(s|min)',text).groups()
  seconds=int(value)*(60 if unit=='min' else 1)
  self.assertLessEqual(seconds,60)
 def test_old_worker_cannot_publish_or_clear_new_owners_lease(self):
  from products import tasks
  from products.external_markets import _sync_state_finish
  def old_worker():
   old=MarketDataSyncState.objects.get(key='ime_live')
   self.assertTrue(old.lease_token)
   old.lease_until=timezone.now()-timedelta(seconds=1);old.save(update_fields=['lease_until'])
   claimed=MarketDataSyncState.objects.filter(pk=old.pk,lease_until__lte=timezone.now()).update(lease_token='new-owner',lease_until=timezone.now()+timedelta(minutes=5),status='running',metadata={'new':'preserve'})
   self.assertEqual(claimed,1)
   _sync_state_finish(old,count=99,metadata={'old':'must not publish'})
   return 99
  with patch('products.tasks.sync_ime_live',side_effect=old_worker):
   with self.assertRaises(Exception):tasks.refresh_market('ime_live',force=True)
  state=MarketDataSyncState.objects.get(key='ime_live')
  self.assertEqual(state.lease_token,'new-owner');self.assertIsNotNone(state.lease_until)
  self.assertEqual(state.metadata,{'new':'preserve'});self.assertEqual(state.status,'running')
 def test_failed_scheduler_heartbeat_does_not_advance_last_success(self):
  from django.core.management import call_command,CommandError
  from products.external_markets import MarketSyncError
  from io import StringIO
  previous=timezone.now()-timedelta(days=1)
  MarketDataSyncState.objects.create(key='market_scheduler',last_success_at=previous)
  with patch('products.management.commands.sync_external_markets.refresh_market',side_effect=[MarketSyncError('safe'),{},{}]):
   with self.assertRaises(CommandError):call_command('sync_external_markets',stdout=StringIO())
  state=MarketDataSyncState.objects.get(key='market_scheduler')
  self.assertEqual(state.status,'error');self.assertEqual(state.last_success_at,previous)
