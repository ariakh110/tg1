from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase
from products.models import CommodityExchangeTrade


class TradedReportFilterTests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(get_user_model().objects.create_user('traded-reports-admin', is_staff=True))
        for index, volume in enumerate([20, 0, None, -1], 1):
            CommodityExchangeTrade.objects.create(source_report_id=index, symbol=f'T-{index}', goods_name=f'ورق {index}',
                product_group='ورق', producer_name='کارخانه', trade_date=timezone.localdate(),
                trade_date_jalali='1405/08/03', traded_volume=volume, offered_volume=100, unit='تن')

    def report(self, **extra):
        return self.client.post('/api/messaging/market-drafts/', {'date':str(timezone.localdate()), **extra}, format='json')

    def test_item_filter_keeps_only_positive_trades_and_default_preserves_all(self):
        self.assertEqual(len(self.report().data['results']), 4)
        response=self.report(traded_only=True)
        self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.data['results']),1)
        self.assertIn('T-1',response.data['results'][0]['texts']['telegram'])

    def test_summary_filters_before_aggregation(self):
        response=self.report(traded_only=True,kind='summary')
        self.assertEqual(response.status_code,200)
        text=response.data['results'][0]['texts']['telegram']
        self.assertIn('تعداد نمادها: ۱',text)
        self.assertIn('حجم عرضه: ۱۰۰ تن',text)
        self.assertIn('حجم معامله: ۲۰ تن',text)

    def test_empty_results_and_invalid_boolean(self):
        CommodityExchangeTrade.objects.filter(traded_volume__gt=0).update(traded_volume=0)
        self.assertEqual(self.report(traded_only=True).data['results'],[])
        self.assertEqual(self.report(traded_only='false').status_code,400)
