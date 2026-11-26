"""Replay verified public spot and FX responses into the legacy analytics database."""

import argparse
import hashlib
import json
import sqlite3
from collections import defaultdict
from decimal import Decimal
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from agents.equities.daily_bars import binance_daily, candle, price

PAIRS = {"BTCUSDT", "ETHUSDT"}
TABLES = {
    "api.upbit.com": (
        "upbit_daily",
        "market,date,opening_price,high_price,low_price,trade_price,acc_trade_volume_24h,acc_trade_price_24h",
    ),
    "api.bybit.com": (
        "bybit_spot_daily",
        "symbol,date,open,high,low,close,volume,quote_volume",
    ),
    "api.bitget.com": (
        "bitget_spot_daily",
        "symbol,date,open,high,low,close,volume,quote_volume",
    ),
    "api.frankfurter.dev": ("exchange_rate", "date,krw_usd"),
}


def observations(url, document, cutoff):
    parsed = urlsplit(url)
    query = {k: v[0] for k, v in parse_qs(parsed.query).items() if len(v) == 1}
    host = parsed.netloc
    if parsed.scheme != "https" or host not in TABLES:
        raise ValueError("공개 원천 확인 필요")
    if host == "api.frankfurter.dev":
        if (
            query.get("symbols") != "KRW"
            or query.get("base") != "USD"
            or document["base"] != "USD"
        ):
            raise ValueError("환율 통화 불일치")
        for day, values in document["rates"].items():
            if date.fromisoformat(day) < cutoff:
                yield (day, price(values["KRW"]))
        return
    if host == "api.upbit.com":
        pair = query["market"]
        if parsed.path != "/v1/candles/days" or pair not in {"KRW-BTC", "KRW-ETH"}:
            raise ValueError("업비트 시장 불일치")
        for row in document:
            start = datetime.fromisoformat(row["candle_date_time_utc"])
            if row["market"] != pair or start != datetime.combine(
                start.date(), datetime.min.time()
            ):
                raise ValueError("업비트 일봉 식별 오류")
            if start.date() < cutoff:
                bar = candle(
                    start.date(),
                    [
                        row[k]
                        for k in (
                            "opening_price",
                            "high_price",
                            "low_price",
                            "trade_price",
                        )
                    ],
                )
                yield (
                    pair,
                    *bar,
                    price(row["candle_acc_trade_volume"]),
                    price(row["candle_acc_trade_price"]),
                )
        return
    pair = query["symbol"]
    if pair not in PAIRS:
        raise ValueError("거래쌍 불일치")
    if host == "api.bybit.com":
        result = document["result"]
        if (
            parsed.path != "/v5/market/kline"
            or document["retCode"] != 0
            or result["symbol"] != pair
            or result["category"] != "spot"
            or query.get("interval") != "D"
        ):
            raise ValueError("바이비트 현물 일봉 식별 오류")
        rows = result["list"]
    else:
        if (
            parsed.path
            not in {
                "/api/v2/spot/market/candles",
                "/api/v2/spot/market/history-candles",
            }
            or query["granularity"] != "1Dutc"
            or document["code"] != "00000"
        ):
            raise ValueError("비트겟 UTC 일봉 식별 오류")
        rows = document["data"]
    for row in rows:
        ts = int(row[0])
        if ts % 86400000:
            raise ValueError("UTC 경계 불일치")
        day = datetime.fromtimestamp(ts // 1000, timezone.utc).date()
        if day < cutoff:
            yield (pair, *candle(day, row[1:5]), price(row[5]), price(row[6]))


# Fields retain the same units as the existing extended-metrics collector.
EXTENDED = {
    "globalLongShortAccountRatio": (
        ("longShortRatio", "longAccount", "shortAccount"),
        ("long_short_ratio", "long_account_pct", "short_account_pct"),
    ),
    "takerlongshortRatio": (
        ("buySellRatio", "buyVol", "sellVol"),
        ("taker_buy_sell_ratio", "taker_buy_vol", "taker_sell_vol"),
    ),
    "topLongShortPositionRatio": (
        ("longShortRatio",),
        ("top_trader_long_short_ratio",),
    ),
}


def import_futures(db, url, rows, cutoff):
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    pair = query["symbol"][0]
    path = parsed.path
    metric = path.rsplit("/", 1)[-1]
    if (
        parsed.scheme != "https"
        or parsed.netloc != "fapi.binance.com"
        or pair not in PAIRS
    ):
        raise ValueError("선물 원천 식별 오류")
    if path == "/fapi/v1/klines" and query.get("interval") == ["1d"]:
        midnight = datetime.combine(cutoff, datetime.min.time(), tzinfo=timezone.utc)
        candles = list(binance_daily(rows, midnight))
        for bar, _ in candles:
            day, _, high, low, close = bar
            volatility = (Decimal(high) - Decimal(low)) / Decimal(close)
            db.execute(
                """INSERT INTO binance_futures_metrics(symbol,date,volatility_24h) VALUES(?,?,?)
                ON CONFLICT(date,symbol) DO UPDATE SET volatility_24h=coalesce(volatility_24h,excluded.volatility_24h)""",
                (pair, day, str(volatility)),
            )
        return len(candles)
    funding = path == "/fapi/v1/fundingRate"
    if not funding and (
        metric not in {*EXTENDED, "openInterestHist"}
        or path != "/futures/data/" + metric
        or query.get("period") != ["1d"]
    ):
        raise ValueError("선물 지표 식별 오류")
    totals = defaultdict(list)
    dates = set()
    count = 0
    for row in rows:
        stamp = row["fundingTime" if funding else "timestamp"]
        if stamp in dates or row.get("symbol", pair) != pair:
            raise ValueError("선물 시점 또는 심볼 오류")
        dates.add(stamp)
        day = datetime.fromtimestamp(stamp / 1000, timezone.utc).date()
        if day >= cutoff:
            continue
        if funding:
            rate = Decimal(row["fundingRate"])
            if not rate.is_finite() or not int(query["startTime"][0]) <= stamp <= int(
                query["endTime"][0]
            ):
                raise ValueError("펀딩 기간·값 오류")
            totals[day].append(rate)
        elif metric == "openInterestHist":
            # Legacy scripts mix base units and USD in sum_open_interest.
            db.execute(
                """CREATE TABLE IF NOT EXISTS binance_open_interest_daily(
                symbol TEXT,date TEXT,base_quantity TEXT,notional_usdt TEXT,
                PRIMARY KEY(symbol,date)) WITHOUT ROWID"""
            )
            db.execute(
                "INSERT OR IGNORE INTO binance_open_interest_daily VALUES(?,?,?,?)",
                (
                    pair,
                    day.isoformat(),
                    price(row["sumOpenInterest"]),
                    price(row["sumOpenInterestValue"]),
                ),
            )
        else:
            fields, columns = EXTENDED[metric]
            values = [price(row[k]) for k in fields]
            updates = ",".join(
                f"{col}=coalesce({col},excluded.{col})" for col in columns
            )
            db.execute(
                f"INSERT INTO futures_extended_metrics(symbol,date,{','.join(columns)}) "
                f"VALUES(?,?,{','.join('?' for _ in values)}) ON CONFLICT(date,symbol) "
                f"DO UPDATE SET {updates}",
                (pair, day.isoformat(), *values),
            )
        count += 1
    for day, rates in totals.items():
        db.execute(
            """INSERT INTO binance_futures_metrics(symbol,date,avg_funding_rate) VALUES(?,?,?)
            ON CONFLICT(date,symbol) DO UPDATE SET avg_funding_rate=coalesce(avg_funding_rate,excluded.avg_funding_rate)""",
            (pair, day.isoformat(), str(sum(rates) / len(rates))),
        )
    return count


def restore(db, snapshot, cutoff):
    raw = snapshot.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    with db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS public_market_import(
            sha256 TEXT, url TEXT, cutoff TEXT, inserted INTEGER, PRIMARY KEY(sha256,url,cutoff))"""
        )
        for url, doc in json.loads(raw).items():
            if urlsplit(url).netloc == "fapi.binance.com":
                if db.execute(
                    "SELECT 1 FROM public_market_import WHERE sha256=? AND url=? AND cutoff=?",
                    (digest, url, cutoff.isoformat()),
                ).fetchone():
                    continue
                before = db.total_changes
                processed = import_futures(db, url, doc, cutoff)
                changes = db.total_changes - before
                db.execute(
                    "INSERT INTO public_market_import VALUES(?,?,?,?)",
                    (digest, url, cutoff.isoformat(), changes),
                )
                print("futures", processed)
                continue
            table, columns = TABLES[urlsplit(url).netloc]
            rows = list(observations(url, doc, cutoff))
            before = db.total_changes
            db.executemany(
                f"INSERT INTO {table} ({columns}) VALUES ({','.join('?' for _ in columns.split(','))}) ON CONFLICT DO NOTHING",
                rows,
            )
            added = db.total_changes - before
            db.execute(
                "INSERT OR IGNORE INTO public_market_import VALUES(?,?,?,?)",
                (digest, url, cutoff.isoformat(), added),
            )
            print(table, added)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument(
        "--cutoff", type=date.fromisoformat, required=True, help="첫 미완료 UTC 일자"
    )
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / "data/project.db"
    cutoff = min(
        args.cutoff,
        datetime.fromtimestamp(args.snapshot.stat().st_mtime, timezone.utc).date(),
        datetime.now(timezone.utc).date(),
    )
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as db:
        restore(db, args.snapshot, cutoff)
