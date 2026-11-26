"""History of completed public bars and private valuations observed on this Mac."""

import json
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import socket
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

from agents import analyst_feeds, intelligence
from agents.equities import daily_bars
from agents.portfolio import portfolio_accounts
from . import live_valuation

DDL = (
    """CREATE TABLE IF NOT EXISTS price_bar(venue TEXT, symbol TEXT, currency TEXT, source TEXT,
       day TEXT, opening TEXT NOT NULL, high TEXT NOT NULL, low TEXT NOT NULL, closing TEXT NOT NULL,
       seen TEXT NOT NULL, revisions INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(venue,symbol,currency,source,day)) WITHOUT ROWID""",
    """CREATE TABLE IF NOT EXISTS bar_job(venue TEXT,symbol TEXT,currency TEXT,feed TEXT, due TEXT NOT NULL,
       attempt TEXT,success TEXT,status TEXT, PRIMARY KEY(venue,symbol,currency)) WITHOUT ROWID""",
    """CREATE TABLE IF NOT EXISTS bar_source(name TEXT PRIMARY KEY,attempt TEXT,success TEXT,status TEXT)""",
    """CREATE TABLE IF NOT EXISTS session_open(venue TEXT,symbol TEXT,currency TEXT,day TEXT,opening TEXT,
       source_at TEXT,source TEXT,seen TEXT,PRIMARY KEY(venue,symbol,currency,day,source)) WITHOUT ROWID""",
    """CREATE TABLE IF NOT EXISTS session_close(venue TEXT,symbol TEXT,currency TEXT,day TEXT,closing TEXT,
       source_at TEXT,feed TEXT,seen TEXT,PRIMARY KEY(venue,symbol,currency,day)) WITHOUT ROWID""",
)
PRIVATE_DDL = (
    """CREATE TABLE IF NOT EXISTS mark_day(day TEXT,pid TEXT, currency TEXT, quantity TEXT, price TEXT,
       valuation TEXT, gain TEXT, weight TEXT, state TEXT, ledger TEXT, source_at TEXT, fx_at TEXT, observed TEXT,
       PRIMARY KEY(day,pid)) WITHOUT ROWID""",
    """CREATE TABLE IF NOT EXISTS mark_run(day TEXT PRIMARY KEY, observed TEXT NOT NULL)""",
)


def install(db):
    for stmt in DDL:
        db.execute(stmt)


# Legacy chart rows retain their original provider and can be audited in place.
VENUE_BARS = "(venue!='KRX' OR source NOT LIKE 'https://fchart.stock.naver.com/%')"
REGULAR_CLOSE = """(venue!='KRX' OR feed NOT IN ('KOSPI','KOSDAQ','etf')
                   OR time(source_at,'+9 hours') BETWEEN '15:30:00' AND '15:30:59')"""


def persist(db, key, source, bars, stamp):
    if key[0] == "KRX" and source.startswith("https://fchart.stock.naver.com/"):
        key = ("KR_REFERENCE", *key[1:])
    db.executemany(
        """INSERT INTO price_bar VALUES (?,?,?,?,?,?,?,?,?,?,0)
        ON CONFLICT(venue,symbol,currency,source,day) DO UPDATE SET opening=excluded.opening,
        high=excluded.high,low=excluded.low,closing=excluded.closing,seen=excluded.seen,
        revisions=price_bar.revisions+((excluded.opening,excluded.high,excluded.low,excluded.closing)
        !=(price_bar.opening,price_bar.high,price_bar.low,price_bar.closing)) WHERE excluded.seen>price_bar.seen""",
        [(*key, source, *bar, stamp) for bar in bars],
    )


def persist_activity(db, pair, url, observations, stamp):
    db.execute("""CREATE TABLE IF NOT EXISTS binance_spot_activity(
        pair TEXT,day TEXT,volume TEXT,quote_volume TEXT,trades INTEGER,
        taker_buy_volume TEXT,taker_buy_quote TEXT,source TEXT,seen TEXT,
        PRIMARY KEY(pair,day)) WITHOUT ROWID""")
    db.executemany("""INSERT INTO binance_spot_activity VALUES (?,?,?,?,?,?,?,?,?)
        ON CONFLICT(pair,day) DO UPDATE SET volume=excluded.volume,
        quote_volume=excluded.quote_volume,trades=excluded.trades,
        taker_buy_volume=excluded.taker_buy_volume,taker_buy_quote=excluded.taker_buy_quote,
        source=excluded.source,seen=excluded.seen WHERE excluded.seen>=binance_spot_activity.seen""",
        [(pair, bar[0], *activity, url, stamp) for bar, activity in observations])


def snapshots(directory, package, now=None):
    now = now or datetime.now(timezone.utc)
    stamp = now.astimezone(timezone.utc).isoformat()
    day = now.astimezone(intelligence.KST).date().isoformat()
    book = live_valuation.read(package)
    accounts = portfolio_accounts(directory, package, quote_book=book)
    rows = []
    for a in accounts:
        for m in a["marks"]:
            pid = intelligence.position_id(
                a["provider"], a["account"], m["symbol"], m["currency"]
            )
            vals = [
                m[k]
                for k in (
                    "currency",
                    "qty",
                    "price",
                    "value",
                    "gain",
                    "weight_pct",
                    "state",
                )
            ]
            rows.append(
                (
                    day,
                    pid,
                    *(str(v) if v is not None else None for v in vals),
                    a["as_of"],
                    m["at"],
                    m["fx_at"],
                    stamp,
                )
            )
    with live_valuation.connection(package, write=True, account_history=True) as db:
        for stmt in PRIVATE_DDL:
            db.execute(stmt)
        old = db.execute("SELECT observed FROM mark_run WHERE day=?", (day,)).fetchone()
        if not accounts or (old and old[0] >= stamp):
            return
        db.execute("DELETE FROM mark_day WHERE day=?", (day,))
        db.executemany("INSERT INTO mark_day VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        db.execute("INSERT OR REPLACE INTO mark_run VALUES (?,?)", (day, stamp))


def capture_closes(db):
    # The running quote feed can report a genuine close even during an OHLC API outage.
    quotes = db.execute("""SELECT venue,symbol,currency,price,at,feed,seen FROM quote
        WHERE venue IN ('KRX','NASDAQ','NYSE','AMEX') AND session IN ('CLOSE','CLOSED','END')""")
    batch = []
    for r in quotes:
        tz = ZoneInfo("Asia/Seoul" if r["venue"] == "KRX" else "America/New_York")
        local = datetime.fromisoformat(r["at"]).astimezone(tz)
        day = local.date().isoformat()
        venue = r["venue"]
        if (venue == "KRX" and r["feed"] in ("KOSPI", "KOSDAQ", "etf")
                and (local.hour, local.minute) != (15, 30)):
            venue = "KR_REFERENCE"
        batch.append(
            (
                venue,
                r["symbol"],
                r["currency"],
                day,
                r["price"],
                r["at"],
                r["feed"],
                r["seen"],
            )
        )
    db.executemany(
        """INSERT INTO session_close VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(venue,symbol,currency,day)
        DO UPDATE SET closing=excluded.closing,source_at=excluded.source_at,feed=excluded.feed,seen=excluded.seen
        WHERE (excluded.source_at,excluded.seen)>(session_close.source_at,session_close.seen)""",
        batch,
    )


def refresh(package, fetcher=analyst_feeds.fetch, *, limit=24, now=None):
    now = now or datetime.now(timezone.utc)
    stamp = now.isoformat()
    lease = (now + timedelta(minutes=10)).isoformat()
    with live_valuation.connection(package, write=True) as db:
        install(db)
        capture_closes(db)
        db.execute("""INSERT OR IGNORE INTO bar_job(venue,symbol,currency,feed,due)
            SELECT venue,symbol,currency,feed,'' FROM quote WHERE venue IN ('KRX','NASDAQ','NYSE','AMEX')""")
        prev = db.execute(
            "SELECT attempt FROM bar_source WHERE name='kraken_pairs'"
        ).fetchone()
        discover = (
            not prev or datetime.fromisoformat(prev[0]) + timedelta(hours=1) <= now
        )
        if discover:
            db.execute(
                "INSERT INTO bar_source VALUES ('kraken_pairs',?,NULL,'조회 중') ON CONFLICT(name) DO UPDATE SET attempt=excluded.attempt,status=excluded.status",
                (stamp,),
            )
    if discover:
        try:
            pairs = daily_bars.token_listing(
                fetcher(dict(kind="quotes", url=daily_bars.PAIRS))
            )
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            pairs = {}
        with live_valuation.connection(package, write=True) as db:
            db.executemany(
                "INSERT OR IGNORE INTO bar_job(venue,symbol,currency,feed,due) VALUES ('KRAKEN_X',?,'USD',?,'')",
                pairs.items(),
            )
            db.execute(
                "UPDATE bar_source SET status=?,success=coalesce(?,success) WHERE name='kraken_pairs' AND attempt=?",
                (
                    "수집 완료" if pairs else "공개 목록 수집 실패",
                    stamp if pairs else None,
                    stamp,
                ),
            )
    with live_valuation.connection(package, write=True) as db:
        jobs = [
            tuple(r)
            for r in db.execute(
                """SELECT venue,symbol,currency,feed FROM
          (SELECT *,row_number() over (partition by venue order by due,symbol) priority FROM bar_job WHERE due<=?)
          ORDER BY priority,venue LIMIT ?""",
                (stamp, limit),
            )
        ]
        db.executemany(
            "UPDATE bar_job SET attempt=?,due=? WHERE (venue,symbol,currency)=(?,?,?)",
            [(stamp, lease, *j[:3]) for j in jobs],
        )

        kr_day = now.astimezone(intelligence.KST).date().isoformat()
        closes = {
            r["symbol"]: r["closing"]
            for r in db.execute(
                "SELECT symbol,closing FROM session_close WHERE venue='KR_REFERENCE' AND day=?",
                (kr_day,),
            )
        }

    def collect_regular(job):
        try:
            url = daily_bars.endpoint(job)
            raw = fetcher(dict(kind="quotes", url=url))
            activity = []
            if job[0] == "BINANCE_B":
                activity = list(daily_bars.binance_daily(json.loads(raw), now))
                bars = [bar for bar, _ in activity]
            else:
                bars = daily_bars.read_bars(job, raw, now)
            return url, bars, "수집 완료" if bars else "완료 거래일 자료 없음", activity
        except HTTPError as err:
            return "", [], f"HTTP {err.code}", []
        except URLError as err:
            return (
                "",
                [],
                "DNS 실패"
                if isinstance(err.reason, socket.gaierror)
                else "원천 연결 실패",
                [],
            )
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            OverflowError,
            ArithmeticError,
        ):
            return "", [], "연결·원문 확인 실패", []

    def collect(job):
        primary = collect_regular(job)
        if job[0] != "KRX" or primary[1]:
            return primary
        try:
            url = daily_bars.naver_endpoint(job[1])
            bars = daily_bars.naver_bars(fetcher(dict(kind="quotes", url=url)),
                                        job[1], now, closes.get(job[1]))
            if bars:
                return url, bars, primary[2] + " · 거래장 미확정 참고 이력 저장", []
        except (OSError, ValueError, TypeError, KeyError):
            pass
        return primary

    with ThreadPoolExecutor(max_workers=3) as pool:
        for job, (source, bars, status, activity) in zip(jobs, pool.map(collect, jobs)):
            with live_valuation.connection(package, write=True) as db:
                if activity:
                    persist_activity(db, job[3], source, activity, stamp)
                if bars:
                    persist(db, job[:3], source, bars, stamp)
                regular_ok = bool(bars) and not (job[0] == "KRX" and source.startswith("https://fchart.stock.naver.com/"))
                retry = now + timedelta(hours=6 if regular_ok else 2)
                db.execute(
                    """UPDATE bar_job SET due=?,success=coalesce(?,success),status=?
                           WHERE (venue,symbol,currency)=(?,?,?) AND attempt=?""",
                    (
                        retry.isoformat(),
                        stamp if regular_ok else None,
                        status,
                        *job[:3],
                        stamp,
                    ),
                )


def local_history_key(db, provider, mark):
    symbol = mark.get("symbol", "").strip().upper()
    direct = set(mark.get("direct_ids", ()))
    token = next(iter(direct), "")
    if len(direct) == 1 and token.startswith("token:XT:"):
        code = token.split(":", 2)[2].upper()
        if code in daily_bars.BSTOCKS:
            return ("BINANCE_B", code, "USDT")
    if not direct and provider == "binance" and symbol in daily_bars.BSTOCKS:
        return ("BINANCE_B", symbol, "USDT")
    if mark.get("instrument"):
        return mark["instrument"]
    if db is None:
        return None
    symbols = set(mark.get("direct_ids", ()))
    if len(symbols) > 1:
        return None
    if symbols:
        _, market, symbol = symbols.pop().split(":", 2)
    else:
        from . import store

        if provider not in store.BROKERS:
            return None
        symbol = mark["symbol"].strip().upper()
        market = ""
        if symbol.startswith(("US-", "KR-")):
            market, symbol = symbol.split("-", 1)
    venues = {
        "US": daily_bars.US,
        "KR": ("KRX",),
        "XT": ("KRAKEN_X",),
        "": ("KRX", *daily_bars.US),
    }[market]
    currencies = ("KRW", "USD") if mark["currency"] == "KRW" else (mark["currency"],)
    found = []
    for venue in venues:
        for ccy in currencies:
            key = (venue, symbol.upper(), ccy)
            if db.execute(
                "SELECT 1 FROM price_bar WHERE (venue,symbol,currency)=(?,?,?) LIMIT 1",
                key,
            ).fetchone():
                found.append(key)
    return found[0] if len(found) == 1 else None


def series(db, key, *, long=False):
    if (
        db is None
        or not db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='price_bar'"
        ).fetchone()
    ):
        return [], None
    where = "venue=? AND symbol=? AND currency=? AND " + VENUE_BARS
    choices = db.execute(
        f"SELECT source,max(day) AS last,count(*) AS n FROM price_bar WHERE {where} GROUP BY source ORDER BY last DESC,n DESC,source",
        key,
    ).fetchall()
    pick = next(iter(choices), None)
    if long and pick:
        cutoff = date.fromisoformat(pick["last"]) - timedelta(days=7)
        pick = max(
            (r for r in choices if date.fromisoformat(r["last"]) >= cutoff),
            key=lambda r: (r["n"], r["last"]),
        )
    if not pick:
        return [], None
    return list(
        db.execute(
            f"SELECT * FROM price_bar WHERE {where} AND source=? ORDER BY day",
            (*key, pick[0]),
        )
    ), pick[0]


def known_sessions(db, venue):
    if venue in ("KRAKEN_X", "BINANCE_B"):
        return set()
    benchmark = (
        [("KRX", "069500", "KRW"), ("KRX", "005930", "KRW")]
        if venue == "KRX"
        else [
            ("AMEX", "SPY", "USD"),
            ("NASDAQ", "MSFT", "USD"),
            ("NASDAQ", "AAPL", "USD"),
        ]
    )
    return {
        r[0]
        for key in benchmark
        for r in db.execute(
            "SELECT DISTINCT day FROM price_bar WHERE venue=? AND symbol=? AND currency=? AND " + VENUE_BARS,
            key,
        )
    }


def moving_average(rows, missing=()):
    closes = [Decimal(row["closing"]) for row in rows]
    total = Decimal(0)
    missing = sorted(missing)
    result = {}
    for i, (r, v) in enumerate(zip(rows, closes)):
        total += v
        if i >= 120:
            total -= closes[i - 120]
        if i < 119:
            continue
        start, end = rows[i - 119]["day"], r["day"]
        if (
            bisect_right(missing, start) == bisect_right(missing, end)
            and (date.fromisoformat(end) - date.fromisoformat(start)).days <= 200
        ):
            result[end] = total / 120
    return result


def summaries(rows, missing=()):
    if not rows:
        return {}
    days = [date.fromisoformat(r["day"]) for r in rows]
    close = [Decimal(r["closing"]) for r in rows]
    last = days[-1]
    missing = sorted(missing)

    def against(target):
        idx = bisect_right(days, target) - 1
        if (
            idx >= 0
            and (target - days[idx]).days <= 7
            and bisect_right(missing, days[idx].isoformat())
            == bisect_right(missing, target.isoformat())
        ):
            return (close[-1] / close[idx] - 1) * 100

    try:
        year = last.replace(year=last.year - 1)
    except ValueError:
        year = date(last.year - 1, 2, 28)
    prior_month = last.replace(day=1) - timedelta(days=1)
    month = prior_month.replace(day=min(prior_month.day, last.day))
    ma = moving_average(rows[-120:], missing).get(rows[-1]["day"])
    return dict(
        day=(close[-1] / close[-2] - 1) * 100
        if len(close) > 1
        and (last - days[-2]).days <= 8
        and bisect_right(missing, rows[-2]["day"])
        == bisect_right(missing, rows[-1]["day"])
        else None,
        week=against(last - timedelta(days=7)),
        month=against(month),
        year=against(year),
        ma=ma,
    )


def aggregate(rows, mode):
    groups = {}
    for r in rows:
        d = date.fromisoformat(r["day"])
        key = (
            d.isocalendar()[:2]
            if mode == "week"
            else (d.year, d.month)
            if mode == "month"
            else d
        )
        if key not in groups:
            groups[key] = dict(
                first=r["day"],
                day=r["day"],
                opening=Decimal(r["opening"]),
                closing=Decimal(r["closing"]),
            )
        groups[key].update(day=r["day"], closing=Decimal(r["closing"]))
    return list(groups.values())


def kr_public_symbols():
    from agents import market_anomalies, market_prices

    return {
        s.removesuffix(".KS")
        for s in (
            *market_anomalies.STOCKS["KR"],
            *market_anomalies.SECTORS["KR"],
            *market_prices.ETF_SAMPLE,
        )
    }


def save_openings(db, rows):
    db.executemany(
        """INSERT INTO session_open VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(venue,symbol,currency,day,source)
                  DO UPDATE SET opening=excluded.opening,source_at=excluded.source_at,seen=excluded.seen
                  WHERE (excluded.source_at,excluded.seen)>(session_open.source_at,session_open.seen)""",
        rows,
    )


def listing_openings(db, rows, source):
    available = []
    for row in rows:
        if row.get("opening"):
            local = ZoneInfo(
                "Asia/Seoul" if row["venue"] == "KRX" else "America/New_York"
            )
            day = datetime.fromisoformat(row["at"]).astimezone(local).date().isoformat()
            venue = row["venue"]
            if venue == "KRX" and source.startswith("https://m.stock.naver.com/api/stocks/marketValue/"):
                venue = "KR_REFERENCE"
            available.append(
                (
                    venue,
                    row["symbol"],
                    row["currency"],
                    day,
                    row["opening"],
                    row["at"],
                    source,
                    row["seen"],
                )
            )
    if available:
        install(db)
        save_openings(db, available)


def record_opens(package, raw, stamp):
    checked = datetime.fromisoformat(stamp)
    if (
        checked.tzinfo is None
        or checked > datetime.now(timezone.utc) + timedelta(minutes=2)
        or not isinstance(raw, list)
    ):
        raise ValueError("공개 시가 확인 시각 오류")
    rows = []
    for item in raw:
        fields = {"venue", "symbol", "currency", "day", "opening", "observed", "url"}
        if (
            not isinstance(item, dict)
            or set(item) != fields
            or not all(isinstance(v, str) for v in item.values())
        ):
            raise ValueError("공개 시가 입력 필드를 확인하세요.")
        venue, symbol, ccy = item["venue"], item["symbol"], item["currency"]
        url = item["url"]
        if (
            venue != "KRX"
            or ccy != "KRW"
            or symbol not in kr_public_symbols()
            or url != f"https://stockanalysis.com/quote/krx/{symbol}/history/"
        ):
            raise ValueError("국내 공개 시가 원천 불일치")
        observed = datetime.fromisoformat(item["observed"])
        if (
            observed.tzinfo is None
            or observed > checked
            or observed.astimezone(intelligence.KST).date().isoformat() != item["day"]
        ):
            raise ValueError("시가와 원천 거래일 불일치")
        rows.append(
            (
                venue,
                symbol,
                ccy,
                item["day"],
                daily_bars.price(item["opening"]),
                observed.astimezone(timezone.utc).isoformat(),
                url,
                checked.astimezone(timezone.utc).isoformat(),
            )
        )
    with live_valuation.connection(package, write=True) as db:
        install(db)
        save_openings(db, rows)
    return len(rows)


def import_public(raw, stamp, *, naver_symbols=()):
    """Validate independently checked pages from the project's pre-existing public market universe."""
    from agents import market_anomalies

    if not isinstance(raw, list) or not raw:
        raise ValueError("공개 일봉 목록을 확인하세요.")
    checked = datetime.fromisoformat(stamp)
    if checked.tzinfo is None or checked > datetime.now(timezone.utc) + timedelta(
        minutes=2
    ):
        raise ValueError("확인 시각 오류")
    us_checked = checked.astimezone(ZoneInfo("America/New_York"))
    captured = []
    for entry in raw:
        fields = {"venue", "symbol", "currency", "url", "rows"}
        if (
            not isinstance(entry, dict)
            or set(entry) not in (fields, fields | {"published_close_at"})
            or not all(isinstance(entry[k], str) for k in fields - {"rows"})
        ):
            raise ValueError("공개 일봉 입력 필드를 확인하세요.")
        venue, symbol, currency, url = (
            entry[k] for k in ("venue", "symbol", "currency", "url")
        )
        if url.startswith("https://pubmarks.github.io/"):
            nasdaq = {
                "AAPL",
                "ADBE",
                "GOOG",
                "INTU",
                "LRCX",
                "META",
                "MSFT",
                "NFLX",
                "NVDA",
                "TSLA",
            }
            nyse = {"ACN", "CRM", "DELL", "RMD", "SAP", "TSM", "UBER"}
            expected = f"https://pubmarks.github.io/datasets/stocks/{symbol}/ohlcv.csv"
            valid = currency == "USD" and (
                (venue == "NASDAQ" and symbol in nasdaq)
                or (venue == "NYSE" and symbol in nyse)
            )
        elif venue == "KRX" and url.startswith("https://fchart.stock.naver.com/"):
            expected = daily_bars.naver_endpoint(symbol)
            valid = currency == "KRW" and symbol in naver_symbols
        elif venue == "KRX":
            pool = kr_public_symbols()
            expected = "https://stockanalysis.com/quote/krx/" + symbol + "/history/"
            valid = currency == "KRW" and symbol in pool
        elif symbol in market_anomalies.STOCKS["US"]:
            expected = (
                "https://stockanalysis.com/stocks/" + symbol.lower() + "/history/"
            )
            valid = currency == "USD" and venue == (
                "NYSE" if symbol == "JPM" else "NASDAQ"
            )
        else:
            expected = "https://stockanalysis.com/etf/" + symbol.lower() + "/history/"
            valid = (
                currency == "USD"
                and symbol in {"SPY", *market_anomalies.SECTORS["US"]}
                and venue == ("NASDAQ" if symbol == "SOXX" else "AMEX")
            )
        if (
            not valid
            or expected != url
            or not isinstance(entry["rows"], list)
            or len(entry["rows"]) > 1000
        ):
            raise ValueError("고정 공개 원천 불일치")
        bars = []
        for item in entry["rows"]:
            if (
                not isinstance(item, list)
                or len(item) != 5
                or not all(isinstance(v, str) and len(v) <= 50 for v in item)
            ):
                raise ValueError("거래일과 네 가격의 형식을 확인하세요.")
            day = date.fromisoformat(item[0])
            local_now = (
                checked.astimezone(intelligence.KST) if venue == "KRX" else us_checked
            )
            if day > local_now.date():
                raise ValueError("완료 거래일을 확인하세요.")
            bars.append(daily_bars.candle(day, item[1:]))
        if len({r[0] for r in bars}) != len(bars):
            raise ValueError("원천 내 거래일 중복")
        captured.append(((venue, symbol, currency), url, bars))
    return captured


def record_public(package, raw, stamp):
    naver_symbols = set()
    if isinstance(raw, list) and any(isinstance(e, dict) and isinstance(e.get("url"), str)
                                    and e["url"].startswith("https://fchart.stock.naver.com/") for e in raw):
        with live_valuation.connection(package) as db:
            if db and db.execute("SELECT 1 FROM sqlite_master WHERE name='bar_job'").fetchone():
                naver_symbols = {s for (s,) in db.execute(
                    "SELECT symbol FROM bar_job WHERE venue='KRX' AND currency='KRW'")}
    batches = import_public(raw, stamp, naver_symbols=naver_symbols)
    with live_valuation.connection(package, write=True) as db:
        install(db)
        checked = datetime.fromisoformat(stamp)
        for entry, (key, source, bars) in zip(raw, batches):
            zone = intelligence.KST if key[0] == "KRX" else ZoneInfo("America/New_York")
            today = checked.astimezone(zone).date().isoformat()
            for day, _, _, _, close in bars:
                if day == today:
                    if not isinstance(entry.get("published_close_at"), str):
                        raise ValueError("완료 일봉 원문 게시 시각을 확인하세요.")
                    try:
                        published = datetime.fromisoformat(entry["published_close_at"])
                    except ValueError:
                        raise ValueError(
                            "완료 일봉 원문 게시 시각을 확인하세요."
                        ) from None
                    if (
                        published.tzinfo is None
                        or published > checked
                        or published.astimezone(zone).date().isoformat() != day
                    ):
                        raise ValueError("완료 일봉 원문 게시 시각을 확인하세요.")
                    if key[0] == "KRX" and source.startswith("https://fchart.stock.naver.com/"):
                        comparable = "venue IN ('KRX','KR_REFERENCE')"
                        args = (*key[1:], day)
                    else:
                        comparable = "venue=? AND " + REGULAR_CLOSE
                        args = (*key, day)
                    settled = db.execute(
                        "SELECT closing,source_at FROM session_close WHERE " + comparable
                        + " AND (symbol,currency,day)=(?,?,?) AND julianday(source_at)<=julianday(?)"
                          " ORDER BY julianday(source_at) DESC LIMIT 1", (*args, published.isoformat()),
                    ).fetchone()
                    if (not settled or datetime.fromisoformat(settled[1]) > published
                            or Decimal(settled[0]) != Decimal(close)):
                        raise ValueError("현지 당일 시장 마감 시세와 대조 대기")
            persist(
                db,
                key,
                source,
                bars,
                datetime.fromisoformat(stamp).astimezone(timezone.utc).isoformat(),
            )
    return sum(len(rows) for _, _, rows in batches)
