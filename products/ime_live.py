"""Periodic official TTS snapshot. Seller prices never become final trade records."""
import json
from decimal import Decimal, InvalidOperation
import urllib.request
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import MarketDataSyncState
from .steel_scope import classify_steel_chain
from .external_markets import MarketSyncError, _sync_state_start, _sync_state_finish, _sync_state_error

MARKETS_URL = 'https://dataapi.ime.co.ir/api/spotmarketdata/GetMarketsInfo'
OFFERS_URL = 'https://dataapi.ime.co.ir/api/spotmarketdata/GetTradesWithId/1'
SOURCE_URL = 'https://tts.ime.co.ir/صنعتی%20و%20معدنی'
MAX_BYTES = 2 * 1024 * 1024
ERROR = 'دریافت تابلوی رسمی زنجیره فولاد انجام نشد.'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _get_json(url):
    if url not in (MARKETS_URL, OFFERS_URL):
        raise MarketSyncError(ERROR)
    request = urllib.request.Request(url, headers={'Accept':'application/json',
        'Origin':'https://tts.ime.co.ir', 'Referer':'https://tts.ime.co.ir/',
        'User-Agent':'KavehMetal-SteelBoard/1.0'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(request,
                timeout=min(30, settings.MARKET_HTTP_TIMEOUT_SECONDS)) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('oversized response')
        return json.loads(raw.decode('utf-8-sig'))
    except Exception as exc:
        raise MarketSyncError(ERROR) from exc


def _number(value):
    if value is None or value == '':
        return None
    if isinstance(value, bool):
        raise ValueError('invalid boolean')
    try:
        result = Decimal(str(value).replace(',', ''))
    except InvalidOperation as exc:
        raise ValueError('invalid number') from exc
    if not result.is_finite() or result < 0 or result > Decimal('1e25'):
        raise ValueError('invalid number')
    return str(result)


def _text(row, key, required=False):
    value = row.get(key)
    if value is not None and not isinstance(value, str):
        raise ValueError('invalid text')
    value = (value or '').strip()
    if len(value) > 1000 or (required and not value):
        raise ValueError('invalid text')
    return value


def parse_snapshot(markets, instruments):
    if not isinstance(markets, list) or not isinstance(instruments, list) or len(instruments)>10000:
        raise ValueError('invalid snapshot lists')
    market = next((m for m in markets if isinstance(m, dict) and type(m.get('MarketId')) is int and m['MarketId']==1), None)
    if market is None:
        raise ValueError('industrial market missing')
    seen, rows = set(), []
    for item in instruments:
        if not isinstance(item, dict) or type(item.get('MarketId')) is not int or item['MarketId']!=1:
            raise ValueError('wrong market')
        identity = item.get('InstrumentId')
        if type(identity) is not int or identity<=0 or identity in seen:
            raise ValueError('invalid or duplicate identity')
        seen.add(identity)
        name = _text(item, 'InstrumentName', True)
        symbol = _text(item, 'InstrumentSymbol')
        group = classify_steel_chain(name, symbol)
        # Validate numeric fields even when an unrelated instrument is excluded.
        numbers = {target:_number(item.get(source)) for target,source in (
            ('seller_price','CurrentSellPrice'),('offered_volume','QtySell'),('demand_volume','TotalBuyQty'))}
        if not group or item.get('IsDeleted') is True:
            continue
        rows.append({'offer_id':identity,'goods_name':name,'symbol':symbol,'product_group':group,
            'producer_name':_text(item,'Producer'),'supplier_name':_text(item,'Supplier'),
            'currency':_text(item,'Currency'),'unit':_text(item,'Unit'),
            'status':_text(item,'TradeStatusDesc') or _text(item,'StatusDesc'),
            'delivery_date':_text(item,'DeliveryDate'),'delivery_place':_text(item,'DeliveryPlace'),**numbers})
    return {'rows':rows, 'session_date':None, 'market':{'name':'صنعتی و معدنی — زنجیره فولاد',
        'start_time':_text(market,'StartTime'),'finish_time':_text(market,'FinishTime')}}


def sync_ime_live():
    state = _sync_state_start('ime_live')
    try:
        snapshot = parse_snapshot(_get_json(MARKETS_URL), _get_json(OFFERS_URL))
        snapshot['fetched_at'] = timezone.now().isoformat()
        _sync_state_finish(state, count=len(snapshot['rows']), metadata=snapshot)
        return len(snapshot['rows'])
    except Exception as exc:
        _sync_state_error(state, MarketSyncError(ERROR))
        raise MarketSyncError(ERROR) from exc


def live_snapshot():
    state = MarketDataSyncState.objects.filter(key='ime_live').first()
    data = state.metadata if state and isinstance(state.metadata,dict) else {}
    received = parse_datetime(data.get('fetched_at') or '')
    age = (timezone.now()-received).total_seconds() if received and timezone.is_aware(received) else None
    rows = data.get('rows', [])
    has_snapshot = isinstance(rows,list) and received is not None
    failed = bool(state and (state.status=='error' or state.error_message))
    return {'rows':rows if has_snapshot else [],'count':len(rows) if has_snapshot else 0,
        'has_snapshot':has_snapshot,'fetched_at':data.get('fetched_at') if has_snapshot else None,
        'session_date':None,'stale':failed or age is None or age>180,
        'error':ERROR if failed else '', 'market':data.get('market',{}),
        'source':{'name':'تابلوی رسمی بورس کالا','url':SOURCE_URL},'market_scope':'steel_chain'}
