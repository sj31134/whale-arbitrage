from datetime import datetime, timezone
import json

import pytest

from agents import intelligence as intel, market_anomalies as scan
from private_accounts import market_panel, market_review as review

DAY = "2025-05-20"
AT = DAY + "T23:00:00+00:00"
DAYS = {"KR": DAY, "US": DAY}
SOURCE = "https://www.nasdaq.com/market-activity"


def case(**changes):
    base = dict(market="US", day=DAY, symbol="DEMO", kind="종목", evidence="관련 보도", source=SOURCE,
                name="공개 테스트", issue="공시 대기", flow="확인 대기", trend="주간 확인 대기",
                insight="비용 재검토", revisit="다음 거래일", refs=[], change_pct="5")
    return dict(base, **changes)


def test_sample_same_day_spreads_and_previous_volatility():
    assert scan.spread_bps("99", "101") == 200
    with pytest.raises(ValueError):
        scan.spread_bps("101", "99")
    from datetime import timedelta
    end = datetime.fromisoformat(DAY+"T20:00:00+00:00")
    stamps = [(end-timedelta(days=n)).timestamp() for n in reversed(range(23))]
    closes = [100 + i % 3 for i in range(22)] + [140]
    q = dict(high=closes, low=closes, close=closes, volume=[200]*22+[500])
    chart = dict(chart=dict(result=[dict(meta=dict(symbol="DEMO"),timestamp=stamps,
                 indicators=dict(quote=[q],adjclose=[dict(adjclose=closes)]))]))
    one, = scan.chart("US","DEMO","공개","종목",json.dumps(chart),DAY,SOURCE)
    assert one["z"] > 2 and one["volume_multiple"] == 2.5 and "spread_bps" not in one
    assert not scan.chart("US","DEMO","공개","종목",json.dumps(chart),"2025-05-21",SOURCE)


def test_program_validates_units_columns_and_days():
    def tr(cols):
        return "<tr>"+"".join("<td>"+str(x)+"</td>" for x in cols)+"</tr>"
    body = "단위: 백만원<table>"+tr(["차익거래","비차익거래","전체"])+tr(["매도","매수","순매수"]*3)
    body += "".join(tr([d,2,3,1,5,3,-2,7,6,-1]) for d in ("25.05.20","25.05.19","25.05.16","25.05.15","25.05.14"))
    rows = scan.program(body.encode(),DAY,"KOSPI",SOURCE)
    assert [r["five_day_net"] for r in rows] == [5,-10,-5]
    with pytest.raises(ValueError):
        scan.program(body.replace("백만원","주").encode(),DAY,"KOSPI",SOURCE)


def test_cases_are_dated_and_portfolio_is_local(tmp_path,monkeypatch):
    package = tmp_path.resolve()
    sample = dict(section="moves",status="확인",rows=[dict(case(),change_pct=5,basis="공개 표본")])
    review.run_scan(package,DAYS,collector=lambda _:{"demo":sample})
    review.run_scan(package,DAYS,collector=lambda _:{"demo":dict(section="moves",rows=[],status="연결 실패")})
    review.import_cases(package,"market-cases",AT,[case()])
    review.import_cases(package,"market-cases",AT,[case()])
    snapshot = review.snapshot(package)
    assert snapshot["sources"]["demo"]["success"] and snapshot["sources"]["demo"]["status"] == "연결 실패"
    assert len(snapshot["cases"]) == 1
    q = case(bid="100",ask="101",venue="Cboe BZX",observed="2025-05-20T15:45:00-04:00")
    del q["change_pct"]
    review.import_cases(package,"market-cases",AT,[q])
    assert review.snapshot(package)["spreads"][0]["spread_bps"] == 99.502
    with pytest.raises(ValueError):
        review.import_cases(package,"market-cases",AT,[dict(q,day="2025-05-19")])
    with pytest.raises(ValueError):
        review.import_cases(package,"market-cases",AT,[case(source="http://localhost/private")])
    with pytest.raises(ValueError):
        review.import_cases(package,"market-cases",AT,[case(weight="private")])
    portfolio = [dict(provider="mock",account="test",holdings=[dict(symbol="테스트 전용",currency="USD")])]
    monkeypatch.setattr(review.portfolio,"portfolio_accounts",lambda *_:portfolio)
    pid = intel.position_id("mock","test","테스트 전용","USD")
    intel.update_json(package,intel.NOTES,{},lambda _:dict(tags={pid:["underlying:US:DEMO","sector:KR:DEMO"]}))
    review.crosscheck(tmp_path,package)
    assert "테스트 전용" not in json.dumps(review.snapshot(package),ensure_ascii=False)
    matches = intel.private_json(package,review.MATCHES,{})["matched"]
    assert matches and {r["relation"] for r in matches} == {"기초주식"}
    assert "테스트 전용" in market_panel.render(package,"/test","US")
    assert "signal-num up" not in market_panel.render(package,"/test","KR")
    review.run_scan(package,{"KR":"2025-05-21","US":"2025-05-21"},collector=lambda _:{"demo":dict(section="moves",rows=[],status="연결 실패")})
    assert not review.snapshot(package)["cases"] and not review.snapshot(package)["groups"]


def test_market_structure_uses_publication_time_and_selected_market(tmp_path):
    package = tmp_path.resolve()
    review.run_scan(package,DAYS,collector=lambda _: {})
    row = dict(market="KR",venue="KOSPI",kind="거래소 조치",as_of=DAY+"T09:06:00+09:00",
               published=DAY+"T09:11:00+09:00",title="공개 테스트 공지",source=SOURCE,
               implication="장중 관측",revisit="마감 점검")
    review.import_structure(package,"market-structure",AT,[row])
    assert "공개 테스트 공지" in market_panel.render(package,"/sample","KR")
    assert "공개 테스트 공지" not in market_panel.render(package,"/sample","US")
    with pytest.raises(ValueError):
        review.import_structure(package,"market-structure",AT,[dict(row,published=DAY+"T08:00:00+09:00")])


def test_overnight_watch_uses_only_known_same_session_closes(tmp_path):
    def at(value):
        return review.overnight_watch(tmp_path, datetime.fromisoformat(value))

    rows = [case(symbol=symbol, kind=kind, source=url, change_pct="-5")
            for symbol, (kind, url) in review.OVERNIGHT_SAMPLES.items()]
    with pytest.raises(ValueError):
        review.import_cases(tmp_path, "market-cases", AT, [dict(rows[0], symbol="OTHER")])
    review.import_cases(tmp_path, "market-cases", AT, rows[:1])
    assert at(AT)["state"].startswith("판단 보류")
    assert not at("2025-05-21T07:00:00+09:00")["samples"]
    review.import_cases(tmp_path, "market-cases", AT, rows[1:])
    assert at(AT)["state"].startswith("경보")
    assert not at("2025-05-22T08:00:00+09:00")["samples"]
    reviewed = "2025-05-21T08:30:00+09:00"
    intel.update_json(tmp_path, review.FILE, {}, lambda _: dict(feeds={
        "SOXX": dict(success=reviewed, rows=[dict(rows[0], change_pct=-4.99)])}))
    assert at(AT)["state"].startswith("경보")
    assert at(reviewed)["state"] == "동반 급락 조건 미충족"
    assert at(reviewed)["samples"]["SOXX"]["checked"] == reviewed


def test_daily_refresh_collects_only_missing_public_closes(tmp_path, monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromisoformat(AT).astimezone(tz)

    monkeypatch.setattr(review, "datetime", Clock)
    review.import_cases(tmp_path, "market-cases", AT, [case(symbol="NVDA", change_pct="-7")])

    def collect(days, selected):
        assert days["US"] == DAY and selected == {"SOXX"}
        return {"SOXX": dict(status="확인", rows=[case(symbol="SOXX", kind="섹터 ETF 표본", change_pct=-6)])}

    review.refresh_overnight(tmp_path, collector=collect)
    assert review.overnight_watch(tmp_path, Clock.now(timezone.utc))["state"].startswith("경보")
    review.refresh_overnight(tmp_path, collector=lambda *_a, **_k: pytest.fail("duplicate collection"))
