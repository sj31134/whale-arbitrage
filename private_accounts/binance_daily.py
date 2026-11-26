"""Import public Binance daily market data. No portfolio inputs or credentials."""

import argparse
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from agents import analyst_feeds
from agents.equities import daily_bars
from private_accounts import live_valuation, price_history

BASES = sorted(daily_bars.BSTOCKS | {"BTC", "ETH"})


def ingest(package, market_db, base, url, rows, now):
    if url != daily_bars.binance_url(base):
        raise ValueError("원천 URL과 거래쌍 불일치")
    observations = list(daily_bars.binance_daily(rows, now))
    if not observations:
        raise ValueError("완료 거래일 자료 없음")
    stamp = now.isoformat()
    with live_valuation.connection(package, write=True) as db:
        price_history.install(db)
        pair = base + "USDT"
        price_history.persist_activity(db, pair, url, observations, stamp)
        if base in daily_bars.BSTOCKS:
            key = ("BINANCE_B", base, "USDT")
            price_history.persist(db, key, url, [bar for bar, _ in observations], stamp)
            db.execute(
                """INSERT OR IGNORE INTO bar_job(venue,symbol,currency,feed,due,success,status)
                VALUES(?,?,?,?,?,?,'수집 완료')""",
                (*key, pair, stamp, stamp),
            )
    if base in ("BTC", "ETH"):
        with closing(
            sqlite3.connect(market_db.as_uri() + "?mode=rw", uri=True)
        ) as db, db:
            db.executemany(
                """INSERT INTO binance_spot_daily(symbol,date,open,high,low,close,volume,quote_volume)
                VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(symbol,date) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low, close=excluded.close,
                volume=excluded.volume, quote_volume=excluded.quote_volume""",
                [(pair, *bar, *activity[:2]) for bar, activity in observations],
            )
            # The legacy weekly key is the Sunday ending a full UTC trading week.
            db.execute(
                """WITH daily AS (
                    SELECT *,date(date,'weekday 0') AS week_end FROM binance_spot_daily WHERE symbol=?),
                weeks AS (SELECT week_end,max(high) high,min(low) low,sum(volume) volume,
                    sum(quote_volume) quote_volume FROM daily GROUP BY week_end
                    HAVING count(*)=7 AND count(open)=7 AND count(close)=7 AND count(high)=7
                    AND count(low)=7 AND count(volume)=7 AND count(quote_volume)=7)
                INSERT OR IGNORE INTO binance_spot_weekly(symbol,date,open,high,low,close,volume,quote_volume)
                SELECT ?,w.week_end,first.open,w.high,w.low,last.close,w.volume,w.quote_volume
                FROM weeks w JOIN daily first ON first.date=date(w.week_end,'-6 days')
                JOIN daily last ON last.date=w.week_end""",
                (pair, pair),
            )
    return len(observations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, help="공개 API 원문 JSON 재실행")
    args = parser.parse_args()
    package = Path(__file__).resolve().parent
    market_db = package.parent / "data" / "project.db"
    snapshot = json.loads(args.snapshot.read_bytes()) if args.snapshot else None
    now = datetime.now(timezone.utc)
    if args.snapshot:
        # A snapshot cannot certify a candle which was open when captured.
        now = min(
            now, datetime.fromtimestamp(args.snapshot.stat().st_mtime, timezone.utc)
        )
    count = 0
    failures = []
    for base in BASES:
        try:
            url = daily_bars.binance_url(base)
            if snapshot is None:
                rows = json.loads(analyst_feeds.fetch(dict(kind="quotes", url=url)))
            else:
                url, rows = snapshot[base]["url"], snapshot[base]["rows"]
                # Raw API exports contain the current candle. Never promote it on replay.
                rows = rows[:-1]
            count += ingest(package, market_db, base, url, rows, now)
        except (
            OSError,
            ValueError,
            LookupError,
            TypeError,
            ArithmeticError,
            sqlite3.Error,
        ) as err:
            failures.append((base, type(err).__name__))
    print(
        json.dumps(
            dict(
                markets=len(BASES) - len(failures),
                completed_rows=count,
                failures=failures,
            )
        )
    )
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
