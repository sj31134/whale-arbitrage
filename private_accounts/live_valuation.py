"""Public quote cache and strictly local mark-to-market calculations."""
import difflib
import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
from zoneinfo import ZoneInfo

from agents import intelligence, market_prices
from agents.portfolio import normalize
from . import local_sources, store

FILE = "public_quotes.sqlite3"
DDL = """
CREATE TABLE IF NOT EXISTS quote (
 venue TEXT, symbol TEXT, currency TEXT, name TEXT, english TEXT, price TEXT,
 at TEXT, session TEXT, delay TEXT, feed TEXT, page INTEGER, seen TEXT,
 PRIMARY KEY (venue,symbol,currency));
CREATE TABLE IF NOT EXISTS source (
 feed TEXT PRIMARY KEY, attempt TEXT, success TEXT, status TEXT, next_page INTEGER);
"""
UPSERT = """
INSERT INTO quote VALUES (:venue,:symbol,:currency,:name,:english,:price,:at,:session,:delay,:feed,:page,:seen)
ON CONFLICT(venue,symbol,currency) DO UPDATE SET name=excluded.name,english=excluded.english,
 price=excluded.price,at=excluded.at,session=excluded.session,delay=excluded.delay,
 feed=excluded.feed,page=excluded.page,seen=excluded.seen WHERE excluded.at>quote.at OR (excluded.at=quote.at AND excluded.seen>=quote.seen)
"""


@contextmanager
def connection(package, *, write=False, account_history=False):
    name = "account_marks.sqlite3" if account_history else FILE
    path = package / ".local" / name if package is not None else None
    if path is None or (not write and not path.exists()):
        yield None
        return
    local_sources.secure_directory(path.parent)
    if write:
        fd = os.open(path, os.O_CREAT | os.O_NOFOLLOW | os.O_RDONLY, 0o600)
        os.close(fd)
    with local_sources.open_private(path), closing(sqlite3.connect(
            path.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=5)) as con:
        con.row_factory = sqlite3.Row
        if write and not account_history:
            con.executescript(DDL)
        with con:
            con.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield con


def refresh(package, fetcher=None):
    with connection(package, write=True) as db:
        cursors = {r["feed"]: r["next_page"] for r in db.execute("SELECT * FROM source")}
    attempt = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    results = market_prices.collect(cursors, **({"fetcher": fetcher} if fetcher else {}))
    now = datetime.now(timezone.utc)
    observed = now.isoformat(timespec="milliseconds")
    with connection(package, write=True) as db:
        for feed in market_prices.LABELS:
            samples = [r for r in results if r[0] == feed]
            issues, next_page, usable = [], cursors.get(feed, 1), False
            for _, page, pages, rows, status in samples:
                received = len(rows)
                rows = [dict(r, feed=feed, page=page, seen=observed) for r in rows
                        if datetime.fromisoformat(r["at"]) <= now + timedelta(minutes=2)]
                if rows and len(rows) != received:
                    issues.append("일부 기준시각 오류")
                if rows:
                    db.executemany(UPSERT, rows)
                    from . import price_history
                    price_history.listing_openings(db, rows, market_prices.origin(feed,page))
                    usable = True
                    if status != "수집 완료":
                        issues.append(status)
                    if feed == "etf":
                        next_page = 1 if page >= pages else page + 1
                    elif pages == 1:
                        next_page = 1
                    elif page > 1:
                        next_page = 2 if page >= pages else page + 1
                    elif next_page <= 1 or next_page > pages:
                        next_page = 2
                else:
                    issues.append(status if status != "수집 완료" else "기준시각 오류")
            status = ("일부 실패 · " if usable else "") + ", ".join(dict.fromkeys(issues)) if issues else "수집 완료"
            db.execute("""INSERT INTO source VALUES (?,?,?,?,?) ON CONFLICT(feed) DO UPDATE SET
                       attempt=excluded.attempt, success=coalesce(excluded.success,source.success),
                       status=excluded.status,next_page=excluded.next_page WHERE excluded.attempt>=source.attempt""",
                       (feed, attempt, observed if usable else None, status, next_page))
        return {r["feed"]: r["status"] for r in db.execute("SELECT feed,status FROM source")}


def refresh_token_prices(package, fetcher=None):
    from agents import analyst_feeds
    name = "kraken_x"
    stamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    try:
        raw = (fetcher or analyst_feeds.fetch)({"kind":"quotes","url":market_prices.endpoint(name)})
        quotes,_ = market_prices.parse(name,raw)
        stamp_received = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
        status = "수집 완료"
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError):
        quotes,status = [],"공개 시세 연결 실패"
    with connection(package,write=True) as db:
        db.executemany(UPSERT,[dict(r,feed=name,page=1,seen=stamp_received) for r in quotes])
        db.execute("""INSERT INTO source VALUES (?,?,?,?,1) ON CONFLICT(feed) DO UPDATE SET
                   attempt=excluded.attempt,success=coalesce(excluded.success,source.success),
                   status=excluded.status WHERE excluded.attempt>=source.attempt""",
                   (name,stamp,stamp_received if quotes else None,status))


def run_stream(package, feed, stopped):
    def save(source, rows, status):
        now = datetime.now(timezone.utc)
        at = now.isoformat(timespec="milliseconds")
        valid = [dict(row, feed=source, page=1, seen=at) for row in rows
                 if datetime.fromisoformat(row["at"]) <= now + timedelta(seconds=30)]
        if rows and not valid:
            status = "기준시각 오류"
        with connection(package, write=True) as db:
            db.executemany(UPSERT, valid)
            db.execute("""INSERT INTO source VALUES (?,?,?,?,1) ON CONFLICT(feed) DO UPDATE SET
                       attempt=excluded.attempt,success=coalesce(excluded.success,source.success),
                       status=excluded.status WHERE excluded.attempt>=source.attempt""",
                       (source, at, at if valid else None, status))
    market_prices.stream(feed, stopped, save)


class QuoteBook:
    def __init__(self, rows=(), sources=()):
        self.sources = {r["feed"]: dict(r) for r in sources}
        self.index = {}
        self.compact_names = {}
        self.rows_by_venue = {}
        self.fx = None
        self.usdt_usd = None
        self.latest_market_at = {}
        latest = {}
        versions = {}
        for record in rows:
            row = dict(record)
            identity = (row["venue"], row["symbol"], row["currency"])
            # Re-observations can correct the price without changing market time.
            at = datetime.fromisoformat(row["at"])
            received = datetime.fromisoformat(row["seen"]) if row.get("seen") else datetime.min.replace(tzinfo=timezone.utc)
            version = (at, received)
            if identity not in versions or version > versions[identity]:
                latest[identity] = row
                versions[identity] = version
        for row in latest.values():
            if row["venue"] == "fx":
                if (row["symbol"], row["currency"]) == ("USD/KRW", "KRW"):
                    self.fx = row
                elif (row["symbol"], row["currency"]) == ("USDT/USD", "USD"):
                    self.usdt_usd = row
                continue
            venue = row["venue"]
            self.rows_by_venue.setdefault(venue, []).append(row)
            if venue in ("KRX", *market_prices.AMERICA):
                when = datetime.fromisoformat(row["at"])
                self.latest_market_at[venue] = max(when, self.latest_market_at.get(venue, when))
            for key in {normalize(row[k]) for k in ("symbol", "name", "english") if row.get(k)}:
                self.index.setdefault(key, []).append(row)
            for key in {normalize(row[k]).replace(" ","") for k in ("name","english") if row.get(k)}:
                self.compact_names.setdefault(key,[]).append(row)

    def rate_for(self, target_ccy, quote_ccy):
        if (target_ccy, quote_ccy) == ("KRW", "USD"):
            return self.fx, "fx"
        if (target_ccy, quote_ccy) == ("USD", "USDT"):
            return self.usdt_usd, "usdt_usd"
        return None, None

    def match(self, provider, symbol, currency, tags=()):
        if "invalid:workbook" in tags:
            return None
        direct = {t for t in tags if t.startswith(("stock:KR:", "stock:US:", "token:XT:"))}
        if not direct and any(t.startswith("underlying:") for t in tags):
            return None
        if len(direct) > 1:
            return None
        if direct:
            kind, market, identifier = direct.pop().split(":", 2)
            venues = {"KR": {"KRX"}, "US": set(market_prices.AMERICA), "XT": {"KRAKEN_X"}}[market]
            rows = [r for r in self.index.get(normalize(identifier), []) if r["venue"] in venues
                    and normalize(r["symbol"]) == normalize(identifier) and (r["currency"] == currency
                    or (currency, r["currency"]) == ("KRW", "USD"))]
            return rows[0] if len(rows) == 1 else None
        key = normalize(symbol)
        prefix = key[:3] if key.startswith(("us-", "kr-")) and provider not in store.CRYPTO else ""
        rows = self.index.get(key[len(prefix):], [])
        if not rows and provider not in store.CRYPTO:
            rows = self.compact_names.get(key[len(prefix):].replace(" ",""),[])
        venues = {provider} if provider in store.CRYPTO else {*market_prices.AMERICA, "KRX"}
        if prefix:
            venues &= {"KRX"} if prefix == "kr-" else set(market_prices.AMERICA)
        eligible = [r for r in rows if r["venue"] in venues and
                    (r["currency"] == currency or (currency, r["currency"]) == ("KRW", "USD")
                     or (r["venue"] == "binance" and (currency, r["currency"]) == ("USD", "USDT")))]
        return eligible[0] if len(eligible) == 1 else None


def suggest_identifiers(book, provider, symbol, currency):
    """Return read-only candidate stock:KR / stock:US tags for unmatched broker rows."""
    if book is None or provider in store.CRYPTO or symbol.upper() == currency:
        return []
    target = normalize(symbol).replace(" ", "")
    if len(target) < 2:
        return []
    venues = ("KRX", *market_prices.AMERICA)
    scored = []
    for venue in venues:
        prefix = "stock:KR:" if venue == "KRX" else "stock:US:"
        for r in book.rows_by_venue.get(venue, ()):
            if not (r["currency"] == currency or (currency, r["currency"]) == ("KRW", "USD")):
                continue
            for label in (r.get("name") or "", r.get("english") or ""):
                cand = normalize(label).replace(" ", "")
                if not cand:
                    continue
                ratio = difflib.SequenceMatcher(None, target, cand).ratio()
                if ratio >= 0.86:
                    scored.append((ratio, prefix + r["symbol"], r.get("name") or r["symbol"]))
                    break
    scored.sort(key=lambda x: (-x[0], x[1]))
    seen = set()
    out = []
    for _, tag, label in scored:
        if tag not in seen:
            seen.add(tag)
            out.append((tag, label))
        if len(out) == 3:
            break
    return out


def read(package):
    with connection(package) as db:
        rows = list(db.execute("SELECT * FROM quote")) if db is not None else []
        sources = list(db.execute("SELECT * FROM source")) if db is not None else []
    captures = intelligence.private_json(package, intelligence.CAPTURE_FILE, {})
    for source in ("upbit", "upbit_sample", "FX_USDKRW"):
        for item in captures.get(source, {}).get("items", []):
            is_fx = source == "FX_USDKRW"
            value = item["value"].split()[0].replace(",", "")
            rows.append(dict(venue="fx" if is_fx else "upbit", symbol="USD/KRW" if is_fx else item["title"],
                             name="", english="", currency="KRW", price=value, at=item["as_of"], session="",
                             feed="fx" if is_fx else source, page=1, delay="", seen=captures[source].get("collected"), manual=True))
    book = QuoteBook(rows, sources)
    book.tags = intelligence.private_json(package, intelligence.NOTES, {}).get("tags", {})
    return book


def mark_account(book, provider, rows, pnl, balance_at, account=None, identifiers=None):
    # Multiple workbook lots share one market price; costs stay in their original valuation currency.
    groups = {}
    with localcontext() as ctx:
        ctx.prec = 100
        for symbol, currency, quantity, value, *_ in rows:
            key = (symbol, currency)
            qty, baseline = groups.get(key, (Decimal(0), Decimal(0)))
            groups[key] = (qty + Decimal(quantity),
                           baseline + Decimal(value) if baseline is not None and value is not None else None)
        marked = []
        for (symbol, currency), (qty, baseline) in sorted(groups.items()):
            if not qty:
                continue
            pid = intelligence.position_id(provider, account, symbol, currency) if account else None
            direct = set(getattr(book,"tags",{}).get(pid,()))
            direct.update((identifiers or {}).get((symbol,currency),()))
            quote = book.match(provider, symbol, currency, direct)
            value, gain = baseline, pnl.get((symbol, currency))
            cost = baseline - gain if baseline is not None and gain is not None else None
            state, price, at, fx_at = "시세 미연결", None, None, None
            fx_row, fx_feed = None, None
            if symbol.upper() == currency:
                state = "통화 잔액"
            elif provider == "binance" and (symbol.upper(), currency) == ("USDT", "USD"):
                fx_row, fx_feed = book.rate_for("USD", "USDT")
                if fx_row and datetime.fromisoformat(fx_row["at"]) >= datetime.fromisoformat(balance_at):
                    at = fx_row["at"]
                    fx_at = fx_row["at"]
                    price = Decimal(fx_row["price"])
                    value = qty * price
                    gain = value - cost if cost is not None else None
                    state = "통화 잔액 · USDT/USD 환산"
                else:
                    state = "환율 미확인"
            elif quote:
                at = quote["at"]
                price = Decimal(quote["price"])
                state = "시세 반영"
                if datetime.fromisoformat(at) < datetime.fromisoformat(balance_at):
                    price, state = None, "원장보다 이전 시세"
                elif quote["currency"] != currency:
                    fx_row, fx_feed = book.rate_for(currency, quote["currency"])
                    if fx_row and abs(datetime.fromisoformat(at) - datetime.fromisoformat(fx_row["at"])) <= timedelta(days=4):
                        price *= Decimal(fx_row["price"])
                        fx_at = fx_row["at"]
                    else:
                        price, state = None, "환율 미확인"
                if price is not None:
                    value = qty * price
                    gain = value - cost if cost is not None else None
                    if quote["session"] in ("HALT", "SUSPENDED", "TRADING_HALT"):
                        state = "거래 정지 · 마지막 시세"
                    elif quote["session"] in ("CLOSE", "CLOSED", "END"):
                        state = "종가"
                    elif (datetime.now(timezone.utc) - datetime.fromisoformat(at)).total_seconds() > 180:
                        state = "시세 지연"
                    if quote["venue"] == "KRAKEN_X":
                        state += " · Kraken 토큰 자체 가격 · 조회시각 기준"
                    if state == "종가" and quote["venue"] in book.latest_market_at:
                        zone = ZoneInfo("Asia/Seoul" if quote["venue"] == "KRX" else "America/New_York")
                        day = datetime.fromisoformat(at).astimezone(zone).date()
                        if day < book.latest_market_at[quote["venue"]].astimezone(zone).date():
                            state += " · 시장 최신 관측일보다 지연"
                        elif datetime.now(zone).date() > day:
                            state += " · 이후 개장 여부 미확인"
                    if quote.get("manual"):
                        state += " · 원문 확인분"
                    elif book.sources.get(quote["feed"], {}).get("status") != "수집 완료":
                        state += " · 저장값"
                    if fx_at and datetime.now(timezone.utc) - datetime.fromisoformat(fx_at) > timedelta(days=1):
                        state += " · 환율 최신 여부 미확인"
                    if fx_at and fx_row and fx_row.get("manual"):
                        state += " · 원문 확인 환율"
                    elif fx_at and fx_feed and book.sources.get(fx_feed, {}).get("status") != "수집 완료":
                        state += " · 저장 환율"
            marked.append(dict(symbol=symbol, currency=currency, qty=store.fixed(qty), value=value, gain=gain,
                               rate=100*gain/cost if gain is not None and cost and cost > 0 else None,
                               change=value-baseline if price is not None and baseline is not None else None,
                               price=price, at=at, fx_at=fx_at, state=state,
                               seen=quote.get("seen") if quote else None,
                               fx_seen=fx_row.get("seen") if fx_at and fx_row else None,
                               market_price=quote["price"] if quote else None, market_currency=quote["currency"] if quote else None,
                               direct_ids=tuple(t for t in direct if t.startswith(("stock:US:", "stock:KR:", "token:XT:"))),
                               instrument=(quote["venue"],quote["symbol"],quote["currency"]) if quote else None,
                               feed=quote["feed"] if quote else None, page=quote["page"] if quote else 1,
                               delay=quote["delay"] if quote else ""))
        rows = [(m["symbol"], m["currency"], m["qty"], m["value"]) for m in marked]
        for mark, holding in zip(marked, store.weighted_view(rows, balance_at)["holdings"]):
            mark["weight_pct"] = holding["weight_pct"]
        return marked
