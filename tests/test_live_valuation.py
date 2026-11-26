from contextlib import closing
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import http.client
import json
import threading
from urllib.parse import urlsplit

from agents import desk_variables, intelligence, market_prices, public_variables
from agents.portfolio import portfolio_accounts
from private_accounts import live_panel, live_valuation as live, monitor, store, view


def inputs(tmp_path):
    package, directory = tmp_path.resolve() / "project", tmp_path.resolve() / "vault"
    package.mkdir()
    when = datetime.now(timezone.utc) - timedelta(days=1)
    with store.database(directory, True) as db:
        store.save(db, "upbit", "fixture", when.isoformat(), [("ALPHA", "KRW", "2", "20"), ("KRW", "KRW", "20", "20")])
        store.save(db, "kis", "fixture", when.isoformat(), [("US-ALPHA", "KRW", "1", "1234")])
    return package, directory, when


def test_two_ticks_update_cache_account_weights_stress_and_http(tmp_path, dashboard_http):
    package, directory, when = inputs(tmp_path)
    now = datetime.now(timezone.utc)
    ms = int(now.timestamp()*1000)
    price = 20

    def fetch(src):
        if src["url"] == market_prices.endpoint("upbit"):
            return json.dumps([dict(market="KRW-ALPHA", trade_timestamp=ms, trade_price=price)]).encode()
        if src["url"] == market_prices.endpoint("NASDAQ"):
            return json.dumps(dict(totalCount=1, stocks=[dict(symbolCode="ALPHA", closePrice="2",
                              localTradedAt=now.isoformat())])).encode()
        if src["url"] == market_prices.endpoint("fx"):
            return json.dumps(dict(reutersCode="FX_USDKRW", closePrice="1,300", localTradedAt=now.isoformat())).encode()
        raise OSError

    live.refresh(package, fetch)
    b = intelligence.board(directory, package, quote_book=live.read(package))
    account = next(a for a in b["accounts"] if a["provider"] == "upbit")
    assert account["marks"][0]["weight_pct"] == "66.6667"
    assert next(a for a in b["accounts"] if a["provider"] == "kis")["totals"]["KRW"] == "2600"
    assert "금리" in live_panel.panel(directory, package)
    assert "-13.33%p" in monitor.stress_panel(b["positions"], "/fixture", "pullback")

    with dashboard_http(directory, package) as (url, client):
        def get(suffix, headers=None):
            client.request("GET", urlsplit(url).path + suffix, headers=headers or {})
            response = client.getresponse()
            return response.status, response.read().decode()
        s, page = get("/desk/manager")
        assert s == 200 and "live.js" in page and "66.67%" in page
        price, ms = 40, ms + 2
        live.refresh(package, fetch)
        s, fragment = get("/desk/manager", {"X-Live-Sections": "1"})
        assert s == 200 and "80%" in fragment and 'id="live-values"' in fragment
        s, research_update = get("/desk/manager?screen=US", {"X-Live-Sections":"1", "X-Research-Sections":"1"})
        assert s == 200 and "80%" in research_update
        assert research_update.count('class="analyst-link"') == len(intelligence.DOMAINS)
        assert research_update.count('class="category-link"') == len(intelligence.catalog())
        assert "-16.00%p" in get("/portfolio")[1]
        assert "80%" in get("/accounts")[1]
        assert get("/live.js")[0] == 200
    # Changing price must never rewrite the accountant's recorded snapshot.
    assert next(a for a in portfolio_accounts(directory, package) if a["provider"] == "upbit")["totals"]["KRW"] == "40"
    price, ms = 3, ms - 5000
    live.refresh(package, fetch)
    book = live.read(package)
    assert book.match("upbit", "ALPHA", "KRW")["price"] == "40"
    def failed(_):
        raise OSError
    live.refresh(package, failed)
    assert live.read(package).match("upbit", "ALPHA", "KRW")["price"] == "40"
    assert live.read(package).sources["upbit"]["status"] != "수집 완료"


def test_lots_and_cost_currency_missing_values_and_ambiguous_identity():
    now = datetime.now(timezone.utc)
    before = (now - timedelta(days=1)).isoformat()
    row = dict(venue="KRX", symbol="000001", currency="KRW", name="테스트", english="", price="15",
               at=now.isoformat(), session="OPEN", delay="", feed="KOSPI", page=1)
    book = live.QuoteBook([row])
    raw = [("테스트", "KRW", "1", "10"), ("테스트", "KRW", "2", "20"), ("B", "KRW", "1", None)]
    marks = live.mark_account(book, "kis", raw, {("테스트", "KRW"): Decimal(6)}, before)
    m = next(m for m in marks if m["symbol"] == "테스트")
    assert (m["value"], m["gain"], m["rate"], m["weight_pct"]) == (45, 21, Decimal("87.5"), None)
    assert live.QuoteBook([row, dict(row, symbol="000002")]).match("kis", "테스트", "KRW") is None
    m, = live.mark_account(book, "kis", raw[:1], {}, (now+timedelta(hours=1)).isoformat())
    assert m["value"] == 10 and m["price"] is None and m["gain"] is None
    wrong = dict(row, venue="NASDAQ", currency="USD")
    assert live.mark_account(live.QuoteBook([wrong]), "kis", raw[:1], {}, before)[0]["state"] == "환율 미확인"


def test_public_crypto_variables_and_streams(tmp_path):
    package, _, _ = inputs(tmp_path)
    ms = int((datetime.now(timezone.utc)-timedelta(seconds=1)).timestamp()*1000)
    def fetch(s):
        if "orderbook" in s["url"]:
            level = dict(bid_size=2, bid_price=10, ask_size=1, ask_price=12)
            return json.dumps([dict(market="KRW-"+a, timestamp=ms, orderbook_units=[level]*5)
                               for a in public_variables.SAMPLE]).encode()
        asset = "BTC" if "BTCUSDT" in s["url"] else "ETH"
        obj = dict(symbol=asset+"USDT", openInterest="1234", time=ms)
        if "fundingRate" in s["url"]:
            obj = [dict(symbol=asset+"USDT", fundingRate="-0.0002", fundingTime=ms)]
        return json.dumps(obj).encode()
    public_variables.refresh(package, fetch)
    rows = desk_variables.read(package, "crypto")
    assert len(rows) == 6 and any("매수 100 / 매도 60" in r["value"] for r in rows)
    assert any(r["key"] == "funding" and Decimal(r["value"].split()[0]) == Decimal("-0.02") for r in rows)
    raw = dict(type="ticker", code="KRW-ALPHA", trade_price=13, trade_timestamp=ms)
    assert market_prices.stream_rows("upbit_stream", json.dumps(raw))[0]["symbol"] == "ALPHA"
    raw = [dict(e="24hrMiniTicker", s="ALPHAUSDT", c="12", v="1", E=ms)]
    assert market_prices.stream_rows("binance_stream", json.dumps(raw))[0]["price"] == "12"
    assert not market_prices.stream_rows("binance_stream", "[]")



def test_independent_capture_and_provider_schema(tmp_path):
    package, _, _ = inputs(tmp_path)
    now = datetime.now(timezone.utc)
    at = (now-timedelta(seconds=1)).isoformat()
    obj = {"exchangeInfo": dict(reutersCode="FX_USDKRW", localTradedAt=at, closePrice="1,300.1")}
    quotes, pages = market_prices.parse("fx", json.dumps(obj))
    assert pages == 1 and quotes[0]["price"] == "1300.1"
    intelligence.import_capture(package, "FX_USDKRW", now.isoformat(), [dict(at=at, price="1300.1")])
    intelligence.import_capture(package, "upbit_sample", now.isoformat(), [dict(
        market="KRW-BTC", trade_price="100", trade_timestamp=int((now.timestamp()-2)*1000), signed_change_rate="0")])
    b = live.read(package)
    assert b.fx["manual"] and b.match("upbit", "BTC", "KRW")["price"] == "100"
    assert "upbit" not in b.sources
    day = now.date().isoformat()
    intelligence.import_capture(package, "DGS10", now.isoformat(), [dict(day=day, value="4.9")])
    assert "4.9 %" in live_panel.variables(package) and "원문 확인" in live_panel.variables(package)


def test_authenticated_server_releases_fixed_listener_for_update(tmp_path, listener):
    from private_accounts import dashboard_launcher as launcher
    package, directory, _ = inputs(tmp_path)
    key = launcher.identity(package)
    server, _ = listener(directory, port=0, package=package, identity_key=key)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        assert launcher.running(key, port=server.server_port, build=launcher.build_id(package))
        assert launcher.running(key, port=server.server_port, request_stop=True)
        worker.join(timeout=3)
        assert not worker.is_alive()
    finally:
        server.shutdown()
        server.server_close()

def test_workbook_price_then_fx_revalues_both_weights_and_screen(tmp_path):
    import os
    from openpyxl import Workbook
    from private_accounts import local_sources

    package = tmp_path.resolve() / "project"
    package.mkdir()
    directory = tmp_path.resolve() / "vault"
    path = package / "accounts_stocks.xlsx"
    wb = Workbook()
    sheet = wb.active
    sheet.append([*local_sources.FIELDS, "시장", "종목코드"])
    for name, qty, value, cost, market, code in (
        ("합성 주식", 2, 200, 80, "US", "FIXTURE"),
        ("KRW", 100, 100, 1, None, None),
    ):
        sheet.append(["한국투자증권", "fixture", name, None, None, qty, value, cost, None, market, code])
        for col in (7, 8):
            sheet.cell(sheet.max_row, col).number_format = '"₩"#,##0'
    wb.save(path)
    path.chmod(0o600)
    now = datetime.now(timezone.utc)
    os.utime(path, (now.timestamp()-3600,)*2)
    def check(price, fx, expected):
        def fetch(src):
            when = now.isoformat()
            if src["url"] == market_prices.endpoint("NASDAQ"):
                return json.dumps(dict(totalCount=1, stocks=[dict(symbolCode="FIXTURE",
                    closePrice=price, localTradedAt=when, marketStatus="OPEN")])).encode()
            if src["url"] == market_prices.endpoint("fx"):
                return json.dumps(dict(reutersCode="FX_USDKRW", closePrice=fx, localTradedAt=when)).encode()
            raise OSError
        live.refresh(package, fetch)
        book = live.read(package)
        accounts = portfolio_accounts(directory, package, quote_book=book)
        cash, stock = accounts[0]["marks"]
        assert (stock["value"], stock["gain"], stock["rate"], stock["weight_pct"], cash["weight_pct"]) == expected
        page = live_panel.panel(directory, package, book, accounts)
        assert all(cell in page for cell in (f'<td>{live_panel.fmt(stock["value"])}</td>',
                   live_panel.signed(stock["gain"]), f'<td>{live_panel.fmt(cash["weight_pct"])}%</td>',
                   "해당 시세 마지막 수신", "화면 자료 조회"))
    check(10, 10, (200, 40, 25, "66.6667", "33.3333"))
    check(15, 10, (300, 140, Decimal("87.5"), "75", "25"))
    check(15, 20, (600, 440, 275, "85.7143", "14.2857"))


def test_quote_quality_keeps_instrument_basis_and_market_dates():
    now = datetime.now(timezone.utc)
    stamp = now.isoformat()
    older = (now - timedelta(days=5)).isoformat()
    ledger = (now - timedelta(days=10)).isoformat()
    row = dict(venue="NASDAQ", symbol="ALPHA", currency="USD", name="fixture", english="",
               price="10", at=older, seen=stamp, session="CLOSED", delay="", feed="NASDAQ", page=1)
    token = dict(row, venue="KRAKEN_X", symbol="ALPHAX", at=stamp, price="12", session="", feed="kraken_x")
    book = live.QuoteBook([row, token, dict(row, symbol="BETA", at=stamp)],
                          [dict(feed="NASDAQ", status="일부 누락")])
    assert book.match("kis", "ALPHA", "USD", ["underlying:US:ALPHA"]) is None
    assert book.match("kis", "ALPHA", "USD", ["invalid:workbook"]) is None
    marked, = live.mark_account(book, "kis", [("ALPHA", "USD", "1", "8")], {}, ledger)
    assert "종가" in marked["state"] and "지연" in marked["state"] and "저장값" in marked["state"]
    assert marked["seen"] == stamp and marked["at"] == older
    tagged = {("ALPHA", "USD"): ["underlying:US:ALPHA", "token:XT:ALPHAX"]}
    marked, = live.mark_account(book, "kis", [("ALPHA", "USD", "1", "8")], {}, ledger, identifiers=tagged)
    assert marked["value"] == 12 and "토큰 자체 가격" in marked["state"]
    halted = live.QuoteBook([dict(row, session="HALT")])
    marked, = live.mark_account(halted, "kis", [("ALPHA", "USD", "1", "8")], {}, ledger)
    assert "거래 정지" in marked["state"]
