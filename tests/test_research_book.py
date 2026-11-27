import json
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from agents import intelligence as intel
from private_accounts import (daily_review, monitor, reports, research_archive as archive,
                              research_book as book, research_page as page)


@pytest.fixture
def journal(tmp_path, monkeypatch):
    package = tmp_path.resolve() / "workspace"
    package.mkdir()
    class Clock(datetime):
        instant = datetime(2024, 1, 2, 10, tzinfo=intel.KST)
        @classmethod
        def now(cls, tz=None):
            return cls.instant.astimezone(tz)
    monkeypatch.setattr(book, "datetime", Clock)
    src = {"url": "https://example.org/filing", "label": "공시", "as_of": "2024-01-02T09:00:00+09:00"}
    rid = reports.publish(package, "equities", dict(title="원문 연구", conclusion="관찰", revisit="매출 감소",
        downside="수요 감소", as_of=src["as_of"], status="관찰", sources=[src]))
    f = dict(idea="a"*32, asset="sample <A>", benchmark="index", currency="USD", report=rid,
             observed=src["as_of"], entry="80", benchmark_entry="1000", bear="60", base="100", bull="140",
             fees="10", slip="20", catalyst="실적 공시", invalidate="매출 감소", due="2024-01-12",
             price_source=src["url"], benchmark_source="https://example.org/index")
    return package, Clock, f


def test_forward_marks_archive_and_idempotence(journal):
    package, clock, fields = journal
    assert book.entries(package) == []
    assert not (package/".local"/book.DB).exists()
    book.record(package, fields)
    book.record(package, fields)
    assert len(book.entries(package)) == 1
    a = book.entries(package)[0]["a"]
    m = book.metrics(a)
    assert m["expected"] == Decimal("29.70") and m["margin"] == 20 and m["qualifies"]
    with pytest.raises(ValueError):
        book.record(package, dict(fields, fees="11"))
    with pytest.raises(ValueError):
        book.record(package, dict(fields, idea="b"*32, fees="NaN"))
    mark = dict(idea=fields["idea"], exit="100", benchmark_exit="1000", observed=fields["observed"],
                source=fields["price_source"], benchmark_source=fields["benchmark_source"])
    with pytest.raises(ValueError):
        book.mark(package, mark, opening=True)
    mark["observed"] = (clock.instant + timedelta(minutes=5)).isoformat()
    clock.instant += timedelta(minutes=6)
    book.mark(package, mark, opening=True)
    book.mark(package, mark, opening=True)
    end = dict(mark, verdict="가설 지지", reason="수요 확인", exit="110", benchmark_exit="1040")
    with pytest.raises(ValueError):
        book.mark(package, end)
    end["observed"] = (clock.instant + timedelta(days=10)).isoformat()
    clock.instant += timedelta(days=11)
    book.mark(package, end)
    book.mark(package, end)
    with pytest.raises(ValueError):
        book.mark(package, dict(end, exit="120"))
    row, = book.entries(package)
    assert book.performance(row) == (Decimal("9.7"), Decimal("4.0"), Decimal("5.7"))
    rendered = page.render(package, "/test", "test", "").decode()
    assert "sample &lt;A&gt;" in rendered and "+5.70%p" in rendered
    assert "초보자용 가설 연구장 활용법" in rendered and "시나리오 가격 범위" in rendered
    backup = archive.snapshot(package)
    recovered = archive.recover(package, backup)
    assert book.entries(recovered) == [row] and reports.read(recovered) == reports.read(package)
    assert set(p.name for p in (recovered/".local").iterdir()) == set(archive.FILES)
    with pytest.raises(ValueError):
        archive.recover(package, backup)
    damaged = package/".local"/"research-archives"/backup/reports.FILE
    damaged.write_bytes(b"{}")
    with pytest.raises(ValueError, match="체크섬"):
        archive.recover(package, backup)


def test_comparison_status_and_export_allowlist(journal):
    package, _, f = journal
    book.record(package, f)
    book.record(package, dict(f, idea="b"*32, asset="SECOND", bull="190"))
    cmp = page.comparison(book.entries(package))
    assert cmp.index("SECOND") < cmp.index("sample")
    mixed = book.entries(package)
    mixed[0]["a"]["currency"] = "KRW"
    assert not page.comparison(mixed)
    intel.update_json(package, intel.CACHE, {}, lambda _: {"financial_conditions/DGS10": dict(
        status="네트워크 오류", attempt="2024-01-04T18:00:00+09:00", collected="2024-01-03T10:00:00+09:00",
        items=[dict(as_of="2024-01-02")])})
    panel = page.feed_health(package)
    assert all(x in panel for x in ["네트워크 오류","2024-01-03 10:00", "2024-01-02"])
    flow = dict(market="market", period="day", as_of="2024-01-02", metric="net", unit="unit",
                theme="theme", net="+5", source="https://example.org/data")
    day = "2024-01-03"
    intel.update_json(package, daily_review.FILE, {}, lambda _: {day: dict(generated=f["observed"],
        flows=[flow], account_dates=["private-sentinel"], observations=["private-observation"])})
    archive.market_note(package, day)
    note = (package/".local"/"market-notes"/(day+".md")).read_text()
    assert "private-" not in note and flow["source"] in note
    with pytest.raises(ValueError):
        archive.market_note(package, "2024-01-04")


def test_stress_does_not_duplicate_overlapping_roles():
    pos = dict(provider="kis", account="fake", currency="USD", role=None, as_of="2024-01-02T00:00:00+00:00")
    rows = [dict(pos, symbol="A", tasks={"equities":"보유 분석", "us_small_cap_high_beta":"검증"}, weight_pct="50"),
            dict(pos, symbol="USD", tasks={}, weight_pct="40"),
            dict(pos, symbol="B", tasks={"equities":"증권 계좌 상품 유형 확인"}, weight_pct="10")]
    html = monitor.stress_panel(rows, "/test", "severe")
    assert "90.00%" in html and "-15.00%p" in html and "1행" in html
    assert "산정 보류" in monitor.stress_panel([dict(rows[0], weight_pct=None)], "/test", "severe")
    conc = monitor.concentration_panel(rows, None, "/test")
    assert "소수 집중 · 현금 버퍼 실전 점검" in conc and "40.0%" in conc and "버퍼 확보" in conc
    fake_accs = [
        dict(provider="kis", account="main", marks=[
            dict(symbol="A", currency="KRW", qty="2", price=Decimal("80"), value=Decimal("160"),
                 gain=Decimal("-40"), rate=Decimal("-20"), weight_pct="80", state="시세 반영", instrument=("KRX", "005935", "KRW")),
            dict(symbol="KRW", currency="KRW", qty="40", price=Decimal("1"), value=Decimal("40"),
                 gain=Decimal("0"), rate=Decimal("0"), weight_pct="20", state="통화 잔액", instrument=None),
        ]),
        dict(provider="mirae", account="isa", marks=[
            dict(symbol="A", currency="KRW", qty="1", price=Decimal("80"), value=Decimal("80"),
                 gain=Decimal("-10"), rate=Decimal("-11.1"), weight_pct="100", state="시세 반영", instrument=("KRX", "005935", "KRW")),
        ]),
    ]
    cockpit = page.action_cockpit(None, None, "/test", quote_book=monitor.live_valuation.QuoteBook(), accounts=fake_accs)
    assert "한눈에 보는 내 계좌 손실 복기" in cockpit and "본전 100" in cockpit and "행동 지침표" in cockpit
    assert "현금 35% 목표 시뮬레이터" in cockpit and "+58원" in cockpit
    assert "절세계좌 보호" in cockpit and "다계좌 2곳 합산" in cockpit
    assert "가설 미등록 주요 보유주" in cockpit and "원클릭 가설 검증 채우기" in cockpit
    assert "준코어 · 반등 추세 유예" in cockpit


def test_voc_prefill_crypto_form_url_and_networth_banner(journal, tmp_path):
    from private_accounts import chat_page, live_panel, live_valuation
    package, _, _ = journal
    prefilled = page.render(
        package, "/test", "csrf-tok", "", query=dict(
            asset="한화에어로스페이스 (012450)", currency="KRW",
            entry="650000", bear="598000", base="950000", bull="1120000",
            price_source="https://m.stock.naver.com/domestic/stock/012450/total",
            catalyst="방산 수주", invalidate="수주 취소",
        )
    ).decode()
    assert '<details id="create" open>' in prefilled
    assert "자동 채움 시나리오 3관문 사전 시뮬레이션" in prefilled
    assert "한화에어로스페이스 (012450)" in prefilled

    crypto_desk = chat_page.render(tmp_path.resolve() / "empty-vault", package, "/tok", "csrf-tok", "crypto", "").decode()
    assert 'action="/tok/desk/crypto/variable"' in crypto_desk

    qb = live_valuation.QuoteBook(
        rows=[
            dict(venue="upbit", symbol="BTC", currency="KRW", name="비트코인", english="Bitcoin",
                 price="138000000", at="2026-11-27T10:00:00+09:00", session="OPEN", delay="0", feed="upbit", page=1, seen="2026-11-27T10:00:00+09:00"),
            dict(venue="binance", symbol="BTC", currency="USDT", name="Bitcoin", english="Bitcoin",
                 price="98000", at="2026-11-27T10:00:00+09:00", session="OPEN", delay="0", feed="binance", page=1, seen="2026-11-27T10:00:00+09:00"),
            dict(venue="fx", symbol="USD/KRW", currency="KRW", name="달러원", english="USD/KRW",
                 price="1395", at="2026-11-27T10:00:00+09:00", session="OPEN", delay="0", feed="fx", page=1, seen="2026-11-27T10:00:00+09:00"),
            dict(venue="fx", symbol="USDT/USD", currency="USD", name="테더", english="USDT/USD",
                 price="1.0005", at="2026-11-27T10:00:00+09:00", session="OPEN", delay="0", feed="usdt_usd", page=1, seen="2026-11-27T10:00:00+09:00"),
            dict(venue="NASDAQ", symbol="NVDA", currency="USD", name="NVIDIA", english="NVIDIA",
                 price="149.30", at="2026-11-25T16:00:00-05:00", session="CLOSE", delay="0", feed="NASDAQ", page=1, seen="2026-11-26T00:00:00+00:00"),
            dict(venue="KRAKEN_X", symbol="NVDAX", currency="USD", name="NVDAx", english="NVDAx",
                 price="155.26", at="2026-11-27T07:25:00+00:00", session="OPEN", delay="0", feed="kraken_x", page=1, seen="2026-11-27T07:25:00+00:00"),
        ]
    )
    accs = [
        dict(provider="upbit", account="spot", marks=[
            dict(symbol="BTC", currency="KRW", qty="1", price=Decimal("138000000"), value=Decimal("138000000"),
                 gain=Decimal("8000000"), rate=Decimal("6.15"), weight_pct="100", state="시세 반영", instrument=None),
        ]),
        dict(provider="binance", account="spot", marks=[
            dict(symbol="BTC", currency="USD", qty="1", price=Decimal("98049"), value=Decimal("98049"),
                 gain=Decimal("-1951"), rate=Decimal("-1.95"), weight_pct="80", state="시세 반영", instrument=None),
            dict(symbol="NVDAB", currency="USD", qty="100", price=Decimal("155.26"), value=Decimal("15526"),
                 gain=Decimal("526"), rate=Decimal("3.5"), weight_pct="20", state="시세 반영", instrument=("Binance", "NVDAB", "USDT")),
        ]),
        dict(provider="kis", account="us", marks=[
            dict(symbol="NVDA", currency="USD", qty="50", price=Decimal("149.30"), value=Decimal("7465"),
                 gain=Decimal("-535"), rate=Decimal("-6.7"), weight_pct="100", state="시세 반영", instrument=("NASDAQ", "NVDA", "USD")),
        ]),
    ]
    banner = live_panel.networth_reference(accs, qb)
    assert "전체 계좌 단순 합산 참고치" in banner and "BTC 김치프리미엄" in banner
    overlap = live_panel.multi_account_overlap(accs)
    assert "본주+RWA 기초자산 중복" in overlap
    us_cockpit = page.action_cockpit(None, None, "/test", quote_book=qb, accounts=accs)
    assert "저녁 미국장 실전 준비" in us_cockpit and "엔비디아 선행(NVDAx)" in us_cockpit and "+3.99%" in us_cockpit
    assert "본주+RWA 합산 2곳" in us_cockpit



def test_dashboard_journal_workflow(journal, tmp_path, dashboard_http):
    import http.client
    import re
    import threading
    from urllib.parse import urlencode, urlsplit
    from private_accounts import view

    package, clock, f = journal
    with dashboard_http(tmp_path.resolve()/"fake-accounts", package) as (url, client):
        u = urlsplit(url)
        def request(method, path, fields=None):
            headers = {"Origin": "http://" + u.netloc, "Content-Type": "application/x-www-form-urlencoded"}
            client.request(method, u.path + path, urlencode(fields) if fields else None, headers)
            response = client.getresponse()
            return response.status, response.read().decode()

        status, home = request("GET", "")
        assert status == 200 and "오늘의 투자 검토" in home
        status, html = request("GET", "/research")
        assert status == 200
        csrf = re.search(r'name="csrf" value="([^"]+)"', html)[1]
        f["observed"] = "2024-01-02T09:00:00"
        assert request("POST", "/desk/manager/idea", dict(f, csrf="bad"))[0] == 403
        assert request("POST", "/desk/manager/idea", dict(f, csrf=csrf))[0] == 303
        assert "모의 추적 시작" in request("GET", "/research")[1]
        m = dict(idea=f["idea"], csrf=csrf, exit="100", benchmark_exit="1000",
                 source=f["price_source"], benchmark_source=f["benchmark_source"])
        clock.instant += timedelta(hours=1)
        assert request("POST", "/desk/manager/start", dict(m, observed="2024-01-02T10:45:00"))[0] == 303
        clock.instant += timedelta(days=10)
        end = dict(m, exit="104", observed="2024-01-12T10:40:00", verdict="가설 기각", reason="공시 대조")
        assert request("POST", "/desk/manager/assess", end)[0] == 303
        assert "+3.70%p" in request("GET", "/research")[1]
        assert request("POST", "/desk/manager/snapshot", dict(csrf=csrf))[0] == 303
        key, = (package/".local"/"research-archives").iterdir()
        assert request("POST", "/desk/manager/recover", dict(csrf=csrf, snapshot_id=key.name))[0] == 303
        assert request("POST", "/desk/manager/market-note", dict(csrf=csrf, day="2001-04-01"))[0] == 400


def test_cash_flow_reconciliation_is_explicit_and_auditable(journal):
    from private_accounts import account_performance as perf
    package, _, _ = journal
    a = dict(provider="kis", account="sample", source="snapshot", currency="USD",
             as_of="2024-01-01T00:00:00+09:00", value="1000")
    b = dict(a, value="1600", as_of="2024-01-11T00:00:00+09:00")
    intel.update_json(package, daily_review.FILE, {}, lambda _: {
        "2023-12-31": {}, "2024-01-01":{"valuations":[a]},
        "2024-01-11":{"valuations":[b,dict(b,currency="KRW",value="900")]}})
    token, = perf.intervals(package)
    fields = dict(interval=token, confirmed="yes", begin=a["as_of"], end=b["as_of"],
                  flows="2024-01-06T00:00:00, +500")
    with pytest.raises(ValueError):
        perf.save(package, dict(fields, flows=""))
    perf.save(package, fields)
    perf.save(package, fields)
    saved = intel.private_json(package, perf.FILE, {})[token]
    assert len(saved) == 1 and saved[0]["data"]["gain"] == "100" and saved[0]["data"]["rate"] == "8"
    with pytest.raises(ValueError):
        perf.save(package, dict(fields, flows="없음"))
    perf.save(package, dict(fields, flows="없음", revision="1"))
    assert len(intel.private_json(package, perf.FILE, {})[token]) == 2
    assert "+60.00%" in perf.panel(package, "/test", "test")
    with pytest.raises(ValueError):
        perf.save(package, dict(fields, flows="2024-01-12T00:00:00, +1"))
    zero, end = datetime.fromisoformat(a["as_of"]), datetime.fromisoformat(b["as_of"])
    assert perf.calculate("0","50",zero,end,[]) == (50,None)


def test_research_cli_retry(journal, tmp_path, monkeypatch, capsys):
    import io
    import sys
    from private_accounts.__main__ import run
    package, clock, fields = journal
    project = tmp_path.resolve()/"project"
    project.mkdir()
    package.rename(project/"private_accounts")
    payload = {k:v for k,v in fields.items() if k != "idea"}
    def call(args, doc):
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(doc)))
        run(args, tmp_path.resolve()/"unused", project)
        return capsys.readouterr().out.strip()
    key = call(["research-register"], payload)
    assert len(key) == 32 and call(["research-register"], payload) == key
    clock.instant += timedelta(days=1)
    quote = dict(observed="2024-01-03T09:00:00+09:00", exit="90", benchmark_exit="1000",
                 source=fields["price_source"], benchmark_source=fields["benchmark_source"])
    assert call(["research-observe","start",key], quote) == "모의 관측 저장 완료"
    clock.instant += timedelta(days=1)
    quote.update(observed="2024-01-04T09:00:00+09:00", exit="85", verdict="가설 기각", reason="촉매 취소")
    assert call(["research-observe","finish",key], quote) == "모의 관측 저장 완료"


def test_six_persona_institutional_factor_custody_and_combined_stress():
    from private_accounts import live_panel
    stamp = "2026-11-27T23:00:00+09:00"
    qb = monitor.live_valuation.QuoteBook(rows=[
        dict(venue="fx", symbol="USD/KRW", currency="KRW", price="1350", at=stamp, seen=stamp),
        dict(venue="fx", symbol="USDT/USD", currency="USD", price="1.0", at=stamp, seen=stamp),
    ])
    accs = [
        dict(provider="kis", account="일반위탁", marks=[
            dict(symbol="000660", currency="KRW", qty="10", price=Decimal("5000000"), value=Decimal("50000000"),
                 gain=Decimal("0"), rate=Decimal("0"), weight_pct="71.4", state="시세 반영", instrument=("KRX", "000660", "KRW")),
            dict(symbol="KRW", currency="KRW", qty="20000000", price=Decimal("1"), value=Decimal("20000000"),
                 gain=Decimal("0"), rate=Decimal("0"), weight_pct="28.6", state="통화 잔액", instrument=None),
        ]),
        dict(provider="upbit", account="원화코인", marks=[
            dict(symbol="BTC", currency="KRW", qty="0.1", price=Decimal("80000000"), value=Decimal("8000000"),
                 gain=Decimal("0"), rate=Decimal("0"), weight_pct="100", state="시세 반영", instrument=None),
        ]),
        dict(provider="binance", account="현물RWA", marks=[
            dict(symbol="NVDAB", currency="USD", qty="100", price=Decimal("150"), value=Decimal("15000"),
                 gain=Decimal("0"), rate=Decimal("0"), weight_pct="60", state="시세 반영", instrument=("BINANCE_B", "NVDAB", "USD")),
            dict(symbol="BTC", currency="USDT", qty="0.1", price=Decimal("60000"), value=Decimal("6000"),
                 gain=Decimal("0"), rate=Decimal("0"), weight_pct="30", state="시세 반영", instrument=None),
            dict(symbol="USDT", currency="USDT", qty="4000", price=Decimal("1"), value=Decimal("4000"),
                 gain=Decimal("0"), rate=Decimal("0"), weight_pct="10", state="시세 반영", instrument=None),
        ]),
    ]
    strip = live_panel.institutional_risk_strip(accs, qb)
    assert "IPS 팩터 상한(45%) 초과" in strip and "해외거래소·RWA 수탁" in strip and "RP 3.25%" in strip
    ov = live_panel.multi_account_overlap(accs, qb)
    assert "BTC (거래소·통화 통합)" in ov

    cockpit = page.action_cockpit(None, None, "/test", quote_book=qb, accounts=accs)
    assert "CRIX.UPBIT.KRW-BTC" in cockpit
    assert "domestic%2Fstock%2FBTC" not in cockpit

    pos = [
        dict(provider="mirae", account="isa", currency="KRW", role=None, as_of=stamp,
             symbol="267260", tasks={"equities": "증권 계좌 상품 유형 확인"}, weight_pct="90"),
        dict(provider="mirae", account="isa", currency="KRW", role="cash", as_of=stamp,
             symbol="KRW", tasks={}, weight_pct="10"),
        dict(provider="binance", account="spot", currency="USDT", role="crypto", as_of=stamp,
             symbol="USDT", tasks={"crypto": "보유 분석"}, weight_pct="100"),
    ]
    comb = monitor.stress_panel(pos, "/test", "combined")
    assert "복합 위기" in comb and "-31.50%p" in comb and "-5.00%p" in comb

    # Verify US 11/27 Mistake #1 (single-stock token overheat alert) & Mistake #3 (20/60D bull trend-hold upgrade)
    qb_noise = monitor.live_valuation.QuoteBook(rows=[
        dict(venue="fx", symbol="USD/KRW", currency="KRW", price="1336", at=stamp, seen=stamp),
        dict(venue="AMEX", symbol="SPY", currency="USD", price="716.70", at=stamp, seen=stamp),
        dict(venue="NASDAQ", symbol="QQQ", currency="USD", price="633.93", at=stamp, seen=stamp),
        dict(venue="NASDAQ", symbol="NVDA", currency="USD", price="149.30", at=stamp, seen=stamp),
        dict(venue="KRAKEN_X", symbol="SPYX", currency="USD", price="728.62", at=stamp, seen=stamp),
        dict(venue="KRAKEN_X", symbol="QQQX", currency="USD", price="649.50", at=stamp, seen=stamp),
        dict(venue="KRAKEN_X", symbol="NVDAX", currency="USD", price="155.26", at=stamp, seen=stamp),
    ])
    cockpit_noise = page.action_cockpit(None, None, "/test", quote_book=qb_noise, accounts=accs)
    assert "개별토큰 과열착시 주의" in cockpit_noise
