import json
import sqlite3
from datetime import datetime, timezone

import pytest

from agents.equities import daily_bars
from private_accounts import (
    binance_daily,
    history_panel,
    live_valuation,
    price_history,
    quant,
)
from private_accounts.spot_history_import import restore


def test_token_identity_and_completed_trades(tmp_path):
    day = 86400000
    rows = [
        [i * day, "2", "4", "1", "3", "10", (i + 1) * day - 1, "22", n, "2", "4", "0"]
        for i, n in enumerate([10, 0, 5])
    ]
    now = datetime.fromtimestamp(2 * day / 1000 + 10, timezone.utc)
    url = daily_bars.binance_url("NVDAB")
    key = ("BINANCE_B", "NVDAB", "USDT")
    job = (*key, "NVDABUSDT")
    assert daily_bars.endpoint(job) == url
    assert len(daily_bars.read_bars(job, json.dumps(rows), now)) == 1
    for _ in range(2):
        assert binance_daily.ingest(tmp_path, None, "NVDAB", url, rows, now) == 1
    with live_valuation.connection(tmp_path) as db:
        assert (
            db.execute("select count(*) from binance_spot_activity").fetchone()[0] == 1
        )
        assert db.execute("select count(*),max(revisions) from price_bar").fetchone()[
            :
        ] == (1, 0)
        mark = {
            "symbol": "NVDAB",
            "currency": "KRW",
            "instrument": ("Binance", "NVDAB", "USDT"),
        }
        assert history_panel.eligible("binance", mark)
        assert price_history.local_history_key(db, "binance", mark) == key
        assert price_history.known_sessions(db, key[0]) == set()
    with pytest.raises(ValueError):
        binance_daily.ingest(tmp_path, None, "TSLAB", url, rows, now)
    assert quant.costs(key[0]).side(False, 1) == 0.0025


def test_spot_fx_cutoff_and_replay(tmp_path):
    db = sqlite3.connect(":memory:")
    db.execute("create table exchange_rate(date text primary key,krw_usd real)")
    url = "https://api.frankfurter.dev/v1/2026-11-22..2026-11-24?base=USD&symbols=KRW"
    path = tmp_path / "fx.json"
    path.write_text(
        json.dumps(
            {
                url: {
                    "base": "USD",
                    "rates": {"2026-11-23": {"KRW": 1300}, "2026-11-24": {"KRW": 1400}},
                }
            }
        )
    )
    for _ in range(2):
        restore(db, path, datetime(2026, 11, 24).date())
    assert db.execute("select * from exchange_rate").fetchall() == [
        ("2026-11-23", 1300)
    ]
    assert db.execute("select inserted from public_market_import").fetchone() == (1,)


def test_derivative_currency_units_and_utc_cutoff():
    from private_accounts.spot_history_import import import_futures

    db = sqlite3.connect(":memory:")
    cutoff = datetime(1970, 1, 2).date()
    url = "https://fapi.binance.com/futures/data/openInterestHist?symbol=BTCUSDT&period=1d"
    rows = [
        dict(
            timestamp=i * 86400000,
            symbol="BTCUSDT",
            sumOpenInterest="20",
            sumOpenInterestValue="700000",
        )
        for i in range(2)
    ]
    assert import_futures(db, url, rows, cutoff) == 1
    assert db.execute(
        "select base_quantity,notional_usdt from binance_open_interest_daily"
    ).fetchall() == [("20", "700000")]
    with pytest.raises(ValueError):
        import_futures(db, url.replace("BTCUSDT", "ETHUSDT"), rows, cutoff)
