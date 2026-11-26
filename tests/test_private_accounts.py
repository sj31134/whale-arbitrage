from contextlib import contextmanager
import http.client
import json
import errno
import socket
import sqlite3
import stat
import threading
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urlsplit

import pytest

from private_accounts import exchanges, store, view
from private_accounts.__main__ import run

WHEN = "2025-01-02T15:30:00+09:00"
HEADER = "symbol,quantity,currency,market_value\n"


@pytest.fixture
def local(tmp_path):
    return tmp_path.resolve() / "private"


def import_sample(local, body, when=WHEN, provider="kis", alias="main"):
    src = local.parent / "sample.csv"
    src.write_text(HEADER + body, encoding="utf-8-sig")
    run(["import-csv", provider, str(src), "--as-of", when, "--account", alias], local)


def test_initial_status_no_private_db(local, capsys):
    run(["status"], local)
    status = capsys.readouterr().out
    assert all(label in status for label in store.PROVIDERS.values())
    assert status.count("수집 전") == 6
    assert not local.exists()


@pytest.mark.parametrize("provider", store.BROKERS)
def test_csv_latest_history_replay_and_privacy(local, provider):
    sample = "005930,10.00,KRW,400\nKRW,600,KRW,600.0\nAAPL,1,USD,40\n"
    import_sample(local, sample, provider=provider)
    import_sample(local, sample, when="2025-01-02T06:30:00Z", provider=provider)
    import_sample(local, "KRW,1000,KRW,1000\n", when="2025-01-01T00:00:00Z", provider=provider)
    with store.database(local) as con:
        assert con.execute("SELECT COUNT(*) FROM snapshots").fetchone() == (2,)
        doc = store.agent_view(con, provider, "main")
        assert doc == {"as_of": "2025-01-02T06:30:00.000000+00:00", "holdings": [
            {"symbol": "005930", "currency": "KRW", "weight_pct": "40"},
            {"symbol": "AAPL", "currency": "USD", "weight_pct": "100"},
            {"symbol": "KRW", "currency": "KRW", "weight_pct": "60"}]}
        with pytest.raises(sqlite3.OperationalError):
            con.execute("DELETE FROM holdings")
    assert stat.S_IMODE(local.stat().st_mode) == 0o700
    assert stat.S_IMODE((local / "balances.sqlite3").stat().st_mode) == 0o600


@pytest.mark.parametrize("invalid", ["", "BTC,1,KRW,2\nBTC,2,KRW,3\n", "BTC,-1,KRW,10\n",
                                     "BTC,NaN,KRW,10\n", "BTC,1,KRW,10,more\n", "BTC,2,KRW,70\n"])
def test_invalid_or_conflicting_import_preserves_previous(local, invalid):
    import_sample(local, "BTC,1,KRW,10\n")
    with pytest.raises(ValueError):
        import_sample(local, invalid)
    with store.database(local) as con:
        assert con.execute("SELECT COUNT(*) FROM snapshots").fetchone() == (1,)
        assert store.positions(con, 1) == [("BTC", "KRW", "1", "10")]


def test_missing_valuations_account_and_currency_isolation(local):
    import_sample(local, "AAPL,3,USD,\nUSD,10,USD,10\nKRW,5,KRW,5\n")
    import_sample(local, "KRW,0,KRW,0\n", alias="retirement")
    with store.database(local) as con:
        results = store.agent_view(con, "kis", "main")["holdings"]
        assert {r["symbol"]: r["weight_pct"] for r in results} == {"AAPL": None, "USD": None, "KRW": "100"}
        assert store.agent_view(con, "kis", "retirement")["holdings"] == []


def test_db_permissions_and_symlinks(local):
    with store.database(local, True):
        pass
    local.chmod(0o755)
    with pytest.raises(ValueError):
        with store.database(local):
            pass
    local.chmod(0o700)
    link = local.parent / "link"
    link.symlink_to(local)
    with pytest.raises(ValueError):
        store.private_path(link, True)


@pytest.mark.parametrize("provider, fiat", [("upbit", "KRW"), ("binance", "USDT")])
def test_crypto_sync_and_quote_outage(local, monkeypatch, provider, fiat):
    reader = Mock(return_value=[{"symbol": "BTC", "free": "1.4", "locked": "0.1"},
                                {"symbol": fiat, "free": "50", "locked": "0"}])
    monkeypatch.setattr(exchanges, "native", reader)
    prices = Mock(return_value={"BTC": Decimal("100")})
    monkeypatch.setattr(exchanges, "public_prices", prices)
    run(["sync", provider], local)
    reader.assert_called_once_with("sync", provider, "main")
    prices.assert_called_once_with(provider)
    with store.database(local) as con:
        doc = store.agent_view(con, provider, "main")
        assert next(r for r in doc["holdings"] if r["symbol"] == "BTC")["weight_pct"] == "75"
    prices.side_effect = TimeoutError()
    run(["sync", provider], local)
    with store.database(local) as con:
        assert all(r["weight_pct"] is None for r in store.agent_view(con, provider, "main")["holdings"])


def test_connect_failure_sync_all_disconnect(local, monkeypatch):
    native = Mock(side_effect=ValueError("bad key"))
    monkeypatch.setattr(exchanges, "native", native)
    with pytest.raises(ValueError):
        run(["connect", "binance"], local)
    with store.database(local) as con:
        assert not any(p[2] for p in store.profiles(con))
    native.side_effect = None
    for p in store.CRYPTO:
        run(["connect", p], local)
    fetch = Mock(side_effect=[ValueError("failure"), []])
    monkeypatch.setattr(exchanges, "sync_rows", fetch)
    with pytest.raises(ValueError, match="binance/main"):
        run(["sync-all"], local)
    run(["disconnect", "upbit"], local)
    with store.database(local) as con:
        assert store.agent_view(con, "upbit", "main")["holdings"] == []
        assert [p for p, _, active, _, _ in store.profiles(con) if active] == ["binance"]


def test_private_http_requests(local, monkeypatch):
    import_sample(local, "005930,10,KRW,1000\n")
    mock = Mock(return_value=SimpleNamespace(server_port=8765))
    monkeypatch.setattr(view, "ThreadingHTTPServer", mock)
    server, url = view.server(local)
    address, handler = mock.call_args.args
    assert address == ("127.0.0.1", 8765)
    u = urlsplit(url)
    for method, path, host, code in [
        ("GET", u.path + "/portfolio", u.netloc, 200), ("GET", "/", u.netloc, 404),
        ("GET", u.path, "example.invalid", 404), ("POST", u.path, u.netloc, 404)]:
        with _request_socket(server, handler, method, path, host) as c:
            response = http_client_response(c)
            assert response.status == code
            if code == 200:
                assert response.getheader("Cache-Control") == "no-store"
            assert (b"005930" in response.read()) == (code == 200)


@contextmanager
def _request_socket(server, handler, method, path, host):
    peer, client = socket.socketpair()
    def serve():
        with peer:
            handler(peer, ("127.0.0.1", 1), server)
    thread = threading.Thread(target=serve, daemon=True)
    with client:
        client.settimeout(4)
        thread.start()
        client.sendall(f"{method} {path} HTTP/1.0\r\nHost: {host}\r\n\r\n".encode())
        try:
            yield client
        finally:
            client.close()
            thread.join(timeout=4)


def http_client_response(client):
    response = http.client.HTTPResponse(client)
    response.begin()
    return response


def test_private_http_listener(local):
    import_sample(local, "005930,10,KRW,1000\n")
    try:
        server, url = view.server(local, port=0)
    except PermissionError as exc:
        if exc.errno == errno.EPERM:
            pytest.skip("실행 환경이 TCP 포트 열기를 차단함")
        raise
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        u = urlsplit(url)
        assert u.hostname == server.server_address[0] == "127.0.0.1"
        client = http.client.HTTPConnection(u.hostname, u.port, timeout=3)
        client.request("GET", u.path + "/portfolio")
        response = client.getresponse()
        assert response.status == 200 and b"005930" in response.read()
        client.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_csv_parser_rejects_extra_sensitive_fields_and_naive_time(local):
    src = local.parent / "test.csv"
    src.write_text("account_number," + HEADER + "private,005930,1,KRW,10\n")
    with pytest.raises(ValueError):
        store.read_csv(src)
    with pytest.raises(ValueError):
        store.timestamp("2025-01-02T12:00")


@pytest.fixture
def workbook_setup(tmp_path):
    from openpyxl import Workbook
    from private_accounts import local_sources
    root = tmp_path.resolve() / "project"
    package = root / "private_accounts"
    package.mkdir(parents=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(local_sources.FIELDS)
    for p, a, symbol, qty, value, fmt in [
        ("한국투자증권", "IRP", "시험 종목", 2, 300, '"₩"#,##0'),
        ("한국투자증권", "IRP", "시험 현금", 2, 100, '"₩"#,##0'),
        ("한국투자증권", "ISA", "시험 종목", 3, 400, '"US$"#,##0'),
        ("Binance", "현물", "TEST", 1, 100, '"US$"#,##0'),
    ]:
        sheet.append([p, a, symbol, -3, -0.01, qty, value, None, None])
        sheet.cell(sheet.max_row, 5).number_format = "0%"
        sheet.cell(sheet.max_row, 7).number_format = fmt
    workbook.save(package / "accounts_stocks.xlsx")
    (root / ".env").write_text("Custom_IRP_account_APP Key=one\nCustom_IRP_account_APP Secret=two\n"
                               "Custom_ISA_account_APP Key=three\nCustom_ISA_account_APP Secret=four\n"
                               "Binance_account_APP Key=fakekey\nBinance_account_APP Secret=fakesecret\n"
                               "Upbit_account_APP Key=testkey\nUpbit_account_APP Secret=testsecret\n"
                               "market_api_key=market-only\n")
    return root


def test_offline_setup_preserves_keys_and_maps_workbook(workbook_setup, local, capsys):
    from private_accounts import local_sources as src
    root = workbook_setup
    package = root / "private_accounts"
    raw = (root / ".env").read_bytes()
    info = src.prepare(root)
    assert info == src.prepare(root)
    assert {p for p in info["ready"]} == {"upbit", "binance"}
    assert "기관 약칭 확인 필요" in [a["credential_status"] for a in info["accounts"]]
    private = package / ".local"
    assert (private / "credentials.env").read_bytes() == raw
    assert not any(x in (root / ".env").read_text() for x in ("fakesecret", "market-only"))
    assert stat.S_IMODE(private.stat().st_mode) == 0o700
    for f in [package / "accounts_stocks.xlsx", private / "credentials.env", private / "bindings.json"]:
        assert stat.S_IMODE(f.stat().st_mode) == 0o600
    assert src.exchange_keys(private / "credentials.env", "binance") == {"access": "fakekey", "secret": "fakesecret"}
    with pytest.raises(ValueError):
        src.exchange_keys(private / "credentials.env", "kis")
    run(["status"], local, root)
    assert "종목" not in capsys.readouterr().out
    run(["agent-view", "kis", "--account", "irp"], local, root)
    result = json.loads(capsys.readouterr().out)
    assert result["source"] == "workbook"
    assert sorted(r["weight_pct"] for r in result["holdings"]) == ["25", "75"]
    assert all(set(r) == {"symbol", "currency", "weight_pct"} for r in result["holdings"])
    page = view.render(local, package).decode()
    assert "시험 종목" in page and "-1.00%" in page
    assert "fakesecret" not in page and "fakesecret" not in (private / "bindings.json").read_text()
    assert not local.exists()


def test_connect_env_links_selected_profile(workbook_setup, local, monkeypatch):
    from private_accounts import local_sources as src
    src.prepare(workbook_setup)
    reader = Mock()
    monkeypatch.setattr(exchanges, "native", reader)
    run(["connect-env", "binance"], local, workbook_setup)
    reader.assert_called_once_with("connect-env", "binance", "spot", credentials={"access": "fakekey", "secret": "fakesecret"})
    with store.database(local) as con:
        assert ("binance", "spot", 1, None, None) in store.profiles(con)


def test_env_no_shell_evaluation_private_modes_and_no_overwrite(workbook_setup):
    from private_accounts import local_sources as src
    root = workbook_setup
    src.prepare(root)
    path = root / "private_accounts/.local/credentials.env"
    raw = path.read_bytes()
    (root / ".env").write_text("another=value\n")
    with pytest.raises(ValueError):
        src.prepare(root)
    assert path.read_bytes() == raw
    path.write_text("UPBIT_API_KEY=\u0024(HIDDEN)\n")
    with pytest.raises(ValueError, match="참조식"):
        src.exchange_keys(path, "upbit")
    path.chmod(0o644)
    with pytest.raises(ValueError, match="0600"):
        src.credential_groups(path)


def test_workbook_currency_is_explicit():
    from private_accounts.local_sources import valuation_currency
    assert valuation_currency('"USDT"#0') == "USDT"
    assert valuation_currency('"US$"#0') == "USD"
    with pytest.raises(ValueError):
        valuation_currency("[$-409]#,##0")


def test_dashboard_skips_totals_and_reports_partial_holdings(workbook_setup, local, monkeypatch):
    from openpyxl import load_workbook
    from private_accounts import local_sources

    package = workbook_setup / "private_accounts"
    path = package / "accounts_stocks.xlsx"
    path.chmod(0o600)
    _, expected = local_sources.workbook_accounts(path)
    wb = load_workbook(path)
    sheet = wb.active
    sheet["D6"] = "=SUM(D2:D5)"
    sheet["G6"] = "=SUM(G2:G5)"
    sheet["K7"] = "=SUM(G2:G5)"
    wb.save(path)
    assert local_sources.workbook_accounts(path)[1] == expected

    httpd = SimpleNamespace(server_port=8765)
    factory = Mock(return_value=httpd)
    monkeypatch.setattr(view, "ThreadingHTTPServer", factory)
    _, url = view.server(local, package=package)
    _, handler = factory.call_args.args
    u = urlsplit(url)
    with _request_socket(httpd, handler, "GET", u.path + "/portfolio", u.netloc) as sock:
        response = http_client_response(sock)
        assert response.status == 200 and "시험 종목" in response.read().decode()

    sheet["C8"] = "private-instrument"
    sheet["F8"] = 1
    wb.save(path)
    wb.close()
    with _request_socket(httpd, handler, "GET", u.path + "/portfolio", u.netloc) as sock:
        response = http_client_response(sock)
        data = response.read().decode()
        assert response.status == 503 and "8행" in data and "private-instrument" not in data
        assert response.getheader("Cache-Control") == "no-store"


def test_portfolio_review_routes_real_sources_within_accounts(workbook_setup, local, capsys):
    from private_accounts import local_sources as src
    from agents.portfolio import portfolio_review

    root = workbook_setup
    src.prepare(root)
    package = root / "private_accounts"
    roles = package / ".local/agent_roles.json"
    roles.write_text(json.dumps([
        dict(provider="kis", account="isa", symbol="시험 종목", role="us_small_cap_high_beta"),
        dict(provider="kis", account="irp", symbol="시험 현금", role="cash"),
    ]))
    roles.chmod(0o600)

    def positions(domain):
        doc = portfolio_review(local, package, domain)
        return {a["account"]: a["holdings"] for a in doc["accounts"]}

    assert positions("whale")["spot"][0]["symbol"] == "TEST"
    assert positions("crypto")["spot"][0]["symbol"] == "TEST"
    assert positions("us_small_cap_high_beta")["irp"] == []
    assert positions("us_small_cap_high_beta")["isa"][0]["task"] == "시총·베타·단기 수급 검증"
    assert positions("equities")["irp"] == [dict(symbol="시험 종목", currency="KRW", weight_pct="75",
                                              task="증권 계좌 상품 유형 확인")]
    assert all(not holdings for holdings in positions("real_estate").values())

    # Use a fixed workbook mtime between two valid, historical snapshots.
    import os
    os.utime(package / "accounts_stocks.xlsx", (1735862400, 1735862400))
    import_sample(local, "OLD,1,USD,40\n", alias="isa")
    capsys.readouterr()
    run(["portfolio-review", "equities"], local, root)
    doc = json.loads(capsys.readouterr().out)
    assert "upbit" in doc["providers_without_data"]
    isa, = [a for a in doc["accounts"] if a["account"] == "isa"]
    assert isa["source"] == "workbook" and len(isa["holdings"]) == 1
    assert isa["holdings"][0]["symbol"] == "시험 종목"

    import_sample(local, "PROP,1,KRW,5\n", alias="isa", when="2025-01-04T00:00:00Z")
    roles.write_text(json.dumps([dict(provider="kis", account="isa", symbol="PROP", role="real_estate")]))
    doc = portfolio_review(local, package, "real_estate")
    isa, = [a for a in doc["accounts"] if a["account"] == "isa"]
    assert isa["source"] == "snapshot" and isa["time_basis"] == "balance_as_of"
    assert isa["holdings"] == [dict(symbol="PROP", currency="KRW", weight_pct="100", task="보유 분석")]
    roles.chmod(0o644)
    with pytest.raises(ValueError, match="0600"):
        portfolio_review(local, package, "whale")


def test_daily_review_signed_loss_and_latest_source(workbook_setup, local, capsys, monkeypatch):
    from openpyxl import load_workbook
    from agents import intelligence
    from private_accounts import daily_review
    src = workbook_setup / "private_accounts"
    path = src / "accounts_stocks.xlsx"
    book = load_workbook(path)
    sheet = book.active
    # Two rows in one KRW account, one offsetting gain. A USD profit has ambiguous units.
    for n, val in ((2, -100), (3, 20), (4, 80), (5, -20)):
        sheet.cell(n, 4, val).number_format = sheet.cell(n, 7).number_format if n != 4 else "General"
    book.save(path)
    book.close()
    path.chmod(0o600)
    refreshed = []
    monkeypatch.setattr(intelligence, "collect", lambda package, *, domains=None: refreshed.append(domains))
    run(["daily-review", "--refresh"], local, workbook_setup)
    assert refreshed == [None]
    assert capsys.readouterr().out == "로컬 일일 검토 저장 완료\n"
    def latest():
        log = intelligence.private_json(src, daily_review.FILE, {})
        assert len(log) == 1
        return next(iter(log.values()))
    krw = latest()["currencies"]["KRW"]
    assert (krw["net"],krw["gross_loss"],krw["recovery_pct"]) == ("-80","100","20.00")
    assert krw["losses"][0]["loss_share_pct"] == "100.0"
    usd = latest()["currencies"]["USD"]
    assert usd["known"] == 1 and usd["total"] == 2 and usd["recovery_pct"] is None
    # Give a saved balance a later as-of than a historical workbook mtime.
    import os
    os.utime(path, (1735689600,1735689600))
    import_sample(local, "NEW,1,KRW,40\n", alias="irp", when="2025-01-04T00:00:00Z")
    run(["daily-review"], local, workbook_setup)
    krw = latest()["currencies"]["KRW"]
    assert krw["known"] == 0 and krw["net"] is None and krw["recovery_pct"] is None
    assert krw["missing"][0]["symbol"] == "NEW"
    assert krw["missing"][0]["source"] == "snapshot"
    assert (src/".local"/daily_review.FILE).stat().st_mode & 0o777 == 0o600


def test_daily_flows_compare_like_periods_and_reject_bad_input():
    import io
    from datetime import date
    from private_accounts.daily_review import read_flows
    row = dict(market="테스트",period="주간",as_of="2025-01-01",metric="순설정",unit="USD",
               theme="A",net="-10",source="https://example.org/report")
    def read(rows):
        return read_flows(io.StringIO(json.dumps(rows)),date(2025,1,2))
    assert [r["theme"] for r in read([row,dict(row,theme="B",net="2"),row])] == ["B","A"]
    for invalid in (dict(row,net="NaN"),dict(row,net="unknown"),dict(row,as_of="2025-03-01"),dict(row,source="file:///fake")):
        with pytest.raises(ValueError):
            read([invalid])
    with pytest.raises(ValueError,match="충돌"):
        read([row,dict(row,net="100")])


def test_daily_research_compares_with_previous_day(workbook_setup, local):
    from datetime import date
    from agents import intelligence
    from private_accounts import daily_review, monitor

    package = workbook_setup / "private_accounts"
    (package / "accounts_stocks.xlsx").chmod(0o600)
    run(["daily-review"], local, workbook_setup)
    reports = intelligence.private_json(package, daily_review.FILE, {})
    first = next(iter(reports.values()))
    assert first["compared_to"] is None
    position = intelligence.board(local, package)["positions"][0]
    evidence = dict(
        position=position["id"], category="fundamentals", day=date.today().isoformat(), action="evidence",
        title="공시 테스트", source="https://example.org/filing", value="1", analysis="검증용 근거",
    )
    # A dated prior review supplies the comparison, even on repeated intraday runs.
    intelligence.update_json(package, daily_review.FILE, {}, lambda _: {"2024-12-31": dict(first)})
    intelligence.manage(local, package, evidence)
    for _ in range(2):
        run(["daily-review"], local, workbook_setup)
        saved = intelligence.private_json(package, daily_review.FILE, {})[first["day"]]
        assert saved["compared_to"] == "2024-12-31"
        assert any(o["title"] == "공시 테스트" for o in saved["new_observations"])
    assert "공시 테스트" in monitor.daily_panel(package, "/test")


def test_stable_dashboard_survives_restart_and_reuses_listener(local, tmp_path, monkeypatch, listener):
    from private_accounts import dashboard_launcher as launcher
    from urllib.request import build_opener, ProxyHandler

    package = tmp_path.resolve() / "project"
    package.mkdir()
    key = launcher.identity(package)
    assert launcher.identity(package) == key
    assert (package / ".local" / launcher.IDENTITY).stat().st_mode & 0o777 == 0o600
    client = build_opener(ProxyHandler({}))
    port = 0
    links = []
    for _ in range(2):
        http, url = listener(local, port, package, identity_key=key)
        port = http.server_port
        monkeypatch.setattr(launcher, "PORT", port)
        worker = threading.Thread(target=http.serve_forever, daemon=True)
        worker.start()
        try:
            assert launcher.running(key)
            with pytest.raises(ValueError):
                launcher.running(b"other")
            links.append(launcher.entry(key))
            assert links[-1] == url + "/desk/manager"
            with client.open(links[-1], timeout=5) as response:
                assert response.status == 200
            with monkeypatch.context() as patch:
                patch.setattr(launcher.subprocess, "Popen", lambda *a, **kw: pytest.fail("duplicate listener"))
                patch.setattr(launcher.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=0))
                patch.setattr(launcher.webbrowser, "open", lambda url: True)
                launcher.open_manager(package)
        finally:
            http.shutdown()
            http.server_close()
            worker.join()
    assert links[0] == links[1] and not launcher.running(key)


def test_public_launcher_only_opens_the_local_window(local, tmp_path, monkeypatch, listener):
    from contextlib import closing
    import re
    from urllib.parse import urlencode
    from private_accounts import dashboard_launcher

    package = tmp_path.resolve() / "project"
    package.mkdir()
    identity = dashboard_launcher.identity(package)
    native_open = Mock()
    monkeypatch.setattr(dashboard_launcher, "open_running_manager", native_open)
    server, private_url = listener(local, 0, package, identity_key=identity)
    port = server.server_port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with closing(http.client.HTTPConnection("127.0.0.1", port)) as client:
            client.request("GET", "/start")
            reply = client.getresponse()
            body = reply.read().decode()
            assert reply.status == 200 and "투자 대시보드 열기" in body
            assert urlsplit(private_url).path not in body
            native_open.assert_not_called()
            nonce = re.search(r'name="open" value="([^"]+)"', body)[1]
            headers = {"Content-Type": "application/x-www-form-urlencoded", "Origin": f"http://127.0.0.1:{port}"}
            client.request("POST", "/start", urlencode({"open": nonce}), headers)
            reply = client.getresponse()
            assert reply.status == 200 and urlsplit(private_url).path not in reply.read().decode()
            native_open.assert_called_once_with(package, identity, port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
