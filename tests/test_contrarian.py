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


def test_contrarian_high_conviction_sizing_and_anti_hindsight_universe(tmp_path):
    pkg, directory = tmp_path.resolve() / "project", tmp_path.resolve() / "vault"
    pkg.mkdir()
    now = datetime(2026, 11, 28, 11, 15, tzinfo=intelligence.KST)

    # 1. Verify 6 legendary archetypes & 4 academic research papers
    assert len(contrarian.ARCHETYPES) == 6
    assert len(contrarian.ACADEMIC_RESEARCH) == 4
    # Ex-post tenbagger mega-caps must be EXCLUDED from the live discovery universe
    universe_syms = {s[0] for s in contrarian.CONTRARIAN_UNIVERSE}
    assert universe_syms.isdisjoint({"000660", "003230", "267260", "298040", "012450", "NVDA", "MSFT", "AVGO", "LLY", "TSM"})
    assert {"214150", "058470", "103140", "ACLS", "ONTO", "LULU", "BABA", "MOH"} <= universe_syms

    with store.database(directory, True) as db:
        store.save(db, "kis", "main", (now - timedelta(days=1)).isoformat(), [("214150", "KRW", "50", "1135000")])

    doc = contrarian.refresh(pkg, fetcher=_fake_yahoo_uncrowded, now=now)
    assert doc["count"] == 20
    top = doc["candidates"][0]
    assert top["trap_shield_ok"] and not top["ex_tenbagger"]
    assert top["mult_5y_low"] <= contrarian.EX_TENBAGGER_CEILING
    # High-conviction sizing MUST be 30%~75% (never single-digit 5%~8%!)
    assert 30.0 <= top["sizing"]["recommended_pct"] <= 75.0

    # 2. Anti-Hindsight Guardrail: stock already 6.5x above 5Y low is automatically blocked from fresh tenbagger pass
    bars_1y = [200.0 - 0.3 * i for i in range(150)] + [150.0 for _ in range(102)]
    bars_5y_run = [20.0] * 50 + [150.0] * 200  # 150 / 20 = 7.5x > 3.6x ceiling
    already_ran = contrarian._score_candidate(contrarian.CONTRARIAN_UNIVERSE[0], bars_1y, 150.0, five_yr_closes=bars_5y_run)
    assert already_ran["ex_tenbagger"] and not already_ran["trap_shield_ok"] and already_ran["sizing"]["recommended_pct"] == 0.0

    # 3. Validate bespoke 1-stock high-conviction playbook & security checks
    with pytest.raises(ValueError):
        contrarian.save_playbook(pkg, dict(
            market="KR", symbol="058470", name="리노공업", archetype="hynix_bottleneck",
            entry="52400", floor="60000", target="120000", horizon="24개월",
            crowd_view="스마트폰 둔화 우려", variant_insight="AI 칩 R&D 소켓 독점", kill_switch="점유율 이탈",
            url="https://dart.fss.or.kr/",
        ))
    with pytest.raises(ValueError):
        contrarian.save_playbook(pkg, dict(
            market="KR", symbol="058470", name="리노공업", archetype="hynix_bottleneck",
            entry="52400", floor="44000", target="120000", horizon="24개월",
            crowd_view="스마트폰 둔화 우려", variant_insight="AI 칩 R&D 소켓 독점", kill_switch="점유율 이탈",
            url="http://127.0.0.1/private",
        ))
    saved = contrarian.save_playbook(pkg, dict(
        market="KR", symbol="058470", name="리노공업", archetype="druckenmiller_inflection",
        solvency="net_cash", win_prob="65",
        entry="52400", floor="44000", target="118000", horizon="24개월",
        crowd_view="스마트폰 업황 둔화와 묶여 반토막 소외", variant_insight="빅테크 자체 AI ASIC 테스트 소켓 톨게이트 독점",
        kill_switch="초미세 소켓 점유율 하락", url="https://dart.fss.or.kr/",
    ))
    assert saved["passes"] and saved["sizing"]["recommended_pct"] >= 50.0
    t1, t2, t3 = [float(x) for x in saved["tranches"]]
    assert t1 > t2 > t3 >= float(saved["floor"])

    # Distressed / dilution-prone stock is rejected to 0% (never 5% "probe")
    blocked = contrarian.save_playbook(pkg, dict(
        market="KR", symbol="035720", name="모의한계기업", archetype="burry_asymmetry",
        solvency="distressed_block", entry="30000", floor="25000", target="75000", horizon="12개월",
        crowd_view="단순 낙폭과대", variant_insight="비용 절감",
        kill_switch="유상증자", url="https://dart.fss.or.kr/",
    ))
    assert not blocked["passes"] and blocked["sizing"]["recommended_pct"] == 0.0

    # Render /contrarian: held 214150 hidden by default, shown with include_held=1
    html_def = contrarian_page.render(directory, pkg, "/unit", "csrf1", {}, "").decode()
    for keyword in ("스탠리 드러큰밀러", "닉 슬립", "모니시 파브라이", "Best Ideas", "기성 텐베거·초대형주 목록", "한 자릿수 5%~8% 백화점식 분산 금지"):
        assert keyword in html_def
    assert "(214150)" not in html_def
    html_inc = contrarian_page.render(directory, pkg, "/unit", "csrf1", {"include_held": "1"}, "").decode()
    assert "(214150)" in html_inc and "내 보유 중" in html_inc


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
        assert code == 200 and "미개화 시선괴리 발굴" in page
        csrf = re.search(r'name="csrf" value="([^"]+)"', page)[1]
        assert req("POST", "/desk/manager/contrarian-run", {"csrf": "bad"})[0] == 403
        st, _, loc = req("POST", "/desk/manager/contrarian-run", {"csrf": csrf})
        assert st == 303 and loc.endswith("/contrarian?done=refreshed")

        st2, _, loc2 = req("POST", "/desk/manager/contrarian-plan", {
            "csrf": csrf, "market": "US", "symbol": "LULU", "name": "Lululemon",
            "archetype": "nomad_ses", "solvency": "net_cash", "win_prob": "62",
            "entry": "108", "floor": "92", "target": "220",
            "horizon": "36개월", "crowd_view": "북미 성장 둔화 과장 공포로 5년 바닥 추락",
            "variant_insight": "무차입 ROIC 30%+ 브랜드 해자 및 중국 고성장·자사주 소각",
            "kill_switch": "매출총이익률 구조적 붕괴", "url": "https://www.sec.gov/edgar/searchedgar/companysearch",
        })
        assert st2 == 303 and loc2.endswith("/contrarian?done=saved#my-playbooks")
        code3, page3, _ = req("GET", "/contrarian")
        assert code3 == 200 and "Lululemon (US:LULU)" in page3 and "단독 초집중" in page3
