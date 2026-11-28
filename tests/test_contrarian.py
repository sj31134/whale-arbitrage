from datetime import datetime, timedelta
import json
import re
from urllib.parse import urlencode, urlsplit

import pytest

from agents import intelligence
from private_accounts import contrarian, contrarian_page, store


def _fake_yahoo_uncrowded(url):
    # Simulate an uncrowded pre-tenbagger monopoly: 5Y low ~85, 52W peak 200, current selloff to 112 (5Y low mult = 1.32x <= 3.6x)
    if "range=5y" in url:
        closes = [85.0 + 0.3 * (i % 40) for i in range(180)] + [200.0 - 1.1 * i for i in range(80)]
    else:
        closes = [200.0 - 0.52 * i for i in range(170)] + [112.0 + (0.1 if i % 2 == 0 else -0.1) for i in range(82)]
    return json.dumps({"chart": {"result": [{"indicators": {"quote": [{"close": closes}]}}]}}).encode()


def test_contrarian_half_kelly_piotroski_and_dual_time_stop(tmp_path):
    pkg, directory = tmp_path.resolve() / "project", tmp_path.resolve() / "vault"
    pkg.mkdir()
    now = datetime(2026, 11, 28, 19, 35, tzinfo=intelligence.KST)

    # 1. Verify CoT Post-Mortem registry, 6 <=12M archetypes & literature-backed academic research
    assert len(contrarian.AGENT_COT_POSTMORTEM) == 3
    assert len(contrarian.ARCHETYPES) == 6
    assert "greenblatt_catalyst" in contrarian.ARCHETYPES and "nomad_ses" not in contrarian.ARCHETYPES
    assert all(contrarian.parse_horizon_months(a["horizon"]) <= 12 for a in contrarian.ARCHETYPES.values())
    assert len(contrarian.ACADEMIC_RESEARCH) == 4

    # Ex-post tenbaggers AND catalyst-less dead-money traps must be EXCLUDED from the live universe
    universe_syms = {s[0] for s in contrarian.CONTRARIAN_UNIVERSE}
    assert universe_syms.isdisjoint({
        "000660", "003230", "267260", "298040", "012450", "NVDA", "MSFT", "AVGO", "LLY", "TSM",
        "111770", "086280", "241560", "383220", "DECK", "ENTG",
    })
    assert {"214150", "058470", "240810", "000100", "ACLS", "ONTO", "CELH", "FOUR", "LULU", "MOH"} <= universe_syms

    with store.database(directory, True) as db:
        store.save(db, "kis", "main", (now - timedelta(days=1)).isoformat(), [("214150", "KRW", "50", "1135000")])

    doc = contrarian.refresh(pkg, fetcher=_fake_yahoo_uncrowded, now=now)
    assert doc["count"] == 20
    for cand in doc["candidates"]:
        contrarian.validate_contrarian_invariants(cand)
        assert cand["catalyst_months"] <= contrarian.MAX_HORIZON_MONTHS
        assert cand["catalyst_12m"] and cand["time_stop"]
        assert cand["piotroski_3"] in (2, 3)
        if cand["trap_shield_ok"]:
            assert 25.0 <= cand["sizing"]["recommended_pct"] <= 50.0
            assert 0.0 < cand["sizing"]["kelly_half_pct"] < cand["sizing"]["kelly_full_pct"]
    top = doc["candidates"][0]
    assert top["trap_shield_ok"] and top["piotroski_3"] == 3 and not top["ex_tenbagger"]
    assert top["mult_5y_low"] <= contrarian.EX_TENBAGGER_CEILING
    # Piotroski 3/3 candidates sort ahead of 2/3 candidates among passing 6M catalysts
    p3_top = [c for c in doc["candidates"] if c["trap_shield_ok"] and c["piotroski_3"] == 3]
    assert len(p3_top) >= 10

    # 2. CoT-ERR-01 Guardrail: stock already >3.6x above 5Y low is blocked to 0%
    bars_1y = [200.0 - 0.3 * i for i in range(150)] + [150.0 for _ in range(102)]
    bars_5y_run = [20.0] * 50 + [150.0] * 200  # 150 / 20 = 7.5x > 3.6x ceiling
    already_ran = contrarian._score_candidate(contrarian.CONTRARIAN_UNIVERSE[0], bars_1y, 150.0, five_yr_closes=bars_5y_run)
    assert already_ran["ex_tenbagger"] and not already_ran["trap_shield_ok"] and already_ran["sizing"]["recommended_pct"] == 0.0

    # 3. CoT-ERR-02 & Half-Kelly Guardrails: BOTH 5~8% dilution AND >50% Full-Kelly overbetting raise ValueError
    bad_diluted = dict(top, sizing=dict(top["sizing"], recommended_pct=8.0))
    with pytest.raises(ValueError, match="분산 비중"):
        contrarian.validate_contrarian_invariants(bad_diluted)
    bad_overbet = dict(top, sizing=dict(top["sizing"], recommended_pct=65.0))
    with pytest.raises(ValueError, match="Half-Kelly 단일 상한"):
        contrarian.validate_contrarian_invariants(bad_overbet)

    # 4. CoT-ERR-03 Guardrail: >12M multi-year buy-and-hold horizons are strictly rejected
    for bad_horizon in ("24개월", "36개월", "3년", "5~10년 존버", "장기보유"):
        with pytest.raises(ValueError):
            contrarian.parse_horizon_months(bad_horizon)
    assert contrarian.parse_horizon_months("6~9개월") == 9
    assert contrarian.parse_horizon_months("2~3분기") == 9
    assert contrarian.parse_horizon_months("1년") == 12

    # 5. Validate bespoke <=12M Half-Kelly + Piotroski playbook & security checks
    with pytest.raises(ValueError, match="1년"):
        contrarian.save_playbook(pkg, dict(
            market="KR", symbol="058470", name="리노공업", archetype="hynix_bottleneck",
            entry="52400", floor="44000", target="118000", horizon="24개월",
            crowd_view="스마트폰 둔화 우려", variant_insight="AI 칩 R&D 소켓 독점", kill_switch="점유율 이탈",
            url="https://dart.fss.or.kr/",
        ))
    with pytest.raises(ValueError):
        contrarian.save_playbook(pkg, dict(
            market="KR", symbol="058470", name="리노공업", archetype="hynix_bottleneck",
            entry="52400", floor="60000", target="120000", horizon="6~9개월",
            crowd_view="스마트폰 둔화 우려", variant_insight="AI 칩 R&D 소켓 독점", kill_switch="점유율 이탈",
            url="https://dart.fss.or.kr/",
        ))
    with pytest.raises(ValueError):
        contrarian.save_playbook(pkg, dict(
            market="KR", symbol="058470", name="리노공업", archetype="hynix_bottleneck",
            entry="52400", floor="44000", target="120000", horizon="6~9개월",
            crowd_view="스마트폰 둔화 우려", variant_insight="AI 칩 R&D 소켓 독점", kill_switch="점유율 이탈",
            url="http://127.0.0.1/private",
        ))
    saved = contrarian.save_playbook(pkg, dict(
        market="KR", symbol="058470", name="리노공업", archetype="hynix_bottleneck",
        solvency="net_cash", piotroski_3="3", win_prob="65",
        entry="52300", floor="44000", target="118000", horizon="6~9개월",
        catalyst_12m="파업 종료 후 4Q 출하 정상화 + 부산 에코델타시티(EDC) 2배 신공장 가동 및 AI 소켓 수주",
        time_stop="3M 1차 점검(4Q OPM 45%+ 정상화 미확인 시 조기 철수) / 6M 본 Time-Stop(EDC 매출 미확인 시 전량 교체)",
        crowd_view="스마트폰 업황 둔화·일회성 파업 감익으로 -59% 과매도", variant_insight="OPM 47.7% + 2배 증설 가동 임박",
        kill_switch="초미세 소켓 점유율 하락", url="https://dart.fss.or.kr/",
    ))
    assert saved["passes"] and saved["horizon_months"] == 9 and saved["piotroski_3"] == 3
    assert 38.0 <= saved["sizing"]["recommended_pct"] <= 50.0
    t1, t2, t3 = [float(x) for x in saved["tranches"]]
    assert t1 > t2 > t3 >= float(saved["floor"])

    # Distressed / dilution-prone stock is rejected to 0% (never 5% "probe")
    blocked = contrarian.save_playbook(pkg, dict(
        market="KR", symbol="035720", name="모의한계기업", archetype="burry_asymmetry",
        solvency="distressed_block", piotroski_3="1", entry="30000", floor="25000", target="75000", horizon="6개월",
        crowd_view="단순 낙폭과대", variant_insight="비용 절감",
        kill_switch="유상증자", url="https://dart.fss.or.kr/",
    ))
    assert not blocked["passes"] and blocked["sizing"]["recommended_pct"] == 0.0

    # Render /contrarian: held 214150 hidden by default, shown with include_held=1
    html_def = contrarian_page.render(directory, pkg, "/unit", "csrf1", {}, "").decode()
    for keyword in (
        "에이전트 Chain-of-Thought(사고과정) 오류 복기",
        "COT-ERR-03",
        "Half-Kelly",
        "Bessembinder",
        "Piotroski",
        "3M 숫자 점검 + 6M 본 Time-Stop",
        "5%~8% 백화점 분산",
    ):
        assert keyword in html_def
    assert "(214150 ·" not in html_def
    html_inc = contrarian_page.render(directory, pkg, "/unit", "csrf1", {"include_held": "1"}, "").decode()
    assert "(214150 ·" in html_inc and "내 보유 중" in html_inc


def test_contrarian_http_routes_and_csrf(tmp_path, dashboard_http, monkeypatch):
    pkg, directory = tmp_path.resolve() / "project", tmp_path.resolve() / "vault"
    pkg.mkdir()
    monkeypatch.setattr(contrarian, "_default_get", _fake_yahoo_uncrowded)
    with dashboard_http(directory, pkg) as (url, client):
        u = urlsplit(url)

        def req(method, path, fields=None):
            headers = {"Origin": "http://" + u.netloc, "Content-Type": "application/x-www-form-urlencoded"}
            client.request(method, u.path + path, urlencode(fields) if fields else None, headers)
            resp = client.getresponse()
            return resp.status, resp.read().decode(), resp.getheader("Location")

        code, page, _ = req("GET", "/contrarian")
        assert code == 200 and "Half-Kelly 2종목 압축 전략실" in page
        csrf = re.search(r'name="csrf" value="([^"]+)"', page)[1]
        assert req("POST", "/desk/manager/contrarian-run", {"csrf": "bad"})[0] == 403
        st, _, loc = req("POST", "/desk/manager/contrarian-run", {"csrf": csrf})
        assert st == 303 and loc.endswith("/contrarian?done=refreshed")

        # Multi-year horizon via HTTP POST returns 400 validation error
        st_bad, page_bad, _ = req("POST", "/desk/manager/contrarian-plan", {
            "csrf": csrf, "market": "US", "symbol": "LULU", "name": "Lululemon",
            "archetype": "greenblatt_catalyst", "solvency": "net_cash", "piotroski_3": "3", "win_prob": "62",
            "entry": "108", "floor": "92", "target": "220",
            "horizon": "36개월", "crowd_view": "북미 성장 둔화 공포",
            "variant_insight": "무차입 ROIC 30%+", "kill_switch": "마진 붕괴",
            "url": "https://www.sec.gov/edgar/searchedgar/companysearch",
        })
        assert st_bad == 400 and "1년 내 승부 원칙 위반" in page_bad

        st2, _, loc2 = req("POST", "/desk/manager/contrarian-plan", {
            "csrf": csrf, "market": "US", "symbol": "ONTO", "name": "Onto Innovation",
            "archetype": "hynix_bottleneck", "solvency": "net_cash", "piotroski_3": "3", "win_prob": "64",
            "entry": "178.42", "floor": "152.00", "target": "320.00",
            "horizon": "6~9개월",
            "catalyst_12m": "4Q 매출 $430~450M 가이던스 + $1.3B 수주잔고 기반 2027 Dragonfly G5 2배 PO 가동",
            "time_stop": "3M 1차 점검: 4Q 총마진 56%+ 유지 확인 / 6M 본 Time-Stop: 패키징 수주잔고 꺾임 시 즉시 교체",
            "crowd_view": "반도체 장비 섹터 투매로 3Q26 매출 +88% 사상최대에도 52주 고점 대비 반토막",
            "variant_insight": "HBM4·CoWoS 수율 독점 계측 백로그 $1.3B 확보 (Piotroski 3/3 최고 기대오차)",
            "kill_switch": "Dragonfly G5 고객사 발주 취소", "url": "https://www.sec.gov/edgar/searchedgar/companysearch",
        })
        assert st2 == 303 and loc2.endswith("/contrarian?done=saved#my-playbooks")
        code3, page3, _ = req("GET", "/contrarian")
        assert code3 == 200 and "Onto Innovation (US:ONTO)" in page3 and "Piotroski 3/3" in page3 and "Half-Kelly" in page3
