"""KRX daily data; credentials stay on the server."""
import os, time, threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests

class KRXError(Exception):
    pass

def now():
    return datetime.now(ZoneInfo('Asia/Seoul'))

def number(value):
    try:
        return float(str(value).replace(',', ''))
    except (ValueError, TypeError):
        return None

class KRXClient:
    def __init__(self):
        self.cache = {}
        self.lock = threading.Lock()

    def daily(self, day):
        key = os.getenv('KRX_AUTH_KEY', '').strip() or os.getenv('KRX_API_KEY', '').strip()
        if not key:
            raise KRXError('서버 환경변수 KRX_AUTH_KEY에 KRX 인증키를 등록해 주세요.')
        stamp = day.strftime('%Y%m%d')
        with self.lock:
            cached = self.cache.get(stamp)
            if cached and time.time() - cached[0] < (21600 if cached[1] else 300):
                return cached[1]
            result = []
            for market, endpoint in [('KOSPI', 'stk_bydd_trd'), ('KOSDAQ', 'ksq_bydd_trd')]:
                try:
                    r = requests.get('https://data-dbg.krx.co.kr/svc/apis/sto/' + endpoint,
                                     headers={'AUTH_KEY': key}, params={'basDd': stamp}, timeout=12)
                    if r.status_code in (401, 403):
                        raise KRXError('KRX 인증 또는 이용승인을 확인해 주세요. 유가증권·코스닥 일별매매정보 모두 승인이 필요합니다.')
                    r.raise_for_status()
                    payload = r.json()
                    rows = payload.get('OutBlock_1')
                    if not isinstance(rows, list):
                        raise KRXError('KRX 응답에 일별매매정보가 없습니다. 인증키·이용승인을 확인해 주세요.')
                    for row in rows:
                        ticker = str(row.get('ISU_CD', '')).strip()
                        if len(ticker) != 6:
                            raise KRXError('KRX 종목코드 형식이 예상과 다릅니다.')
                        result.append(dict(ticker=ticker, name=row.get('ISU_NM', ''), market=market,
                            date=row.get('BAS_DD', stamp), close=number(row.get('TDD_CLSPRC')),
                            change_pct=number(row.get('FLUC_RT')), open=number(row.get('TDD_OPNPRC')),
                            high=number(row.get('TDD_HGPRC')), low=number(row.get('TDD_LWPRC')),
                            volume=number(row.get('ACC_TRDVOL')), value=number(row.get('ACC_TRDVAL')),
                            market_cap=number(row.get('MKTCAP'))))
                except KRXError:
                    raise
                except (requests.RequestException, ValueError):
                    raise KRXError('KRX 연결에 실패했습니다. 잠시 후 다시 시도해 주세요.') from None
            self.cache[stamp] = (time.time(), result)
            return result

    def latest(self, day=None):
        day = day or now().date()
        for offset in range(15):
            target = day - timedelta(days=offset)
            if target.weekday() >= 5:
                continue
            rows = self.daily(target)
            if rows:
                return rows
        raise KRXError('최근 15일에 조회 가능한 KRX 데이터가 없습니다.')

client = KRXClient()
