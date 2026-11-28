from datetime import datetime
import json
import re
from urllib.parse import urlencode, urlsplit

from agents import intelligence as intel
from private_accounts import tournament


def test_tournament_knockout_and_regime_switch(tmp_path):
    pkg = tmp_path.resolve() / "project"
    pkg.mkdir()

    # Stage realistic cached radar (1 clean winner NVO + G2/Piotroski2/overheated knockouts) + Phase 1 discovery
    intel.update_json(pkg, "contrarian_radar.json", {}, lambda _: {
        "updated": "2026-11-28T23:00:00+09:00",
        "candidates": [
            {
                "symbol": "NVO", "market": "US", "currency": "USD", "name": "Novo Nordisk",
                "piotroski_3": 3, "gov_tier": "G1", "total": 92.0, "trap_shield_ok": True,
                "sizing": {"recommended_pct": 32.0}, "catalyst_12m": "3Q adjusted OP +27% & Wegovy Pill ramp",
                "crowd_fear": "29개월 소화",
            },
            {
                "symbol": "FOUR", "market": "US", "currency": "USD", "name": "Shift4 Payments",
                "piotroski_3": 3, "gov_tier": "G1", "total": 86.2, "trap_shield_ok": True,
                "sizing": {"recommended_pct": 32.2}, "catalyst_12m": "Q1 $1B buyback",
                "crowd_fear": "FX noise",
            },
            {
                "symbol": "103140", "market": "KR", "currency": "KRW", "name": "풍산",
                "piotroski_3": 3, "gov_tier": "G2", "total": 80.5, "trap_shield_ok": False,
                "sizing": {"recommended_pct": 0.0}, "crowd_fear": "[낙하하는 칼날 차단: 20·60일선 동시 하회]",
            },
            {
                "symbol": "035900", "market": "KR", "currency": "KRW", "name": "JYP Ent.",
                "piotroski_3": 3, "gov_tier": "G0", "total": 78.0, "trap_shield_ok": False,
                "sizing": {"recommended_pct": 0.0}, "crowd_fear": "[단기 과열(RSI 73) — 조정 대기]",
            },
            {
                "symbol": "259960", "market": "KR", "currency": "KRW", "name": "크래프톤",
                "piotroski_3": 2, "gov_tier": "G1", "total": 85.2, "trap_shield_ok": True,
                "sizing": {"recommended_pct": 35.0}, "crowd_fear": "3Q -35.5% 일시 감속",
            },
        ],
    })

    intel.update_json(pkg, "market_discovery.json", {}, lambda _: {
        "updated": "2026-11-28T23:00:00+09:00",
        "context": {"kr_bench_ret20": -15.5, "us_bench_ret20": -5.6},
        "candidates": [
            {"symbol": "012450", "market": "KR", "name": "한화에어로스페이스", "score": 85.9, "theme": "방산·우주"},
            {"symbol": "COST", "market": "US", "name": "Costco", "score": 82.0, "theme": "필수소비 요새"},
        ],
    })

    now = datetime(2026, 11, 29, 0, 58, tzinfo=intel.KST)
    board = tournament.run_tournament(pkg, now=now)
    assert board["stocks"]["champion"]["symbol"] == "NVO"
    assert board["stocks"]["champion"]["recommended_pct"] == 32.0
    assert board["stocks"]["contrarian_pass_count"] == 2
    assert board["stocks"]["eliminated_count"] == 3
    assert board["strategies"]["champion"]["key"] == "variance-cap"  # Phase 1 Defense wins
    assert "30분" in board["patterns"]["champion"]["rule"]
    assert len(tournament.history(pkg)) == 1

    # Flip macro regime to Phase 2 Recovery and confirm strategy champion hands over to downside-cap
    intel.update_json(pkg, "market_discovery.json", {}, lambda _: {
        "updated": "2026-12-10T23:00:00+09:00",
        "context": {"kr_bench_ret20": 8.4, "us_bench_ret20": 4.2},
        "candidates": [
            {"symbol": "012450", "market": "KR", "name": "한화에어로스페이스", "score": 86.0, "theme": "방산·우주"},
            {"symbol": "COST", "market": "US", "name": "Costco", "score": 79.0, "theme": "필수소비 요새"},
        ],
    })
    board2 = tournament.run_tournament(pkg, now=now)
    assert board2["strategies"]["champion"]["key"] == "downside-cap"
    assert len(tournament.history(pkg)) == 2


def test_tournament_http_route_csrf_and_manager_banner(tmp_path, dashboard_http):
    pkg, directory = tmp_path.resolve() / "project", tmp_path.resolve() / "vault"
    pkg.mkdir()
    with dashboard_http(directory, pkg) as (url, client):
        u = urlsplit(url)

        def req(method, path, fields=None):
            headers = {"Origin": "http://" + u.netloc, "Content-Type": "application/x-www-form-urlencoded"}
            client.request(method, u.path + path, urlencode(fields) if fields else None, headers)
            resp = client.getresponse()
            return resp.status, resp.read().decode(), resp.getheader("Location")

        code, page, _ = req("GET", "/tournament")
        assert code == 200 and "누적 종목·전략·패턴 토너먼트 결승실" in page
        csrf = re.search(r'name="csrf" value="([^"]+)"', page)[1]
        assert req("POST", "/desk/manager/tournament-run", {"csrf": "invalid"})[0] == 403

        st, _, loc = req("POST", "/desk/manager/tournament-run", {"csrf": csrf})
        assert st == 303 and loc.endswith("/tournament?done=battled")

        code2, page2, _ = req("GET", "/tournament?done=battled")
        assert code2 == 200 and "재배틀 및 로그 기록을 완료" in page2 and len(tournament.history(pkg)) >= 1

        code_mgr, page_mgr, _ = req("GET", "/desk/manager")
        assert code_mgr == 200 and 'id="tournament-champions"' in page_mgr and "🏆 최종 우승" in page_mgr
