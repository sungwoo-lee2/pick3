import os, time, re, html, threading
from urllib.parse import urlparse
import requests
class NaverError(Exception): pass
cache = {}
lock = threading.Lock()
def clean(text):
    return html.unescape(re.sub(r'<[^>]*>', '', str(text or '')))
def safe_url(url):
    parsed = urlparse(str(url or ''))
    return url if parsed.scheme in ('http', 'https') and parsed.netloc else ''
def search(query, kind='news', sort='date'):
    cid, secret = os.getenv('NAVER_CLIENT_ID','').strip(), os.getenv('NAVER_CLIENT_SECRET','').strip()
    if not cid or not secret:
        raise NaverError('서버에 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 등록해 주세요.')
    key=(cid,query,kind,sort)
    with lock:
        cached=cache.get(key)
        if cached and time.time()-cached[0]<300: return cached[1]
        try:
            r=requests.get('https://openapi.naver.com/v1/search/'+kind+'.json',
                headers={'X-Naver-Client-Id':cid,'X-Naver-Client-Secret':secret},
                params={'query':query,'display':10,'start':1,**({'sort':sort} if kind=='news' else {})},timeout=10)
            if r.status_code in (401,403):
                try:
                    code = str(r.json().get('errorCode', 'UNKNOWN'))
                except (ValueError, AttributeError):
                    code = 'UNKNOWN'
                code = re.sub(r'[^A-Za-z0-9_-]', '', code)[:32] or 'UNKNOWN'
                raise NaverError(f'네이버 API 요청 거절: HTTP {r.status_code} / 오류코드 {code}. 개발자센터 설정이 맞다면 이 앱의 Render 환경변수와 배포 적용 상태를 확인해 주세요.')
            if r.status_code==429: raise NaverError('네이버 API 호출 한도를 초과했습니다. 잠시 후 다시 시도해 주세요.')
            r.raise_for_status(); data=r.json()
            if not isinstance(data.get('items'),list): raise NaverError('네이버 검색 응답 형식이 올바르지 않습니다.')
            items=[]; seen=set()
            for row in data['items']:
                url=safe_url(row.get('originallink')) or safe_url(row.get('link'))
                if not url or url in seen: continue
                seen.add(url)
                items.append(dict(title=clean(row.get('title')),description=clean(row.get('description')),
                    url=url,source=urlparse(url).hostname,date=row.get('pubDate','')))
            result=dict(items=items,query=query,kind=kind,total=data.get('total',0),source='NAVER', fetched_at=time.time())
            if len(cache)>=128: cache.pop(next(iter(cache)))
            cache[key]=(time.time(),result)
            return result
        except NaverError: raise
        except (requests.RequestException,ValueError): raise NaverError('네이버 검색 연결에 실패했습니다. 잠시 후 다시 시도해 주세요.') from None
