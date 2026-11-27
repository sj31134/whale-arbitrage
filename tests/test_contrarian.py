from datetime import datetime, timedelta, timezone
import json
import re
from urllib.parse import urlencode, urlsplit

import pytest

from agents import intelligence
from private_accounts import contrarian, contrarian_page, store


def _fake_yahoo_1y(url):
    # Simulate a high-moat stock that suffered a -42% crowd selloff from 52w high (prime contrarian gap)
    closes = [200.0 - 0.5 * i for i in range(170)] + [115.0 + (0.1 if i % 2 == 0 else -0.1) for i in range(82)]
    return json.dumps({"chart": {"result": [{"indicators": {"quote": [{"close": closes}]}}]}}).encode()


def test_contrarian_gap_scanner_and_bespoke_1stock_playbook(tmp_path):
    pkg, directory = tmp_path.resolve() / "project", tmp_path.resolve() / "vault"
    pkg.mkdir()
    now = datetime(2026, 11, 27, 21, 0, tzinfo=intelligence.KST)

    with store.database(directory, True) as db:
        store.save(db, "kis", "main", (now - timedelta(days=1)).isoformat(), [("005935", "KRW", "10", "1400000")])

    doc = contrarian.refresh(pkg, fetcher=_fake_yahoo_1y, now=now)
    assert doc["count"] >= 15
    top = doc["candidates"][0]
    assert top["scores"]["essence"] >= 29 and top["scores"]["gap"] >= 20
    assert top["asymmetry"] >= 3.0 and len(top["tranches"]) == 3

    # Validate bespoke 1-stock playbook creation & security checks
    with pytest.raises(ValueError):
        contrarian.save_playbook(pkg, dict(
            market="KR", symbol="000660", name="SK하이닉스", archetype="hynix_bottleneck",
            entry="100000", floor="120000", target="200000", horizon="24개월",
            crowd_view="적자 우려", variant_insight="HBM 병목 독점", kill_switch="점유율 붕괴",
            url="https://dart.fss.or.kr/",
        ))
    with pytest.raises(ValueError):
        contrarian.save_playbook(pkg, dict(
            market="KR", symbol="000660", name="SK하이닉스", archetype="hynix_bottleneck",
            entry="100000", floor="80000", target="220000", horizon="24개월",
            crowd_view="적자 우려", variant_insight="HBM 병목 독점", kill_switch="점유율 붕괴",
            url="http://127.0.0.1/private",
        ))
    saved = contrarian.save_playbook(pkg, dict(
        market="KR", symbol="000660", name="SK하이닉스", archetype="hynix_bottleneck",
        entry="100000", floor="80000", target="220000", horizon="24개월",
        crowd_view="레거시 D램 적자 공포로 기관 매도", variant_insight="HBM3E·HBM4 독점 수율 및 물리적 병목",
        kill_switch="AI 서버 CapEx 역성장 전환", url="https://dart.fss.or.kr/",
    ))
    assert saved["passes"] and saved["asymmetry"] == 6.0 and len(contrarian.playbooks(pkg)) == 1

    # Render /contrarian: held 005935 hidden by default, shown with include_held=1
    html_def = contrarian_page.render(directory, pkg, "/unit", "csrf1", {}, "").decode()
    assert "캄투자일임 이호걸" in html_def and "마이클 버리" in html_def and "가치함정" in html_def
    assert "(005935)" not in html_def
    assert "비대칭 배수 6.00배" in html_def
    html_inc = contrarian_page.render(directory, pkg, "/unit", "csrf1", {"include_held": "1"}, "").decode()
    assert "(005935)" in html_inc and "내 보유 중" in html_inc


def test_contrarian_http_routes_and_csrf(tmp_path, dashboard_http, monkeypatch):
    pkg, directory = tmp_path.resolve() / "project", tmp_path.resolve() / "vault"
    pkg.mkdir()
    monkeypatch.setattr(contrarian, "_default_get", _fake_yahoo_1y)
    with dashboard_http(directory, pkg) as (url, client):
        u = urlsplit(url)

        def req(method, path, fields=None):
            headers = {"Origin": "http://" + u.netloc, "Content-Type": "application/x-www-form-urlencoded"}
            client.request(method, u.path + path, urlencode(fields) if fields else None, headers)
            resp = client.getresponse()
            return resp.status, resp.read().decode(), resp.getheader("Location")

        code, page, _ = req("GET", "/contrarian")
        assert code == 200 and "역발상 · 시장 괴리" in page
        csrf = re.search(r'name="csrf" value="([^"]+)"', page)[1]
        assert req("POST", "/desk/manager/contrarian-run", {"csrf": "bad"})[0] == 403
        st, _, loc = req("POST", "/desk/manager/contrarian-run", {"csrf": csrf})
        assert st == 303 and loc.endswith("/contrarian?done=refreshed")

        st2, _, loc2 = req("POST", "/desk/manager/contrarian-plan", {
            "csrf": csrf, "market": "US", "symbol": "GOOG", "name": "Alphabet",
            "archetype": "burry_asymmetry", "entry": "270", "floor": "235", "target": "460",
            "horizon": "18개월", "crowd_view": "반독점 해체 과장 공포", "variant_insight": "검색 현금흐름 + TPU 저평가",
            "kill_switch": "검색 점유율 구조적 붕괴", "url": "https://www.sec.gov/edgar/searchedgar/companysearch",
        })
        assert st2 == 303 and loc2.endswith("/contrarian?done=saved#my-playbooks")
        code3, page3, _ = req("GET", "/contrarian")
        assert code3 == 200 and "반독점 해체 과장 공포" in page3 and "Alphabet (US:GOOG)" in page3
