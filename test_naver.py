import os, unittest
from unittest.mock import patch,Mock
import naver_api as n
class NaverTests(unittest.TestCase):
    def setUp(self): n.cache.clear()
    def test_search_and_cache(self):
        r=Mock(status_code=200);r.json.return_value={'items':[{'title':'<b>삼성</b> &amp; 실적','description':'요약','originallink':'https://example.com/a','pubDate':'Fri, 02 Oct 2026 12:00:00 +0900'},{'link':'javascript:alert(1)'},{'link':'https://example.com/a'}]}
        with patch.dict(os.environ,{'NAVER_CLIENT_ID':'id','NAVER_CLIENT_SECRET':'secret'}),patch('naver_api.requests.get',return_value=r) as get:
            d=n.search('삼성');self.assertEqual(d['items'][0]['title'],'삼성 & 실적');self.assertEqual(len(d['items']),1)
            n.search('삼성');self.assertEqual(get.call_count,1)
            n.search('삼성','webkr');self.assertNotIn('sort',get.call_args.kwargs['params'])
    def test_errors(self):
        with patch.dict(os.environ,{'NAVER_CLIENT_ID':'','NAVER_CLIENT_SECRET':''}):
            with self.assertRaises(n.NaverError):n.search('test')
        for status in (403,429):
            with patch.dict(os.environ,{'NAVER_CLIENT_ID':'id','NAVER_CLIENT_SECRET':'secret'}),patch('naver_api.requests.get',return_value=Mock(status_code=status)):
                with self.assertRaises(n.NaverError):n.search('test')
if __name__=='__main__':unittest.main()
