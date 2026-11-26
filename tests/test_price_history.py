from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import json

from agents import intelligence, market_prices
from agents.equities import daily_bars
from private_accounts import (
    history_panel,
    live_valuation as live,
    price_history as hist,
    store,
)


def stock(when):
    return dict(
        venue="NASDAQ",
        symbol="PUBLIC",
        currency="USD",
        name="공개 종목",
        english="Public",
        price="15",
        at=when.isoformat(),
        session="CLOSE",
        delay="15",
        feed="NASDAQ",
        page=1,
        seen=when.isoformat(),
    )


def test_completed_daily_bars_and_corrections(tmp_path):
    pkg = tmp_path / "p"
    pkg.mkdir()
    now = datetime(2026, 11, 23, 18, tzinfo=timezone.utc)
    with live.connection(pkg, write=True) as db:
        db.execute(live.UPSERT, stock(now - timedelta(days=3)))
    job = ("NASDAQ", "PUBLIC", "USD", "NASDAQ")
    quote = {"open": [10, 15], "low": [9, 12], "high": [15, 18], "close": [12, 16]}

    def fetch(request):
        if request["url"] == daily_bars.PAIRS:
            raise OSError
        assert request["url"] == daily_bars.endpoint(job)
        return json.dumps(
            {
                "chart": {
                    "result": [
                        {
                            "meta": {
                                "currency": "USD",
                                "dataGranularity": "1d",
                                "symbol": "PUBLIC",
                                "currentTradingPeriod": {
                                    "regular": {"end": int(now.timestamp()) + 10800}
                                },
                            },
                            "timestamp": [
                                int((now - timedelta(days=3)).timestamp()),
                                int(now.timestamp()),
                            ],
                            "indicators": {"quote": [quote]},
                        }
                    ]
                }
            }
        )

    hist.refresh(pkg, fetch, now=now)
    hist.refresh(pkg, lambda _: None, now=now + timedelta(minutes=1))
    with live.connection(pkg, write=True) as db:
        rows, source = hist.series(db, job[:3])
        assert (
            len(rows) == 1
            and rows[0]["day"] == "2026-11-20"
            and rows[0]["closing"] == "12"
        )
        assert db.execute("SELECT count(*) FROM session_close").fetchone()[0] == 1
        assert (
            db.execute("SELECT success FROM bar_job").fetchone()[0] == now.isoformat()
        )
        bar = ("2026-11-20", "10", "15", "9", "12")
        hist.persist(db, job[:3], source, [bar], (now + timedelta(hours=3)).isoformat())
        hist.persist(
            db,
            job[:3],
            source,
            [(*bar[:-1], "11")],
            (now + timedelta(hours=2)).isoformat(),
        )
        assert hist.series(db, job[:3])[0][0]["closing"] == "12"
        hist.persist(
            db,
            job[:3],
            source,
            [(*bar[:-1], "13")],
            (now + timedelta(hours=4)).isoformat(),
        )
        assert hist.series(db, job[:3])[0][0]["revisions"] == 1

    def fail(_):
        raise OSError

    hist.refresh(pkg, fail, now=now + timedelta(hours=7))
    with live.connection(pkg) as db:
        assert hist.series(db, job[:3])[0][0]["closing"] == "13"
        r = db.execute("SELECT status,success FROM bar_job").fetchone()
        assert r["status"] != "수집 완료" and r["success"] == now.isoformat()


def test_periods_and_missing_sessions():
    first = date(2025, 10, 27)
    days = [
        first + timedelta(days=i)
        for i in range(390)
        if (first + timedelta(days=i)).weekday() < 5
    ]
    rows = [
        dict(day=d.isoformat(), opening=str(i + 10), closing=str(i + 11))
        for i, d in enumerate(days)
    ]
    stats = hist.summaries(rows)
    assert (
        stats["ma"] == sum(Decimal(r["closing"]) for r in rows[-120:]) / 120
        and stats["year"] > 0
    )
    assert (
        hist.summaries(rows[-119:])["ma"] is None
        and hist.summaries(rows[-100:])["year"] is None
    )
    gap = rows[-20]["day"]
    reduced = [r for r in rows if r["day"] != gap]
    assert hist.summaries(reduced, {gap})["ma"] is None
    assert hist.summaries(reduced, {gap})["year"] == stats["year"]
    weekly = hist.aggregate(rows[:5], "week")
    assert (
        len(weekly) == 1 and weekly[0]["opening"] == 10 and weekly[0]["closing"] == 15
    )
    assert len(hist.aggregate(rows, "month")) == 14


def test_local_marks_and_private_identity(tmp_path):
    pkg, directory = tmp_path / "project", tmp_path / "accounts"
    pkg.mkdir()
    now = datetime.now(timezone.utc)
    with store.database(directory, True) as db:
        store.save(
            db,
            "kis",
            "fixture",
            (now - timedelta(days=5)).isoformat(),
            [("개인별칭", "USD", "2", "20")],
        )
    with live.connection(pkg, write=True) as db:
        db.execute(live.UPSERT, stock(now))
    pid = intelligence.position_id("kis", "fixture", "개인별칭", "USD")
    intelligence.update_json(
        pkg,
        intelligence.NOTES,
        {},
        lambda _: dict(tags={pid: ["stock:US:PUBLIC", "underlying:US:OTHER"]}),
    )
    hist.snapshots(directory, pkg, now)
    hist.snapshots(directory, pkg, now)
    with live.connection(pkg, account_history=True) as db:
        row = db.execute("SELECT * FROM mark_day").fetchone()
        assert row["pid"] == pid and row["valuation"] == "30" and row["weight"] == "100"
        assert db.execute("SELECT count(*) FROM mark_day").fetchone()[0] == 1
    from agents.portfolio import portfolio_accounts

    accounts = portfolio_accounts(directory, pkg, quote_book=live.read(pkg))
    day = (now - timedelta(days=7)).date().isoformat()
    with live.connection(pkg, write=True) as db:
        hist.install(db)
        hist.persist(
            db,
            ("NASDAQ", "PUBLIC", "USD"),
            "https://example.org/price",
            [(day, "10", "12", "9", "11")],
            now.isoformat(),
        )
        assert not db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='mark_day'"
        ).fetchone()
    page = history_panel.position_history(pkg, accounts, "/test", pid, mode="ma")
    assert (
        "개인별칭" in page
        and "계좌 일별 평가 기록" in page
        and "자료 부족" in page
        and day in page
    )


def test_token_and_korean_market_day():
    now = datetime(2026, 11, 23, 7, tzinfo=timezone.utc)
    paired = {
        "error": [],
        "result": {"TXUSD": {"wsname": "Tx/USD", "altname": "TxUSD"}},
    }
    assert daily_bars.token_listing(json.dumps(paired)) == {"TX": "TxUSD"}
    ts = int(now.timestamp()) - 86400
    raw = json.dumps(
        {
            "error": [],
            "result": {
                "TxUSD": [
                    [ts, "1", "2", "1", "2", "1.5", "100", 4],
                    [ts + 86400, "2", "9", "2", "8", "4", "50", 2],
                ],
                "last": ts,
            },
        }
    )
    assert daily_bars.read_bars(("KRAKEN_X", "TX", "USD", "TxUSD"), raw, now) == [
        ("2026-11-22", "1", "2", "1", "2")
    ]
    raw = b'<protocol><chartdata symbol="123456"><item data="20261120|1|2|1|2|10"/><item data="20261123|2|3|1|3|10"/></chartdata></protocol>'
    assert daily_bars.naver_bars(raw, "123456", now) == [
        ("2026-11-20", "1", "2", "1", "2")
    ]
    encoded = ('<?xml version="1.0" encoding="EUC-KR"?>' +
               raw.decode().replace('symbol="123456"', 'symbol="123456" name="예시"')).encode("euc-kr")
    assert daily_bars.naver_bars(encoded, "123456", now) == daily_bars.naver_bars(raw, "123456", now)
    (row,) = market_prices.parse(
        "kraken_x",
        json.dumps(
            {"error": [], "result": {"TxUSD": {"c": ["3", "1"], "v": ["1", "2"]}}}
        ),
    )[0]
    assert row["venue"] == "KRAKEN_X" and row["price"] == "3"
    book = live.QuoteBook([row])
    assert book.match("kis", "T", "USD", ["underlying:US:T"]) is None
    assert book.match("kis", "내 이름", "USD", ["token:XT:TX"]) == row


def test_public_open_is_kept_separate_until_matching_completed_candle(tmp_path):
    checked = datetime(2026, 1, 8, 7, tzinfo=timezone.utc).isoformat()
    pkg = tmp_path / "project"
    pkg.mkdir()
    day = "2026-01-08"
    key = ("KRX", "005930", "KRW")
    url = "https://stockanalysis.com/quote/krx/005930/history/"
    opening = dict(
        venue=key[0],
        symbol=key[1],
        currency=key[2],
        day=day,
        opening="10",
        observed=day + "T10:30:00+09:00",
        url=url,
    )
    assert hist.record_opens(pkg, [opening], checked) == 1
    entry = dict(
        venue=key[0],
        symbol=key[1],
        currency=key[2],
        url=url,
        rows=[[day, "10", "13", "9", "12"]],
    )
    import pytest

    with pytest.raises(ValueError):
        hist.record_public(pkg, [entry], checked)
    with live.connection(pkg, write=True) as db:
        assert not hist.series(db, key)[0]
        assert db.execute("SELECT opening FROM session_open").fetchone()[0] == "10"
        db.execute(
            "INSERT INTO session_close VALUES (?,?,?,?,?,?,?,?)",
            (*key, day, "12", day + "T06:30:00+00:00", "KOSPI", checked),
        )
    entry["published_close_at"] = day + "T15:40:00+09:00"
    assert hist.record_public(pkg, [entry], checked) == 1
    naver = dict(entry, url=daily_bars.naver_endpoint(key[1]), published_close_at=day + "T15:30:00+09:00")
    with pytest.raises(ValueError, match="고정 공개 원천"):
        hist.record_public(pkg, [naver], checked)
    with live.connection(pkg, write=True) as db:
        db.execute("INSERT INTO bar_job(venue,symbol,currency,feed,due) VALUES(?,?,?,?,?)",
                   (*key, "KOSPI", checked))
        db.execute("UPDATE session_close SET source_at=?", (day + "T06:30:00.000+00:00",))
    assert hist.record_public(pkg, [naver], checked) == 1
    with live.connection(pkg, write=True) as db:
        assert db.execute("SELECT venue FROM price_bar WHERE source=?", (naver["url"],)).fetchone()[0] == "KR_REFERENCE"
        quote = dict(stock(datetime.fromisoformat(day + "T11:00:00+00:00")), venue="KRX", symbol=key[1],
                     currency="KRW", feed="KOSPI", session="CLOSE")
        db.execute(live.UPSERT, quote)
        hist.capture_closes(db)
        assert db.execute("SELECT source_at FROM session_close WHERE venue='KRX'").fetchone()[0] == day + "T06:30:00.000+00:00"
        assert db.execute("SELECT 1 FROM session_close WHERE venue='KR_REFERENCE'").fetchone()
    with pytest.raises(ValueError, match="시세와 대조"):
        hist.record_public(pkg, [dict(naver, published_close_at=day + "T15:29:59+09:00")], checked)
