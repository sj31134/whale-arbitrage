"""Completed public sessions. The caller supplies only a public exchange listing."""

import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

US = ("NASDAQ", "NYSE", "AMEX")
VENUES = ("KRX", *US, "KRAKEN_X", "BINANCE_B")
PAIRS = "https://api.kraken.com/0/public/AssetPairs?asset_class=tokenized_asset"


# Public Binance Spot bStocks listing notices. Never derive queries from accounts.
BSTOCKS = frozenset("""
    AAOIB AAPLB ADBEB AGPUB ALABB AMATB AMCB AMDB AMZNB ANTB
    APPB ARMB ARTYB ASMLB ASTSB AVGOB AXTIB BABAB BEB BMNRB
    BNCB BOTB BRKBB BSPB CBRSB COHRB COINB CRCLB CRDOB CRMB
    CRWDB CRWVB CYPHB DELLB DJTB DRAMB EWJB EWTB EWYB EWZB
    EWZSB FLNCB FRHCB FWDIB GEVB GLWB GMEB GOOGLB GPROB GSB
    HIMSB HOODB HPEB IBITB IBMB IGVB INTCB INTWB IRENB IWMB
    JPMB KORUB KSTRB LITEB LLYB MDBB MELIB METAB MRNAB MRVLB
    MSFTB MSTRB MUB MUUB MVLLB NBISB NFLXB NOKB NUB NVDAB
    ORCLB PDDB PENGB PLTRB PYPLB QCOMB QNTB QQQB RDDTB RKLBB
    SECZB SHAZB SKDDB SKHYB SKUUB SMCIB SMHB SNDKB SNXXB SOXLB
    SOXSB SOXXB SPCXB SPYB SQQQB STXB TMFB TQQQB TSLAB TSMB
    USARB UVXYB VSTB WDCB WENB ZMB
""".split())


def binance_url(base):
    if base not in BSTOCKS and base not in {"BTC", "ETH"}:
        raise ValueError("공개 거래쌍 목록에 없음")
    return f"https://data-api.binance.vision/api/v3/klines?symbol={base}USDT&interval=1d&limit=1000"


def binance_daily(rows, now):
    """UTC daily candles with observed trades and a completed close timestamp."""
    previous = -1
    for r in rows:
        if len(r) != 12 or not isinstance(r[0], int) or r[0] % 86400000 or r[0] <= previous:
            raise ValueError("바이낸스 일봉 정렬·형식 오류")
        previous = r[0]
        if r[6] != r[0] + 86399999 or not isinstance(r[8], int) or r[8] < 0:
            raise ValueError("일봉 종료시각·체결수 오류")
        if r[6] >= int(now.timestamp() * 1000) or not r[8]:
            continue
        day = datetime.fromtimestamp(r[0] // 1000, timezone.utc).date()
        volume, value = price(r[5]), price(r[7])
        buys = [Decimal(str(r[i])) for i in (9, 10)]
        if any(not b.is_finite() or b < 0 or b > Decimal(limit)
               for b, limit in zip(buys, (volume, value))):
            raise ValueError("매수 거래량 범위 오류")
        yield candle(day, r[1:5]), (volume, value, r[8], str(buys[0]), str(buys[1]))


def token_listing(raw):
    doc = json.loads(raw)
    if doc["error"]:
        raise ValueError("거래소 응답 오류")
    pairs = {}
    for info in doc["result"].values():
        name = info.get("wsname", "").split("/")
        if (
            len(name) == 2
            and name[1] == "USD"
            and re.fullmatch(r"[A-Za-z0-9.]+[xX]", name[0])
        ):
            alt = info.get("altname", "")
            if alt.upper() == (name[0] + "USD").upper():
                pairs[name[0].upper()] = alt
    if not pairs:
        raise ValueError("공개 토큰화 주식 목록 대기")
    return pairs


def price(value):
    try:
        n = Decimal(str(value))
        if n.is_finite() and 0 < n < Decimal("1e20"):
            return format(n.normalize(), "f")
    except InvalidOperation:
        pass
    raise ValueError("가격 형식 오류")


def candle(day, values):
    o, h, l, c = (price(x) for x in values)
    if Decimal(h) < max(map(Decimal, (o, l, c))) or Decimal(l) > min(
        map(Decimal, (o, h, c))
    ):
        raise ValueError("일봉 가격 범위 오류")
    return (day.isoformat(), o, h, l, c)


def endpoint(job):
    venue, symbol, currency, feed = job
    if not re.fullmatch(r"[A-Za-z0-9.\-]{1,32}", symbol) or venue not in VENUES:
        raise ValueError("공개 종목 식별 오류")
    if venue == "BINANCE_B":
        if symbol not in BSTOCKS or currency != "USDT" or feed != symbol + currency:
            raise ValueError("bStock 거래쌍 식별 오류")
        return binance_url(symbol)
    if venue == "KRAKEN_X":
        if currency != "USD" or feed.upper() != symbol + "USD":
            raise ValueError("거래쌍 식별 오류")
        return "https://api.kraken.com/0/public/OHLC?" + urlencode(
            dict(pair=feed, interval=1440, asset_class="tokenized_asset")
        )
    code = symbol.replace(".", "-")
    if venue == "KRX":
        code += ".KQ" if feed == "KOSDAQ" else ".KS"
    return (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + quote(code, safe="")
        + "?range=2y&interval=1d"
    )


def read_bars(job, raw, now):
    venue, symbol, currency, feed = job
    doc = json.loads(raw, parse_float=Decimal)
    if venue == "BINANCE_B":
        endpoint(job)
        return [bar for bar, _ in binance_daily(doc, now)]
    if venue == "KRAKEN_X":
        if doc["error"]:
            raise ValueError("거래소 응답 오류")
        series = [v for k, v in doc["result"].items() if k.upper() == feed.upper()]
        if len(series) != 1:
            raise ValueError("거래쌍 응답 불일치")
        today = now.astimezone(timezone.utc).date()
        return [
            candle(datetime.fromtimestamp(r[0], timezone.utc).date(), r[1:5])
            for r in series[0][:-1]
            if datetime.fromtimestamp(r[0], timezone.utc).date() < today
            and int(r[7]) > 0
        ]
    result = doc["chart"]["result"][0]
    meta = result["meta"]
    expected = endpoint(job).split("/chart/")[1].split("?")[0]
    if (
        meta["symbol"].upper() != expected.upper()
        or meta["currency"] != currency
        or meta.get("dataGranularity") != "1d"
    ):
        raise ValueError("시계열 식별 불일치")
    tz = ZoneInfo("Asia/Seoul" if venue == "KRX" else "America/New_York")
    today = now.astimezone(tz).date()
    closing = meta.get("currentTradingPeriod", {}).get("regular", {}).get("end")
    ended = (
        closing is not None
        and datetime.fromtimestamp(closing, tz).date() == today
        and now.timestamp() >= closing + 1200
    )
    q = result["indicators"]["quote"][0]
    bars = []
    for i, stamp in enumerate(result["timestamp"]):
        day = datetime.fromtimestamp(stamp, tz).date()
        if day > today or (day == today and not ended):
            continue
        values = [q[k][i] for k in ("open", "high", "low", "close")]
        if all(x is not None for x in values):
            bars.append(candle(day, values))
    return bars


def naver_endpoint(symbol):
    if not re.fullmatch(r"[0-9A-Z]{6}", symbol):
        raise ValueError("국내 공개 코드 형식 오류")
    return "https://fchart.stock.naver.com/sise.nhn?" + urlencode(
        dict(symbol=symbol, timeframe="day", count=530, requestType=0)
    )


def naver_bars(raw, symbol, now, confirmed_close=None):
    from xml.etree import ElementTree

    try:
        if isinstance(raw, bytes) and re.match(
            br"""\s*<\?xml\b[^?]*\bencoding\s*=\s*['"](?:euc[-_]?kr|cp949)['"]""", raw[:200], re.I
        ):
            # Expat cannot parse Korean multibyte bytes directly.
            raw = raw.decode("cp949")
        chart = ElementTree.fromstring(raw).find(".//chartdata")
    except (ElementTree.ParseError, UnicodeError) as err:
        raise ValueError("국내 일봉 응답 오류") from err
    if chart is None or chart.get("symbol") != symbol:
        raise ValueError("국내 일봉 코드 불일치")
    today = now.astimezone(ZoneInfo("Asia/Seoul")).date()
    bars = []
    for item in chart.findall("item"):
        day, o, h, l, c, volume = item.attrib["data"].split("|")
        day = datetime.strptime(day, "%Y%m%d").date()
        confirmed = (
            day == today
            and confirmed_close is not None
            and price(c) == price(confirmed_close)
        )
        if (day < today or confirmed) and int(volume) > 0:
            bars.append(candle(day, (o, h, l, c)))
    return bars
