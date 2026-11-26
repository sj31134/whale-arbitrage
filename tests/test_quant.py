from datetime import date, timedelta
from decimal import Decimal
from math import sin
import json

import pytest
from private_accounts import (
    quant as q,
    quant_page,
    live_valuation,
    price_history,
    store,
    view,
)


def sample(size):
    return [
        dict(
            day=(date(2020, 1, 1) + timedelta(days=i)).isoformat(),
            opening=str(100 + 5 * sin((i - 0.5) / 2)),
            closing=str(100 + 5 * sin(i / 2)),
            revisions=0,
        )
        for i in range(size)
    ]


def test_fill_after_close_ties_pending_and_terminal_mark():
    values = list(map(Decimal, [4, 2, 2, 4, 4, 2]))
    events, _ = q.signals(values, 2)
    assert events == [0, 0, 0, 1, 0, -1]
    bars = [
        dict(open=o, close=c) for o, c in zip([4, 2, 2, 4, None, 8], map(float, values))
    ]
    run = q.simulate(bars, events, 1, 6, q.Costs(100, 0, 0, 100), detail=True)
    assert run["markers"] == [(4, 1, 8)]
    assert run["net"] == pytest.approx(2 / (8 * 1.01) - 1)
    assert run["exits"] == 0
    bars += [dict(open=3, close=3)]
    run = q.simulate(bars, events + [0], 1, 7, q.Costs(100, 0, 0, 100))
    assert run["net"] == pytest.approx(3 * 0.98 / (8 * 1.01) - 1)
    assert run["exits"] == 1


def test_fixed_windows_and_no_holdout_leakage():
    rows = sample(q.MIN_ROWS)

    def evaluate():
        bars, issues = q.prepare(rows, [], "NASDAQ")
        return q.evaluate(bars, q.costs("NASDAQ"), issues)

    before = evaluate()
    assert list(before["scores"]) == list(range(5, 121))
    assert len(before["holdout"]) == 116 and len(before["folds"]) == 2
    assert before["training"][0] == rows[q.WARM]["day"]
    assert before["candidate"] is not None
    for i in range(len(rows) - q.HOLD, len(rows)):
        rows[i]["closing"] = str(100 + 4 * sin(i / 5))
    after = evaluate()
    for key in ("candidate", "scores", "folds"):
        assert before[key] == after[key]
    assert before["holdout"] != after["holdout"]
    assert all(f["end"] < before["hold_dates"][0] for f in before["folds"])


def test_quality_short_history_and_missing_sessions():
    rows = sample(q.MIN_ROWS)
    rows[15]["opening"] = "50"
    bars, issues = q.prepare(rows, [], "NASDAQ")
    assert "분할" in issues[0]
    assert not q.evaluate(bars, q.costs("NASDAQ"), issues)["selected"]
    missing = rows.pop(6)["day"]
    assert any("누락" in s for s in q.prepare(rows, [missing], "NASDAQ")[1])
    assert q.prepare(rows, [], "KRAKEN_X")[1]
    small = q.evaluate(bars[:130], q.costs("NASDAQ"), [])
    assert (
        len(small["scores"]) == 116 and not small["holdout"] and not small["selected"]
    )
    flat = [dict(r, closing="100", opening="100") for r in sample(q.MIN_ROWS)]
    assert (
        q.evaluate(q.prepare(flat, [], "NASDAQ")[0], q.costs("NASDAQ"), [])["candidate"]
        is None
    )


def test_market_screen_replay_and_corporate_action_hold(tmp_path):
    import gzip
    import hashlib
    from private_accounts import equity_screen

    rows = sample(q.MIN_ROWS)
    k = ("NASDAQ", "PUBLIC", "USD")
    item = (k, "https://example.org/history", rows, [], [rows[-3]["day"]])
    venue, symbol, currency, digest, blob, detail, final_scores = equity_screen.screen_rows(item)
    raw = gzip.decompress(blob)
    inputs = json.loads(raw)
    assert (venue, symbol, currency) == k and hashlib.sha256(raw).hexdigest() == digest
    assert json.loads(detail)["state"] == "action_hold"
    assert json.loads(detail)["actions"] == [rows[-3]["day"]]
    assert json.loads(final_scores) == json.loads(json.dumps(q.replay(inputs)[1]["holdout"]))
    assert not equity_screen.complete_prices(dict(opening="unknown", closing="12"))


def test_market_screen_cutoff_and_authenticated_lookup(tmp_path):
    from private_accounts import equity_screen
    from agents import intelligence

    package = tmp_path / "package"
    package.mkdir()
    rows = sample(q.MIN_ROWS)
    day = rows[-1]["day"]
    cutoff = day + "T23:00:00+00:00"
    with live_valuation.connection(package, write=True) as db:
        for ddl in price_history.DDL:
            db.execute(ddl)
        for venue, symbol, currency in [("KRX", "123456", "KRW"), ("NYSE", "PUBLIC", "USD")]:
            bars = [(r["day"],r["opening"],"150","10",r["closing"]) for r in rows]
            price_history.persist(db, (venue,symbol,currency), "https://example.org/daily", bars, cutoff)
    folder = package / ".local" / "equity_screens"
    path = folder / "20200101T230000.sqlite3"
    equity_screen.run(package, path, {"KR":day,"US":day}, cutoff, None, 1)
    assert intelligence.private_json(package, "equity_screen_index.json", {})["markets"]["KR"]["total"] == 1
    assert "PUBLIC · NYSE" in quant_page.market_screen_panel(package, None, "PUBLIC")
    export = equity_screen.public_csv(package).decode("utf-8-sig")
    assert len(export.splitlines()) == 3 and "NYSE:PUBLIC" in export and "KRX:123456" in export
    assert "표본에서 확인되지" in quant_page.market_screen_panel(package, None, "UNKNOWN")
    with pytest.raises(FileExistsError):
        equity_screen.run(package, path, {"KR":day,"US":day}, cutoff, None, 1)


def test_private_dashboard_render_and_cache(tmp_path):
    pkg, directory = tmp_path / "package", tmp_path / "accounts"
    pkg.mkdir()
    with store.database(directory, True) as db:
        store.save(
            db,
            "kis",
            "fixture",
            "2022-01-01T00:00:00+00:00",
            [("DEMO", "USD", "1", "100")],
        )
    rows = sample(q.MIN_ROWS)
    with live_valuation.connection(pkg, write=True) as db:
        price_history.install(db)
        for source, sequence in [("history", rows), ("latest", sample(4))]:
            price_history.persist(
                db,
                ("NASDAQ", "DEMO", "USD"),
                source,
                [(r["day"], r["opening"], "110", "90", r["closing"]) for r in sequence],
                "2022-01-01",
            )
    for n in ("5", "120"):
        html = quant_page.render(directory, pkg, "/test", {"period": n}, "").decode()
        assert html.count('aria-current="true"') == 1
        assert html.count("/quant?position=") == 116 and "가격과 모의 체결" in html
        assert "초보자용 퀀트 화면 읽는 법" in html
        assert n + "일선 · 최종 미사용 구간" in html
    (cache,) = (pkg / ".local").glob("quant-*.json")
    assert cache.stat().st_mode & 0o077 == 0
    assert json.loads(cache.read_text())["inputs"]["source"] == "history"


def dashboard_request(server, path, host="127.0.0.1:18765"):
    """Exercise the real HTTP parser and authentication without a TCP listener."""
    from io import BytesIO

    class Request:
        def __init__(self):
            self.output = bytearray()

        def makefile(self, *_):
            return BytesIO(f"GET {path} HTTP/1.0\r\nHost: {host}\r\n\r\n".encode())

        def sendall(self, data):
            self.output.extend(data)

    request = Request()
    server.RequestHandlerClass(request, ("127.0.0.1", 1234), server)
    header, body = request.output.decode().split("\r\n\r\n", 1)
    return int(header.split()[1]), body


def test_authenticated_holding_menu(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from urllib.parse import urlsplit
    from agents.intelligence import position_id

    directory, pkg = tmp_path / "accounts", tmp_path / "package"
    pkg.mkdir()
    with store.database(directory, True) as db:
        store.save(
            db,
            "kis",
            "fixture",
            "2022-01-01T00:00:00+00:00",
            [("DEMO", "USD", "1", "100")],
        )
    monkeypatch.setattr(
        view,
        "ThreadingHTTPServer",
        lambda addr, cls: SimpleNamespace(server_port=addr[1], RequestHandlerClass=cls),
    )
    server, url = view.server(directory, 18765, pkg)
    base = urlsplit(url).path
    status, home = dashboard_request(server, base + "/desk/manager")
    path = base + "/quant?position=" + position_id("kis", "fixture", "DEMO", "USD")
    assert status == 200 and path in home
    status, page = dashboard_request(server, path)
    assert status == 200 and "선정 보류" in page and "완료 일봉 원천" in page
    assert dashboard_request(server, "/invalid/quant")[0] == 404
    assert dashboard_request(server, path, "untrusted")[0] == 404


def test_holdout_split_preserves_frozen_candidate(tmp_path):
    rows = sample(q.MIN_ROWS)
    key = ("NASDAQ", "DEMO", "USD")
    _, before, checksum = quant_page.experiment(tmp_path, key, "fixture", rows, [])
    rows[-1]["opening"] = "50"
    _, after, revised = quant_page.experiment(tmp_path, key, "fixture", rows, [])
    assert revised != checksum
    assert (
        after["candidate"] == before["candidate"]
        and after["scores"] == before["scores"]
    )
    assert not after["holdout"] and not after["selected"]


def test_old_gap_restarts_warmup_without_reusing_holdout(tmp_path):
    key = ("NASDAQ", "DEMO", "USD")
    rows = sample(q.MIN_ROWS + 20)
    baseline = quant_page.experiment(tmp_path, key, "fixture", rows[20:], [])[1]
    rows[19]["closing"] = "bad"
    _, recovered, _ = quant_page.experiment(tmp_path, key, "fixture", rows, [])
    assert recovered["excluded"] == 20
    for field in ("candidate", "scores", "holdout", "folds"):
        assert recovered[field] == baseline[field]
    rows[30]["closing"] = "bad"
    _, short, _ = quant_page.experiment(tmp_path, key, "fixture", rows, [])
    assert not short["holdout"] and not short["candidate"]
    assert short["training"][-1] == rows[-q.HOLD - 1]["day"]


def test_invalid_final_close_preserves_training_and_bad_open_defers(tmp_path):
    key = ("NASDAQ", "DEMO", "USD")
    rows = sample(q.MIN_ROWS)
    rows[200]["opening"] = "invalid"
    before = quant_page.experiment(tmp_path, key, "fixture", rows, [])[1]
    rows[-1]["closing"] = "invalid"
    after = quant_page.experiment(tmp_path, key, "fixture", rows, [])[1]
    assert after["candidate"] == before["candidate"] is not None
    assert after["scores"] == before["scores"] and after["folds"] == before["folds"]
    assert not after["holdout"] and not after["selected"]


def test_source_choice_uses_clean_training_only(tmp_path):
    key = ("NASDAQ", "DEMO", "USD")
    with live_valuation.connection(tmp_path, write=True) as db:
        price_history.install(db)
        for source, size in [
            ("long-broken", q.MIN_ROWS + 20),
            ("short-clean", q.MIN_ROWS),
        ]:
            rows = sample(size)
            if source == "long-broken":
                rows[100]["opening"] = "50"
            else:
                rows[-1]["opening"] = "50"
            price_history.persist(
                db,
                key,
                source,
                [(r["day"], r["opening"], "110", "50", r["closing"]) for r in rows],
                "2022-01-01",
            )
        rows, source, count = quant_page.history_for_research(db, key, [])
        assert source == "short-clean" and count == 2
        result = quant_page.experiment(tmp_path, key, source, rows, [])[1]
        assert result["candidate"] is not None and not result["holdout"]
