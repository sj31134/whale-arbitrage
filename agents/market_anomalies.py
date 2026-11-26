"""Public-market screens. Inputs are completed session dates, never a private watchlist."""
import json
import re
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

from . import analyst_feeds as feeds, market_prices

ZONE = {"KR": ZoneInfo("Asia/Seoul"), "US": ZoneInfo("America/New_York")}
# Listed sector funds are samples, not cash flows or a full industry census.
SECTORS = {
    "KR": {"091160.KS": "반도체", "091170.KS": "은행", "117680.KS": "철강", "140710.KS": "운송"},
    "US": dict(XLK="기술", XLF="금융", XLE="에너지", XLV="헬스케어", XLI="산업재",
               XLY="임의소비재", XLP="필수소비재", XLC="커뮤니케이션", XLU="유틸리티",
               XLB="소재", XLRE="부동산 업종", SOXX="반도체"),
}
STOCKS = {"KR": {"005930.KS":"삼성전자", "000660.KS":"SK하이닉스", "005380.KS":"현대차"},
          "US": {"AAPL":"Apple", "NVDA":"NVIDIA", "MSFT":"Microsoft", "AMZN":"Amazon", "JPM":"JPMorgan"}}
TOKEN_SAMPLE = ("AAPL", "NVDA", "TSLA", "SPY")
TOKEN_URL = ("https://api.kraken.com/0/public/Ticker?asset_class=tokenized_asset&pair="
             + ",".join(s+"xUSD" for s in TOKEN_SAMPLE))
LIMIT = 5


def number(value):
    return float(feeds.num(str(value).replace(",", "")))


def spread_bps(bid, ask):
    bid, ask = number(bid), number(ask)
    if not 0 < bid <= ask:
        raise ValueError("비정상 호가")
    return round(20000 * (ask-bid) / (ask+bid), 3)


def listing(feed, data, day):
    market = "KR" if feed in market_prices.KOREA else "US"
    rows = []
    for item in json.loads(data)["stocks"]:
        try:
            at = datetime.fromisoformat(item["localTradedAt"])
            if (at.utcoffset() is None or at.astimezone(ZONE[market]).date().isoformat() != day
                    or item.get("marketStatus") not in ("CLOSE", "CLOSED", "END")):
                continue
            symbol = item["itemCode"] if market == "KR" else item["symbolCode"]
            move = number(item["fluctuationsRatio"])
            rows.append(dict(market=market, kind="종목", symbol=symbol, name=item["stockName"], day=day,
                             change_pct=move, source=market_prices.endpoint(feed), basis=feed+" 시총 첫 페이지"))
        except (KeyError, ValueError, TypeError, ArithmeticError):
            continue
    return rows


def chart(market, symbol, label, kind, data, day, source):
    doc = json.loads(data)["chart"]["result"][0]
    if doc["meta"]["symbol"].upper() != symbol:
        raise ValueError("공개 종목 식별 불일치")
    q = doc["indicators"]["quote"][0]
    adjusted = doc["indicators"]["adjclose"][0]["adjclose"]
    entries = []
    for i, stamp in enumerate(doc["timestamp"]):
        d = datetime.fromtimestamp(stamp, ZONE[market]).date().isoformat()
        if d <= day:
            entries.append((d, i))
    entries.sort()
    if len(entries) < 2 or entries[-1][0] != day or len({d for d, _ in entries}) != len(entries):
        return []
    ids = [i for _, i in entries]
    i, prev = ids[-1], ids[-2]
    def positive(value):
        n = number(value)
        if n <= 0:
            raise ValueError("가격 누락")
        return n
    last = positive(adjusted[i])
    change = (last/positive(adjusted[prev]) - 1)*100
    r = dict(market=market, kind=kind, symbol=symbol.partition(".")[0], name=label, day=day,
             change_pct=round(change, 3), basis="배당·분할 조정 종가", source=source)
    high, low, close = (positive(q[k][i]) for k in ("high","low","close"))
    if low <= close <= high:
        r["range_pct"] = round((high-low)/close*100, 3)
    if len(ids) >= 6 and adjusted[ids[-6]]:
        r["five_day_pct"] = round((last/positive(adjusted[ids[-6]])-1)*100, 3)
    if len(ids) >= 22 and all(adjusted[j] and number(adjusted[j]) > 0 for j in ids[-22:]):
        prior = [100*(positive(adjusted[b])/positive(adjusted[a])-1)
                 for a,b in zip(ids[-22:-2],ids[-21:-1])]
        sd = statistics.stdev(prior)
        if sd > 0:
            r["prior_daily_sigma_pct"] = round(sd, 3)
            r["z"] = round((change-statistics.mean(prior))/sd, 3)
    if len(ids) >= 21 and all(q["volume"][j] is not None for j in ids[-21:]):
        volumes = [number(q["volume"][j]) for j in ids[-21:]]
        median = statistics.median(volumes[:-1])
        if median > 0 and min(volumes) >= 0:
            r["volume_multiple"] = round(volumes[-1]/median, 3)
    return [r]


class Table(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], [], None
    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        if tag in ("th","td"):
            self.cell = []
    def handle_data(self, text):
        if self.cell is not None:
            self.cell.append(text)
    def handle_endtag(self, tag):
        if tag in ("th","td") and self.cell is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        if tag == "tr" and self.row:
            self.rows.append(self.row)


def program(data, day, venue, source):
    try:
        html = data.decode("utf-8")
    except UnicodeDecodeError:
        html = data.decode("cp949")
    table = Table()
    table.feed(html)
    header = "".join("".join(row) for row in table.rows if not re.search(r"\d", "".join(row)))
    units = re.search(r"단위\s*[:：]?\s*(백만원|억원)", re.sub(r"<[^>]+>", " ", html))
    groups = re.search(r"(?<!비)차익.*?비차익.*?(?:전체|합계)", header)
    net_columns = any(len(row) >= 9 and all("순매수" in row[-9:][i] for i in (2,5,8))
                      for row in table.rows)
    if not units or not groups or not net_columns:
        raise ValueError("프로그램매매 헤더·단위 미확인")
    rows = []
    for row in table.rows:
        if len(row) != 10 or not re.fullmatch(r"(\d{2}|\d{4})\.\d{2}\.\d{2}", row[0]):
            continue
        key = ("20"+row[0] if len(row[0])==8 else row[0]).replace(".","-")
        if key <= day:
            rows.append((key, [number(row[i]) for i in (3,6,9)]))
    rows.sort(reverse=True)
    if not rows or rows[0][0] != day or len({r[0] for r in rows}) != len(rows):
        return []
    days = rows[:5]
    return [dict(venue=venue, day=day, category=label, unit=units[1], net=rows[0][1][i],
                 five_day_net=round(sum(r[1][i] for r in days), 3) if len(days)==5 else None,
                 sample_days=[r[0] for r in days], source=source)
            for i,label in enumerate(("차익","비차익","전체"))]


def token_book(data, checked):
    obj = json.loads(data)
    if obj["error"]:
        raise ValueError("공개 호가 응답 오류")
    rows = []
    for symbol in TOKEN_SAMPLE:
        row = next((v for k,v in obj["result"].items() if k.upper()==symbol+"XUSD"), None)
        if not row:
            continue
        try:
            spread = spread_bps(row["b"][0], row["a"][0])
        except (ValueError, ArithmeticError, KeyError, IndexError):
            continue
        rows.append(dict(market="XT",kind="토큰",symbol=symbol+"x",name=symbol+"x",venue="Kraken USD",
                         bid=row["b"][0],ask=row["a"][0],spread_bps=spread,observed=checked.isoformat(),
                         day=checked.astimezone(timezone.utc).date().isoformat(),basis="조회 순간 · 원천 호가시각 미제공",source=TOKEN_URL))
    return rows


def collect(days, fetcher=feeds.fetch, *, selected=None):
    jobs = []
    for feed in (*market_prices.KOREA,*market_prices.AMERICA):
        m = "KR" if feed in market_prices.KOREA else "US"
        jobs.append((feed,market_prices.endpoint(feed),"moves",lambda b,f=feed,d=days[m]: listing(f,b,d)))
    for m in ZONE:
        for kind,items in (("섹터 ETF 표본",SECTORS[m]),("종목",STOCKS[m])):
            for symbol,label in items.items():
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=3mo&interval=1d"
                jobs.append((symbol,url,"moves",lambda b,m=m,s=symbol,n=label,k=kind,u=url: chart(m,s,n,k,b,days[m],u)))
    for venue,code in (("KOSPI","01"),("KOSDAQ","02")):
        url = "https://finance.naver.com/sise/programDealTrendDay.naver?bizdate="+days["KR"].replace("-","")+"&sosok="+code
        jobs.append(("프로그램 "+venue,url,"program",lambda b,v=venue,u=url: program(b,days["KR"],v,u)))
    jobs.append(("Kraken xStocks",TOKEN_URL,"spreads",lambda b: token_book(b,datetime.now(timezone.utc))))
    if selected is not None:
        jobs = [job for job in jobs if job[0] in selected]
    def run(job):
        key,url,section,parse = job
        try:
            rows = parse(fetcher(dict(kind="quotes",url=url)))
            status = "확인" if rows else "해당 기준일·유효 관측 없음"
        except HTTPError as e:
            rows,status = [],f"HTTP {e.code}"
        except (OSError,URLError):
            rows,status = [],"연결 실패"
        except (ValueError,ArithmeticError,KeyError,IndexError,TypeError,AttributeError):
            rows,status = [],"원천 형식·자료 확인 필요"
        return key,section,status,rows
    with ThreadPoolExecutor(max_workers=5) as pool:
        result = list(pool.map(run,jobs))
    return {k:dict(section=s,status=status,rows=rows) for k,s,status,rows in result}


def rankings(feeds_by_key):
    # Keep distinct return definitions in separate samples. Rank both tails by magnitude.
    groups = {}
    for feed in feeds_by_key.values():
        if feed["section"] != "moves":
            continue
        for r in feed["rows"]:
            key = (r["market"],r["day"],r["kind"],r["basis"])
            groups.setdefault(key,{})[r["symbol"]] = r
    result = []
    for (m,day,kind,basis),by_symbol in sorted(groups.items()):
        flags = [r for r in by_symbol.values() if abs(r["change_pct"]) >= 3 or abs(r.get("z",0)) >= 2
                 or r.get("range_pct",0) >= 5]
        result.append(dict(market=m,day=day,kind=kind,basis=basis,coverage=len(by_symbol),flagged=len(flags),
                           leaders=sorted(flags,key=lambda r:(-abs(r["change_pct"]),r["symbol"]))[:LIMIT]))
    return result
