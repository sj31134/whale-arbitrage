from datetime import datetime, timedelta, timezone
import json
from urllib.parse import urlencode, urlsplit

import pytest

from agents import intelligence
from private_accounts import discovery, discovery_page, live_valuation, store


def _fake_fetcher(url):
    if "apewisdom.io" in url:
        return json.dumps({
            "results": [
                {"rank": 1, "ticker": "NVDA", "name": "NVIDIA", "mentions": 200, "upvotes": 5000, "mentions_24h_ago": 150},
                {"rank": 2, "ticker": "PLTR", "name": "Palantir", "mentions": 120, "upvotes": 3100, "mentions_24h_ago": 90},
            ]
        }).encode()
    if "/stocks/up/" in url or "/stocks/marketValue/" in url:
        return json.dumps({"stocks": []}).encode()
    if "/integration" in url:
        code = url.split("/stock/")[1].split("/")[0]
        return json.dumps({
            "itemCode": code,
            "totalInfos": [{"code": "accumulatedTradingValue", "value": "1,800억"}, {"code": "lastClosePrice", "value": "650,000"}],
            "dealTrendInfos": [
                {"foreignerPureBuyQuant": "+15,000", "organPureBuyQuant": "+12,000"} for _ in range(5)
            ],
            "consensusInfo": {"priceTargetMean": "950,000"},
        }).encode()
    if "/basic" in url:
        return json.dumps({"closePrice": "650,000"}).encode()
    if "siseJson.nhn" in url:
        rows = [["날짜", "시가", "고가", "저가", "종가", "거래량"]]
        base = 500000 if "069500" not in url else 70000
        step = 4000 if "069500" not in url else 100
        for i in range(65):
            d = (datetime(2026, 9, 1) + timedelta(days=i)).strftime("%Y%m%d")
            px = base + i * step
            rows.append([d, px, px + 500, px - 500, px, 100000])
        return repr(rows).encode()
    if "finance.yahoo.com" in url:
        base = 100.0
        step = 1.2 if "SPY" not in url else 0.2
        ts = [int((datetime(2026, 9, 1, tzinfo=timezone.utc) + timedelta(days=i)).timestamp()) for i in range(65)]
        closes = [base + i * step for i in range(65)]
        vols = [1_000_000 + (200_000 if i % 2 == 0 else 0) for i in range(65)]
        return json.dumps({
            "chart": {"result": [{"timestamp": ts, "indicators": {"quote": [{"open": closes, "high": closes, "low": closes, "close": closes, "volume": vols}]}}]}
        }).encode()
    raise OSError(url)


def test_six_axis_discovery_streaks_sns_and_portfolio_exclusion(tmp_path):
    pkg, directory = tmp_path.resolve() / "project", tmp_path.resolve() / "vault"
    pkg.mkdir()
    now = datetime(2026, 11, 26, 12, 0, tzinfo=intelligence.KST)

    # Seed public geopolitical & macro cache
    intelligence.update_json(pkg, intelligence.CACHE, {}, lambda _: {
        "global_events/un_security": {"status": "수집 완료", "items": [{"title": "UN security military defense alert", "origin": "https://news.un.org/en/story/1"}]},
        "policy/fed": {"status": "수집 완료", "items": [{"title": "Federal Reserve rate statement", "origin": "https://www.federalreserve.gov/feeds/press_monetary.xml"}]},
    })

    # Seed a private holding (005930 and NVDA) in vault to verify non-portfolio exclusion at render time
    with store.database(directory, True) as db:
        store.save(db, "kis", "main", (now - timedelta(days=1)).isoformat(), [
            ("005930", "KRW", "10", "1700000"),
            ("NVDA", "USD", "5", "750"),
        ])
    with live_valuation.connection(pkg, write=True) as qdb:
        qdb.execute(live_valuation.UPSERT, dict(
            venue="KRX", symbol="005930", currency="KRW", name="삼성전자", english="",
            price="175000", at=now.isoformat(), session="OPEN", delay="", feed="KOSPI", page=1, seen=now.isoformat()
        ))

    day1 = discovery.refresh(pkg, fetcher=_fake_fetcher, now=now)
    assert day1["candidates"] and any(c["symbol"] == "012450" for c in day1["candidates"])
    hanwha = next(c for c in day1["candidates"] if c["symbol"] == "012450")
    assert hanwha["scores"]["flow"] > 20 and hanwha["scores"]["geo"] >= 8.5 and hanwha["streak"] == 1

    # Next day run increments streak
    day2 = discovery.refresh(pkg, fetcher=_fake_fetcher, now=now + timedelta(days=1))
    hanwha2 = next(c for c in day2["candidates"] if c["symbol"] == "012450")
    assert hanwha2["streak"] == 2 and not hanwha2["is_new"]

    # Record SNS overheat note and verify validation + score adjustment
    with pytest.raises(ValueError):
        discovery.record_sns_note(pkg, dict(market="KR", symbol="012450", tone="호재 확산", summary="루머", url="http://localhost/bad"))
    discovery.record_sns_note(pkg, dict(market="KR", symbol="012450", tone="과열·설거지 주의", summary="단기 루머 급증", url="https://x.com/example/status/1"))
    day3 = discovery.refresh(pkg, fetcher=_fake_fetcher, now=now + timedelta(days=1, hours=1))
    hanwha3 = next(c for c in day3["candidates"] if c["symbol"] == "012450")
    assert hanwha3["scores"]["sns"] < hanwha2["scores"]["sns"] and "과열·설거지 주의" in hanwha3["sns_note"]

    # Render /discover: held 005930 and NVDA must be excluded by default, shown only when include_held=1
    html_default = discovery_page.render(directory, pkg, "/unit", "csrf1", {}, "").decode()
    assert "한화에어로스페이스" in html_default and "내 보유 2종목 자동 제외" in html_default
    assert "(005930)" not in html_default and "(NVDA)" not in html_default
    html_with_held = discovery_page.render(directory, pkg, "/unit", "csrf1", {"include_held": "1"}, "").decode()
    assert "내 보유 중" in html_with_held


def test_discover_http_routes_and_csrf(tmp_path, dashboard_http, monkeypatch):
    pkg, directory = tmp_path.resolve() / "project", tmp_path.resolve() / "vault"
    pkg.mkdir()
    monkeypatch.setattr(discovery, "_default_get", _fake_fetcher)
    with dashboard_http(directory, pkg) as (url, client):
        u = urlsplit(url)

        def req(method, path, fields=None):
            headers = {"Origin": "http://" + u.netloc, "Content-Type": "application/x-www-form-urlencoded"}
            client.request(method, u.path + path, urlencode(fields) if fields else None, headers)
            resp = client.getresponse()
            return resp.status, resp.read().decode(), resp.getheader("Location")

        code, page, _ = req("GET", "/discover")
        assert code == 200 and "포트폴리오 외 신규 대장주 발굴" in page
        import re
        csrf = re.search(r'name="csrf" value="([^"]+)"', page)[1]
        assert req("POST", "/desk/manager/discover-run", {"csrf": "wrong"})[0] == 403
        status, _, loc = req("POST", "/desk/manager/discover-run", {"csrf": csrf})
        assert status == 303 and loc.endswith("/discover?done=refreshed")
        status, _, loc = req("POST", "/desk/manager/discover-sns", {
            "csrf": csrf, "market": "US", "symbol": "PLTR", "tone": "호재 확산",
            "summary": "국방 AI 수주 확대 언급", "url": "https://x.com/example/status/2",
        })
        assert status == 303 and loc.endswith("/discover?done=sns#sns-radar")
        code, updated, _ = req("GET", "/discover?market=US")
        assert code == 200 and "Palantir" in updated and "국방 AI 수주 확대 언급" in updated
