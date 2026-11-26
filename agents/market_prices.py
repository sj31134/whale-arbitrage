"""Fixed public quote universes. No portfolio, account or symbol input."""
import json
import math
import re
import socket
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from urllib.error import HTTPError, URLError

from . import analyst_feeds as feeds

# Each venue refreshes its leading page and walks one further page per cycle.
PAGE = 60
KOREA = ("KOSPI", "KOSDAQ")
AMERICA = ("NASDAQ", "NYSE", "AMEX")
# Broad Korean index ETF sample. The list is independent of personal accounts.
ETF_SAMPLE = ("069500", "102110", "360750", "133690")
LABELS = {**{v: v for v in (*KOREA, *AMERICA)},
          **{s: "국내 ETF " + s for s in ETF_SAMPLE},
          "kraken_x": "Kraken 토큰화 주식 USD", "etf": "국내 ETF 전체 순환", "upbit": "업비트 KRW", "binance": "바이낸스 USDT", "fx": "USD/KRW"}
INTERVAL = 30
STREAMS = {"upbit_stream": "업비트 체결 스트림", "binance_stream": "바이낸스 시세 스트림"}
STREAM_URLS = {"upbit_stream": "wss://api.upbit.com/websocket/v1",
               "binance_stream": "wss://stream.binance.com:9443/ws/!miniTicker@arr"}
SOURCES = {**LABELS, **STREAMS}


def origin(feed, page=1):
    if feed == "upbit_sample":
        return "https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH"
    if feed == "upbit_stream":
        return "https://docs.upbit.com/kr/reference/websocket-ticker"
    if feed == "binance_stream":
        return "https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams"
    return endpoint(feed, page)


def endpoint(feed, page=1):
    if feed == "kraken_x":
        return "https://api.kraken.com/0/public/Ticker?asset_class=tokenized_asset"
    if feed in KOREA:
        base = "https://m.stock.naver.com/api/stocks/marketValue/" + feed
    elif feed in AMERICA:
        base = "https://api.stock.naver.com/stock/exchange/" + feed + "/marketValue"
    elif feed == "etf":
        return "https://finance.naver.com/api/sise/etfItemList.nhn"
    elif feed in ETF_SAMPLE:
        return "https://m.stock.naver.com/api/stock/" + feed + "/basic"
    elif feed == "fx":
        return "https://api.stock.naver.com/marketindex/exchange/FX_USDKRW"
    elif feed == "upbit":
        return "https://api.upbit.com/v1/ticker/all?quote_currencies=KRW"
    elif feed == "binance":
        return "https://data-api.binance.vision/api/v3/ticker/24hr?type=MINI"
    else:
        raise ValueError("unknown feed")
    return f"{base}?page={page}&pageSize={PAGE}"


def stamp(raw):
    if isinstance(raw, int):
        dt = datetime.fromtimestamp(raw / 1000, timezone.utc)
    else:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("missing source timezone")
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds")


def parse(feed, data):
    source = json.loads(data, parse_float=Decimal)
    pages = 1
    if feed == "kraken_x":
        if source["error"]:
            raise ValueError("거래소 응답 오류")
        rows = [dict(r, pair=k) for k,r in source["result"].items()]
    elif feed in KOREA + AMERICA:
        rows = source["stocks"]
        pages = max(1, math.ceil(int(source["totalCount"]) / PAGE))
    elif feed in ETF_SAMPLE or feed == "etf":
        rows = [source]
    elif feed == "fx":
        item = source.get("exchangeInfo", source.get("result", source))
        rows = item if isinstance(item, list) else [item]
    else:
        rows = source
    result = []
    for row in rows:
        try:
            if feed == "kraken_x":
                pair = row["pair"].upper()
                if not re.fullmatch(r"[A-Z0-9.]+XUSD",pair) or feeds.num(str(row["v"][1])) <= 0:
                    continue
                symbol,venue,currency = pair[:-3],"KRAKEN_X","USD"
                price,when = row["c"][0],datetime.now(timezone.utc).isoformat()
            elif feed == "upbit":
                market, symbol = row["market"].split("-", 1)
                if market != "KRW":
                    continue
                currency, venue, price, when = market, feed, row["trade_price"], row["trade_timestamp"]
            elif feed == "binance":
                pair = row["symbol"]
                if not pair.endswith("USDT") or pair == "USDT":
                    continue
                if "volume" in row and feeds.num(row["volume"]) <= 0:
                    continue
                symbol = pair[:-4]
                currency, venue, price, when = "USDT", feed, row["lastPrice"], row["closeTime"]
            else:
                if feed == "fx":
                    if row.get("reutersCode", row.get("symbolCode")) != "FX_USDKRW":
                        continue
                    symbol, currency, venue = "USD/KRW", "KRW", "fx"
                elif feed in AMERICA:
                    symbol, currency, venue = row["symbolCode"], "USD", feed
                else:
                    symbol, currency, venue = row["itemCode"], "KRW", "KRX"
                    if feed in ETF_SAMPLE and symbol != feed:
                        continue
                price, when = row["closePrice"], row["localTradedAt"]
            if not re.fullmatch(r"[A-Za-z0-9./_\-]{1,32}", symbol):
                continue
            price = feeds.num(str(price).replace(",", ""))
            if price <= 0:
                continue
            result.append(dict(venue=venue, symbol=symbol.upper(), currency=currency,
                               name=str(row.get("stockName") or "")[:120],
                               english=str(row.get("stockNameEng") or "")[:120],
                               price=format(price, "f"), at=stamp(when),
                               session=str(row.get("marketStatus") or "")[:20],
                               delay=str(row.get("delayTime", ""))[:12]))
            if (venue in ("KRX",*AMERICA) and row.get("openPrice") is not None
                    and result[-1]["session"] in ("OPEN","TRADING","CLOSE","CLOSED","END")):
                try:
                    opening = feeds.num(str(row["openPrice"]).replace(",",""))
                    if opening>0:
                        result[-1]["opening"] = format(opening,"f")
                except (ValueError,ArithmeticError):
                    pass
        except (ValueError, KeyError, TypeError, ArithmeticError, OSError, OverflowError):
            continue
    if not result:
        raise ValueError("no usable quotes")
    return result, pages


def collect(cursors, fetcher=feeds.fetch):
    """Only public pagination state is supplied to the collector."""
    jobs = [(feed, max(1, cursors.get(feed, 1)) if feed == "etf" else 1) for feed in LABELS]
    jobs += [(feed, page) for feed, page in cursors.items()
             if feed in KOREA + AMERICA and 2 <= page <= 500]

    def run(job):
        feed, page = job
        url = endpoint(feed, page)
        try:
            if feed == "etf":
                # Resolve a deterministic slice of the public listing, never a portfolio input.
                raw = fetcher({"kind": "quotes", "url": url})
                listing = json.loads(raw.decode("utf-8") if raw.isascii() else raw.decode("cp949", errors="replace"))
                codes = sorted({r["itemcode"] for r in listing["result"]["etfItemList"]
                                if re.fullmatch("[0-9A-Z]{6}", r["itemcode"]) and r["itemcode"] not in ETF_SAMPLE})
                size = 6
                pages = math.ceil(len(codes) / size)
                if not pages:
                    raise ValueError("empty ETF listing")
                page = 1 if page > pages else page
                rows = []
                for code in codes[(page-1)*size:page*size]:
                    basic = "https://m.stock.naver.com/api/stock/" + code + "/basic"
                    try:
                        batch, _ = parse(feed, fetcher({"kind": "quotes", "url": basic}))
                        rows.extend(row for row in batch if row["symbol"] == code)
                    except (OSError, KeyError, ValueError, TypeError):
                        continue
                if not rows:
                    raise ValueError("no usable ETF quotes")
                state = "수집 완료" if len(rows) == len(codes[(page-1)*size:page*size]) else "일부 누락"
                return feed, page, pages, rows, state
            raw = fetcher({"kind": "quotes", "url": url})
            rows, pages = parse(feed, raw)
            status = "수집 완료"
            if feed in KOREA + AMERICA and len(rows) < len(json.loads(raw)["stocks"]):
                status = "일부 누락"
            return feed, page, pages, rows, status
        except HTTPError as exc:
            status = f"HTTP {exc.code}"
        except URLError as exc:
            status = "DNS 실패" if isinstance(exc.reason, socket.gaierror) else "연결 실패"
        except (OSError, ValueError, KeyError, TypeError, ArithmeticError):
            status = "응답·형식 오류"
        return feed, page, None, [], status
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(run, jobs))


def stream_rows(feed, raw):
    obj = json.loads(raw, parse_float=str)
    if feed == "upbit_stream":
        if obj.get("type") != "ticker":
            return []
        records = [{"market": obj["code"], "trade_price": obj["trade_price"], "trade_timestamp": obj["trade_timestamp"]}]
    else:
        records = [{"symbol": r["s"], "lastPrice": r["c"], "closeTime": r["E"], "volume": r["v"]}
                   for r in obj if r.get("e") == "24hrMiniTicker" and r["s"].endswith("USDT") and feeds.num(r["v"]) > 0]
    return parse(feed.split("_")[0], json.dumps(records))[0] if records else []


def stream(feed, stopped, save):
    try:
        from websockets.sync.client import connect
        from websockets.exceptions import WebSocketException
    except ImportError:
        save(feed, [], "스트림 모듈 미설치")
        return
    backoff = 5
    while not stopped.is_set():
        try:
            codes = []
            if feed == "upbit_stream":
                public = feeds.fetch({"kind": "quotes", "url": "https://api.upbit.com/v1/market/all"})
                codes = sorted({r["market"] for r in json.loads(public) if re.fullmatch("KRW-[A-Z0-9]+", r["market"])})
                if not codes:
                    raise ValueError("public market list empty")
            with connect(STREAM_URLS[feed], open_timeout=7, close_timeout=2, max_size=4_000_000) as conn:
                if codes:
                    conn.send(json.dumps([{"ticket": str(uuid.uuid4())}, {"type": "ticker", "codes": codes}]))
                pending = {}
                last_write = 0
                while not stopped.is_set():
                    for row in stream_rows(feed, conn.recv(timeout=20)):
                        old = pending.get(row["symbol"])
                        if old is None or row["at"] >= old["at"]:
                            pending[row["symbol"]] = row
                    if pending and time.monotonic() - last_write >= 3:
                        save(feed, list(pending.values()), "수집 완료")
                        pending.clear()
                        backoff = 5
                        last_write = time.monotonic()
        except (OSError, TimeoutError, ValueError, KeyError, TypeError, WebSocketException):
            save(feed, [], "스트림 연결 실패")
        if stopped.wait(backoff):
            break
        backoff = min(90, backoff * 2)
