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
