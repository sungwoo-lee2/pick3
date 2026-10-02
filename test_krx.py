import os, tempfile, unittest
from datetime import date, datetime
from unittest.mock import patch, Mock
os.environ['DB_PATH'] = tempfile.mktemp(suffix='.db')
import app
from krx_api import KRXClient, KRXError
ROWS = [dict(ticker='005930', name='삼성전자', market='KOSPI', date='20260925', close=100, change_pct=1, volume=10, value=1000)]
class Integration(unittest.TestCase):
    def setUp(self):
        self.c = app.app.test_client()
        self.code = self.c.post('/api/rooms', json={'name':'test','pin':'9876'}).json['code']
        self.base = '/api/rooms/'+self.code
        self.c.post(self.base+'/join', json={'name':'A'})
    @patch.object(app.krx, 'latest', return_value=ROWS)
    def test_selection_and_prices(self, latest):
        self.assertEqual(self.c.get(self.base+'/stocks?q=삼성').json['items'][0]['ticker'], '005930')
        self.assertEqual(self.c.get(self.base+'/quote/005930').json['close'],100)
        self.assertEqual(self.c.post(self.base+'/pick',json={'ticker':'005930','stock':'wrong','reason':'test'}).status_code,200)
        self.assertEqual(self.c.post(self.base+'/auto-prices').status_code,403)
        self.c.post(self.base+'/admin-login',json={'pin':'9876'})
        with patch.object(app,'korea_now',return_value=datetime(2026,9,30)):
            d=self.c.post(self.base+'/auto-prices').json
            self.assertIsNone(d['end_date'])
            p=self.c.get(self.base+'/state').json['players'][0]
            self.assertEqual(p['start'],100)
            self.assertIsNone(p['end'])
        with patch.object(app,'korea_now',return_value=datetime(2026,10,3)):
            self.assertEqual(self.c.post(self.base+'/auto-prices').json['updated'],1)
            p=self.c.get(self.base+'/state').json['players'][0]
            self.assertEqual(p['end'],100)
        with patch.object(app.krx,'latest',side_effect=KRXError('failure')):
            self.assertEqual(self.c.post(self.base+'/auto-prices').status_code,503)
    def test_missing_key(self):
        with patch.dict(os.environ, {'KRX_AUTH_KEY':''}):
            self.assertEqual(self.c.get(self.base+'/stocks?q=삼성').status_code,503)
    def test_http_cache_and_auth(self):
        row={'ISU_CD':'005930','ISU_NM':'삼성전자','TDD_CLSPRC':'1,000','BAS_DD':'20261002'}
        response=Mock(status_code=200);response.json.return_value={'OutBlock_1':[row]}
        with patch.dict(os.environ,{'KRX_AUTH_KEY':'test-secret'}),patch('krx_api.requests.get',return_value=response) as get:
            client=KRXClient();self.assertEqual(client.daily(date(2026,10,2))[0]['close'],1000)
            client.daily(date(2026,10,2));self.assertEqual(get.call_count,2)
            self.assertEqual(get.call_args.kwargs['headers']['AUTH_KEY'],'test-secret')
        response.status_code=403
        with patch.dict(os.environ,{'KRX_AUTH_KEY':'bad'}),patch('krx_api.requests.get',return_value=response):
            with self.assertRaises(KRXError): KRXClient().daily(date(2026,10,2))
if __name__ == '__main__':
    try: unittest.main()
    finally: os.unlink(os.environ['DB_PATH'])
