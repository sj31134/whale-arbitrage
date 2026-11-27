from datetime import date, timedelta
import gzip
import hashlib
import json
import sqlite3

import pytest

from agents import intelligence
from private_accounts import quant, strategy_page as page, strategy_registry as reg
from private_accounts.strategy_catalog import Q3
from agents.equities import cash_review


def test_price_warning_uses_prior_closes_and_next_open(package):
    bars = [dict(open=100, close=100) for _ in range(61)]
    bars.extend([dict(open=100, close=95), dict(open=95, close=89),
                 dict(open=70, close=100), dict(open=100, close=110)])
    closes = [b["close"] for b in bars]
    assert not cash_review.risk_at(closes, 61)
    assert cash_review.risk_at(closes, 62)
    result = cash_review.replay(bars, "NYSE", "trend", window=4)
    fee = quant.costs("NYSE")
    assert result["net"] == pytest.approx(70 * (1-fee.side(True, 1)) / (100*(1+fee.side(False, 1))) - 1)
    assert (result["signals"], result["matured"]) == (1, 0)
    assert cash_review.local_watch(package, [])["rows"] == []
    make_panel(package)
    watch = cash_review.local_watch(package, [dict(marks=[dict(instrument=("NYSE", "DEMO", "USD"))])])
    assert watch["rows"][0]["status"] == "가격 경보 조건 미충족"


@pytest.fixture
def package(tmp_path):
    pkg = tmp_path / "private_accounts"
    folder = pkg / ".local"
    pkg.mkdir()
    folder.mkdir(mode=0o700)
    return pkg


def make_panel(pkg):
    folder = pkg / ".local/equity_screens"
    folder.mkdir()
    stamp = "20261124T090000"
    intelligence.update_json(
        pkg, "equity_screen_index.json", {}, lambda _: dict(run=stamp)
    )
    dates = [(date(2024, 1, 1) + timedelta(days=i)).isoformat() for i in range(350)]
    key = ("NYSE", "DEMO", "USD")
    input_data = dict(
        key=key,
        source="https://example.org/public",
        sessions=dates,
        rows=[
            dict(
                day=d,
                opening=str(10 + 0.01 * i),
                closing=str(10 + 0.01 * i),
                revisions=0,
            )
            for i, d in enumerate(dates)
        ],
    )
    data = json.dumps(input_data).encode()
    with sqlite3.connect(folder / (stamp + ".sqlite3")) as db:
        db.execute("CREATE TABLE result(venue,symbol,currency,digest,inputs,detail)")
        db.execute(
            "INSERT INTO result VALUES(?,?,?,?,?,?)",
            (
                *key,
                hashlib.sha256(data).hexdigest(),
                gzip.compress(data),
                '{"actions":[]}',
            ),
        )
        db.execute("CREATE TABLE metadata(payload)")
        db.execute(
            "INSERT INTO metadata VALUES(?)",
            (
                json.dumps(
                    dict(
                        days={"US": dates[-1], "KR": dates[-1]},
                        actions_source="public",
                        cutoff="2026-11-24T00:00:00+00:00",
                    )
                ),
            ),
        )
    with sqlite3.connect(folder / (stamp + "-validation.sqlite3")) as db:
        db.execute("CREATE TABLE listing_class(venue,symbol,currency,kind)")
        db.execute(
            "INSERT INTO listing_class VALUES(?,?,?,?)", (*key, "보통주 명칭 확인")
        )
        db.execute(
            "CREATE TABLE assessment(experiment,venue,symbol,currency,price_check)"
        )
        db.execute(
            "INSERT INTO assessment VALUES(?,?,?,?,?)", ("primary", *key, "confirmed")
        )
    return key


def test_disclosure_asof_and_revision(package):
    with reg.database(package) as db:
        assert reg.evidence(db, "berkshire", "2026-11-16T16:00:03-05:00")["items"] == []
        assert reg.evidence(db, "berkshire", "2026-11-16T16:00:04-05:00")["items"] == [
            "AAPL",
            "AXP",
        ]
        assert reg.evidence(db, "household", "2026-01-24T00:00:00+00:00")["items"] == []
        stamp = "2026-11-17T00:00:00+00:00"
        event = dict(
            strategy="berkshire",
            effective="2026-09-30",
            available=stamp,
            url=Q3,
            items=["AXP"],
        )
        reg.import_event(db, event)
        reg.import_event(db, event)
        with pytest.raises(ValueError):
            reg.import_event(db, dict(event, items=["IBM"]))
        with pytest.raises(ValueError):
            reg.import_event(db, dict(event, url="https://example.org/filing"))
        assert reg.evidence(db, "berkshire", stamp)["items"] == ["AXP"]
        assert reg.evidence(db, "berkshire", "2026-11-16T23:00:00+00:00")["items"] == [
            "AAPL",
            "AXP",
        ]


def test_next_open_costs_and_strategy_warmup():
    bars = [
        dict(
            day=(date(2024, 1, 1) + timedelta(days=i)).isoformat(),
            open=100.0,
            close=100.0,
        )
        for i in range(316)
    ]
    fee = quant.Costs(100, 0, 0, 0)
    # A jump at the evaluation close cannot be captured before that close.
    bars[-63]["close"] = 200.0
    assert reg.simulate(bars, "trend-252", fee, 1)["net"] == 0
    assert reg.simulate(bars, "hold", fee, 1)["net"] == pytest.approx(1 / 1.01 - 1)
    assert reg.simulate(bars, "hold", fee, 2)["net"] == pytest.approx(1 / 1.02 - 1)
    assert reg.hold_reason({"bars": bars[-85:]}, "variance-cap") == ""
    assert reg.hold_reason({"bars": bars[-85:]}, "downside-cap") == ""
    assert reg.hold_reason({"bars": bars[-85:]}, "trend-252")
    assert reg.target("downside-cap", [100 + i for i in range(22)]) == 1.0
    assert (
        0.0
        < reg.target("variance-cap", [100, 200] * 11)
        < reg.target("downside-cap", [100, 200] * 11)
        < 1
    )


def test_run_persistence_pause_missing_inputs_and_ui(package):
    key = make_panel(package)
    first = reg.calculate(package)
    assert reg.calculate(package) == first
    with reg.database(package) as db:
        assert db.execute("select count(*) from experiment").fetchone()[0] == 4
        assert reg.summary(db, "trend-252")[0]["result"]["markets"]["US"]["n"] == 1
        reg.state(db, "trend-252", "일시정지")
    assert set(reg.calculate(package)) == {
        "trend-vote",
        "variance-cap",
        "downside-cap",
    }
    selected = page.selected_panel(package, key)
    assert "연구 일시정지" in selected and "2단계 하방 변동성캡 권장 비중" in selected
    html = page.render(package, "/unit", "token", "").decode()
    assert "전략 관리" in html and "연구 재개" in html and "기존 5~120일" in html
    assert "하방 변동성에 따른 노출 축소" in html and "4대 매크로 위기 백테스트 비교" in html
    assert "실전 시나리오 대조 복기" in html and "타당 · 유지" in html and "오류 · 보정" in html
    next((package / ".local/equity_screens").glob("*-validation.sqlite3")).unlink()
    assert reg.refresh(package) == {}
    with reg.database(package) as db:
        assert reg.summary(db, "trend-252")[0]["id"] == first["trend-252"]
        assert (
            "독립 종가" in db.execute("SELECT status FROM refresh_status").fetchone()[0]
        )


def test_frozen_member_survives_missing_classification(package):
    make_panel(package)
    baseline = reg.calculate(package)
    path = next((package / ".local/equity_screens").glob("*-validation.sqlite3"))
    with sqlite3.connect(path) as db:
        db.execute("DELETE FROM listing_class")
    current = reg.calculate(package)
    assert baseline != current
    with reg.database(package) as db:
        market = reg.summary(db, "trend-252")[0]["result"]["markets"]["US"]
        assert market["n"] == 0 and market["sampled"] == 1
        assert "고정 표본" in next(iter(market["held"]))
        assert db.execute("SELECT count(*) FROM experiment").fetchone()[0] == 8


def test_authenticated_dashboard_state(package):
    import http.client
    import re
    import threading
    from urllib.parse import urlencode, urlsplit
    from private_accounts import view

    make_panel(package)
    server, url = view.server(package.parent, port=0, package=package)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    base = urlsplit(url)
    client = http.client.HTTPConnection("127.0.0.1", server.server_port)
    try:
        client.request("GET", base.path + "/strategies")
        resp = client.getresponse()
        assert resp.status == 200
        token = re.search(r'name="csrf" value="([^"]+)"', resp.read().decode())[1]
        path = base.path + "/desk/manager/strategy-state"
        common = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "http://" + base.netloc,
        }
        for supplied, expected in [("wrong", 403), (token, 303)]:
            body = urlencode(
                dict(strategy="trend-252", state="일시정지", csrf=supplied)
            )
            client.request("POST", path, body, common)
            resp = client.getresponse()
            assert resp.status == expected
            if expected == 303:
                assert resp.getheader("Location") == base.path + "/strategies"
            resp.read()
        with reg.database(package) as db:
            assert reg.current_state(db, "trend-252") == "일시정지"
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        t.join()
