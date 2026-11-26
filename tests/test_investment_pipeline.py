import http.client
import json
import re
import socket
import threading
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urlencode, urlsplit

import pytest

from agents import analyst_feeds as feeds, intelligence as intel
from private_accounts import monitor, store, view


@pytest.fixture
def local(tmp_path):
    package = tmp_path.resolve() / "project/private_accounts"
    package.mkdir(parents=True)
    directory = tmp_path.resolve() / "vault"
    now = store.timestamp(datetime.now(timezone.utc).isoformat())
    with store.database(directory, True) as con:
        for provider, rows in [
            ("kis", [("ALPHA", "USD", "1", "60"), ("USD", "USD", "1", "40"), ("LUNR", "KRW", "1", None)]),
            ("namuh", [("PROPERTY", "KRW", "1", "300")]),
            ("upbit", [("UNIT", "KRW", "1", "10")]),
        ]:
            store.save(con, provider, "main", now, rows)
    return directory, package


def test_private_quote_table_shows_source_time_and_provisional_match(local):
    _, package = local
    assert "저장된 보유 종목 시세 점검이 없습니다" in monitor.market_marks_panel(package)
    stamp = "2026-07-01T01:15:00+00:00"
    row = dict(provider="kis", account="test", symbol="<sample>", name="Sample", code="FAKE",
               match="코드 확인 전", currency="KRW", price="10250", pnl=None, unit_target="7400.5", stamp=stamp)
    intel.update_json(package, "portfolio_market_marks.json", {},
                      lambda _: dict(checked=stamp, balances_as_of="2026-06-30T11:00:00+00:00", rows=[row]))
    html = monitor.market_marks_panel(package)
    for label in ("2026-07-01 10:15 KST", "2026-06-30 20:00 KST", "&lt;sample&gt;", "코드 확인 전",
                  "10,250", "미평가", "7,400.5"):
        assert label in html
    assert "<sample>" not in html


def public_fixture(s):
    # The collector interface only receives its static, public source definition.
    assert set(s) <= {"id", "label", "url", "kind", "unit"}
    if s["kind"] == "fred":
        return ("observation_date," + s["id"] + "\n2025-01-01,4\n2025-02-01,4.5\n").encode()
    if s["kind"] == "rss":
        return b"<rss><channel><item><title>Release</title><pubDate>Wed, 01 Jan 2025 00:00:00 GMT</pubDate><link>https://example.org/a</link></item></channel></rss>"
    if s["kind"] == "atom":
        return b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>10-Q - Issuer (0000001234)</title><updated>2025-01-01T00:00:00Z</updated><link href="https://example.org/f"/></entry></feed>'
    docs = {
        "votes": [dict(Date="2025-01-01", Title="Vote", DivisionId=1, AyeCount=3, NoCount=2)],
        "x": {"data": [{"trend_name": "#ALPHA", "tweet_count": 350}]},
        "dart": {
            "status": "000",
            "list": [
                dict(
                    corp_name="ALPHA",
                    report_nm="보고서",
                    stock_code="000001",
                    rcept_no="20250101000123",
                    rcept_dt="20250101",
                )
            ],
        },
        "upbit": [
            dict(market="KRW-UNIT", trade_timestamp=1735689600000, trade_price=120, signed_change_rate=0.2)
        ],
    }
    return json.dumps(docs[s["kind"]]).encode()


def test_ten_analysts_five_agents_and_private_joins(local):
    directory, package = local
    states = intel.collect(package, fetcher=public_fixture)
    assert set(states.values()) == {"수집 완료"}
    b = intel.board(directory, package)
    assert len(b["categories"]) == 10 and all(c["observations"] for c in b["categories"].values())
    with_property = next(p for p in b["positions"] if p["symbol"] == "PROPERTY")
    intel.manage(directory, package, dict(action="role", position=with_property["id"], role="real_estate"))
    briefs = {agent: intel.agent_brief(directory, package, agent) for agent in intel.DOMAINS}
    assert all(b["positions"] for b in briefs.values())
    equity = next(r for r in briefs["equities"]["positions"] if r["symbol"] == "ALPHA")
    assert equity["weight_pct"] == "60" and equity["evidence"]["fundamentals"][0]["title"].startswith("ALPHA")
    assert equity["evidence"]["social"] and "market_flow" not in equity["evidence"]
    assert briefs["equities"]["categories"]["macro"]["context"][0]["stale"]
    (whale,) = briefs["whale"]["positions"]
    assert whale["symbol"] == "UNIT" and whale["evidence"]["market_flow"][0]["value"] == "120 KRW"
    assert "ALPHA" not in json.dumps(briefs["whale"], ensure_ascii=False)
    (beta,) = briefs["us_small_cap_high_beta"]["positions"]
    assert beta["weight_pct"] is None and "검증" in beta["task"]
    b = intel.board(directory, package)
    assert ("USD", "100") in monitor.totals(b["accounts"])
    assert (package / ".local" / intel.CACHE).stat().st_mode & 0o777 == 0o600


def test_market_checkpoint_cutoff_and_desk_scope(local):
    from datetime import timedelta
    from agents import research_chat
    from private_accounts import chat_page

    directory, package = local
    cutoff = datetime.now(intel.KST).replace(second=0, microsecond=0)
    row = dict(title="모의 지수", value="100 pt", analysis="1분봉 종가", origin="https://example.org/index",
               as_of=(cutoff - timedelta(minutes=1)).isoformat(), known_at=cutoff.isoformat(), domains=["equities"])
    intel.record_market_check(package, cutoff, [row])
    with pytest.raises(ValueError):
        intel.record_market_check(package, cutoff, [dict(row, known_at=(cutoff + timedelta(seconds=1)).isoformat())])
    page = chat_page.market_panel(package)
    assert "100 pt" in page and "한국시간 기준" in page and "원문 확인" in page
    board = intel.board(directory, package)
    for desk in ("equities", "whale"):
        facts = research_chat.research_input(board, desk)["facts"]
        assert any(f["title"] == "모의 지수" and f["scope"] == "공통 시장 자료" for f in facts) == (desk == "equities")


def test_refresh_failure_retains_prior_observations(local):
    _, package = local
    intel.collect(package, "macro", fetcher=public_fixture)

    def outage(source):
        raise OSError("secret internal error")

    states = intel.collect(package, "macro", fetcher=outage)
    assert all("secret" not in v for v in states.values())
    cache = intel.private_json(package, intel.CACHE, {})
    assert len(cache) == 2
    (obs,) = cache["macro/UNRATE"]["items"]
    assert obs["value"] == "4.5 %" and "+0.5 %p" in obs["analysis"]
    assert cache["macro/UNRATE"]["attempt"] >= cache["macro/UNRATE"]["collected"]


def test_verified_quotes_survive_dns_failure_and_do_not_duplicate_api(local, monkeypatch, capsys):
    import io
    from urllib.error import URLError
    from private_accounts.__main__ import run

    directory, package = local
    intel.collect(package, "market_flow", fetcher=public_fixture)
    quote = dict(market="KRW-UNIT", trade_timestamp=1735776000000, trade_price=125, signed_change_rate=0.25)
    checked = "2025-01-03T00:00:00Z"
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps([quote])))
    run(["research-import", "upbit", "--checked-at", checked], directory, package.parent)
    result = capsys.readouterr().out
    assert "1건 저장" in result and "UNIT" not in result
    saved = intel.private_json(package, intel.CAPTURE_FILE, {})
    for stamp, rows in [
        ("2025-01-02T12:00:00Z", [quote]),
        (checked, [dict(quote, trade_price=126)]),
        ("2025-01-04T00:00:00Z", [dict(quote, trade_timestamp=1735689600000)]),
        (checked, [quote, quote]),
        (checked, [dict(quote, trade_timestamp=10**30)]),
        (checked, [dict(quote, trade_price="invalid")]),
    ]:
        with pytest.raises(ValueError):
            intel.import_capture(package, "upbit", stamp, rows)
    assert saved == intel.private_json(package, intel.CAPTURE_FILE, {})

    def offline(_):
        raise URLError(socket.gaierror("private details"))

    intel.collect(package, "market_flow", fetcher=offline)
    category = intel.board(directory, package)["categories"]["market_flow"]
    quote_row, = [r for r in category["observations"] if r.get("source_id") == "upbit"]
    assert quote_row["value"] == "125 KRW"
    runs = [r for r in category["runs"] if r["source_id"] == "upbit"]
    assert {(r["via"], r["status"]) for r in runs} == {
        ("공개 API", "원천 도메인 이름 조회 실패(DNS)"), ("공식 화면 확인", "수집 완료")}


def test_official_filing_import_preserves_desk_scope_and_rejects_wrong_origins(local):
    directory, package = local
    checked = "2025-01-03T00:00:00Z"
    dart = dict(company="ALPHA", title="분기보고서", day="2025.01.01", time="11:30",
                url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20250101000123")
    edgar = dict(title="10-Q/A - Example (0000001234) (Filer)", time="2025-01-01T11:35:00-05:00",
                 url="https://www.sec.gov/Archives/edgar/data/1234/000000123425000001/0000001234-25-000001-index.htm")
    for name, row in [("dart_recent", dart), ("edgar", edgar)]:
        assert intel.import_capture(package, name, checked, [row]) == 1
        with pytest.raises(ValueError):
            intel.import_capture(package, name, checked, [dict(row, url="https://example.com/other")])
    with pytest.raises(ValueError):
        intel.import_capture(package, "edgar", checked, [dict(edgar, time="2025-01-01")])
    assert (package / ".local" / intel.CAPTURE_FILE).stat().st_mode & 0o777 == 0o600
    category = intel.board(directory, package)["categories"]["fundamentals"]
    imported = {r["source_id"]: r for r in category["observations"]}
    assert imported["edgar"]["subjects"] == ["CIK0000001234"]
    assert set(imported["edgar"]["domains"]) == {"equities", "us_small_cap_high_beta"}
    assert imported["dart_recent"]["domains"] == ["equities"]
    equity = next(r for r in intel.agent_brief(directory, package, "equities")["positions"] if r["symbol"] == "ALPHA")
    assert equity["evidence"]["fundamentals"][0]["origin"] == dart["url"]


def test_user_evidence_mapping_and_cash_schedule(local):
    directory, package = local
    intel.collect(package, "fundamentals", fetcher=public_fixture)
    p = next(p for p in intel.board(directory, package)["positions"] if p["symbol"] == "ALPHA")

    def manage(action, **rest):
        intel.manage(directory, package, dict(action=action, position=p["id"], **rest))

    manage("tags", tags="CIK0000001234")
    for value in ("before", "after"):
        manage(
            "evidence",
            category="policy",
            title="<script>fixture</script>",
            value=value,
            day="2025-01-01",
            source="https://example.org/update",
            analysis="검증",
        )
    manage("cash-date", day="2030-01-01", title="만기", amount="30")
    b = intel.board(directory, package)
    p = next(i for i in b["positions"] if i["id"] == p["id"])
    assert len(p["direct"]["fundamentals"]) == 2
    assert [i["value"] for i in p["direct"]["policy"]] == ["after"]
    assert "2030-01-01" in p["direct"]["exposure"][-1]["analysis"]
    page = monitor.render(directory, package, "/dummy", "test", {"position": p["id"]}).decode()
    assert "&lt;script&gt;" in page and "<script>fixture" not in page
    intel.manage(directory, package, dict(action="remove-date", entry=b["cash_dates"][0]["id"]))
    assert not intel.board(directory, package)["cash_dates"]


def test_management_requires_local_origin_and_random_token(local, monkeypatch):
    directory, package = local
    httpd = SimpleNamespace(server_port=8765)
    factory = Mock(return_value=httpd)
    monkeypatch.setattr(view, "ThreadingHTTPServer", factory)
    _, url = view.server(directory, package=package)
    path = urlsplit(url).path
    _, handler = factory.call_args.args

    def request(method, target, form=None, origin=None):
        host = "127.0.0.1:8765"
        payload = urlencode(form or {}).encode()
        peer, client = socket.socketpair()

        def serve():
            with peer:
                handler(peer, ("127.0.0.1", 1), httpd)

        thread = threading.Thread(target=serve)
        with client:
            client.settimeout(5)
            thread.start()
            headers = f"{method} {target} HTTP/1.0\r\nHost: {host}\r\nContent-Type: application/x-www-form-urlencoded\r\nContent-Length: {len(payload)}\r\n"
            if origin:
                headers += f"Origin: {origin}\r\n"
            client.sendall(headers.encode() + b"\r\n" + payload)
            res = http.client.HTTPResponse(client)
            res.begin()
            body = res.read().decode()
            if res.status in (200, 303, 403):
                assert res.getheader("Referrer-Policy") == "same-origin"
        thread.join(3)
        return res.status, body, res.getheader("Location")

    status, page, _ = request("GET", path)
    assert status == 200 and "<h1>투자 매니저</h1>" in page and "분야별 최신 결과" in page
    # The stock screen must never become a filter on the private portfolio or research desks.
    board = intel.board(directory, package)
    for choice in ("all", "US", "KR", "XT"):
        code, home, _ = request("GET", path + "/desk/manager?screen=" + choice)
        assert code == 200 and '<details id="live-positions" open>' in home
        assert home.index('id="live-values"') < home.index('id="manager-desks"') < home.index('id="market-desk"')
        assert all(f'position={p["id"]}#position' in home for p in board["positions"])
        assert all(f'category={cid}#sources' in home for cid in board["categories"])
        assert all(f'href="{path}/desk/{desk}" class="analyst-link"' in home for desk in intel.DOMAINS)
        assert all(f"/portfolio#{anchor}" in home for anchor in ("stress", "daily", "performance", "calendar"))
    assert "<h1>투자 매니저</h1>" in request("GET", path + "/")[1]
    assert "<h1>투자 관리</h1>" in request("GET", path + "/portfolio")[1]
    assert "<h1>투자 관리</h1>" in request("GET", path + "?agent=equities")[1]
    assert 'aria-label="투자 에이전트"' in request("GET", path + "/accounts")[1]
    token = re.search(r'name="csrf" value="([^"]+)"', page)[1]
    pid = next(p["id"] for p in intel.board(directory, package)["positions"] if p["symbol"] == "PROPERTY")
    data = dict(csrf=token, position=pid, action="role", role="real_estate")
    assert request("POST", path + "/manage", data, "https://example.org")[0] == 403
    assert request("POST", path + "/manage", data, "null")[0] == 403
    assert request("POST", path + "/manage", dict(data, csrf="bad"), "http://127.0.0.1:8765")[0] == 403
    assert request("POST", path + "/manage", data, "http://127.0.0.1:8765")[0] == 303
    assert intel.agent_brief(directory, package, "real_estate")["positions"][0]["symbol"] == "PROPERTY"

    from private_accounts import desk_feedback, reports
    from agents import research_chat, desk_variables
    origin = "http://127.0.0.1:8765"
    for room in research_chat.NAMES:
        status, html, _ = request("GET", path + "/desk/" + room)
        assert status == 200 and f'{room}/ask' not in html and 'name="question"' not in html
        persona = research_chat.profile(room)["persona"]
        assert persona.role in html and persona.lens in html
        assert request("POST", path + "/desk/" + room + "/ask", {}, origin)[0] == 404
        assert html.index('/desk/manager"') < html.index('/desk/whale"')
        expected = set(research_chat.NAMES) if room == "manager" else {room}
        assert {r["desk"] for r in desk_feedback.walkthrough(room)} == expected
    assert request("GET", path + "/desk/unknown")[0] == 404
    variable = dict(csrf=token, variable="beta", subject="FIXTURE", value="2.1", unit="배",
                    basis="52주 주간·시장 벤치마크", origin="https://example.org/returns", as_of="2025-01-01")
    assert request("POST", path + "/desk/whale/variable", variable, origin)[0] == 400
    assert request("POST", path + "/desk/us_small_cap_high_beta/variable", variable, origin)[0] == 303
    assert desk_variables.read(package, "whale") == []
    assert any(r["asset"] == "FIXTURE" for r in desk_variables.read(package, "us_small_cap_high_beta"))
    _, beta, _ = request("GET", path + "/desk/us_small_cap_high_beta")
    assert "기준일 경과" in beta and "미등록" in beta and "52주 주간·시장 벤치마크" in beta
    assert variable["origin"] in beta
    assert "분류 보류 · 시가총액 미등록, 베타 기준일 경과" in beta

    comment = dict(csrf=token, topic="자료·출처", comment="모의의견표식 <script>", request_id="a"*32)
    feedback = path + "/desk/crypto/feedback"
    assert request("POST", feedback, comment, "https://example.org")[0] == 403
    assert request("POST", feedback, dict(comment, csrf="bad"), origin)[0] == 403
    assert request("POST", feedback, dict(comment, comment=""), origin)[0] == 400
    assert request("POST", feedback, comment, origin)[2].endswith("?feedback=1#feedback")
    assert request("POST", feedback, comment, origin)[0] == 303
    assert len(desk_feedback.entries(package, "crypto")) == 1
    assert "모의의견표식" not in request("GET", path + "/desk/whale")[1]
    assert "모의의견표식 &lt;script&gt;" in request("GET", path + "/desk/manager?feedback=1")[1]
    state = dict(csrf=token, entry=comment["request_id"], done="1")
    assert request("POST", path + "/desk/crypto/feedback-state", state, origin)[0] == 404
    assert request("POST", path + "/desk/manager/feedback-state", state, origin)[0] == 303
    assert desk_feedback.entries(package, "crypto")[0]["done"]
    assert (package / ".local" / desk_feedback.FILE).stat().st_mode & 0o777 == 0o600

    assert not hasattr(httpd, "chat_service")
    from private_accounts import __main__ as cli
    import io
    from contextlib import redirect_stdout
    stamp = "2025-01-01T11:00:00+09:00"
    doc = dict(title="분야 보고 <script>", as_of=stamp, status="관찰", conclusion="모의 결론", downside="호가 공백",
               revisit="호가 회복 시 재검토", sources=[dict(label="모의 원문", as_of=stamp, url="https://example.org/doc")])
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(doc)))
    with redirect_stdout(io.StringIO()) as notice:
        cli.run(["publish-report", "crypto"], directory, package.parent)
    key = notice.getvalue().strip()
    assert key == reports.publish(package, "crypto", doc)
    assert len(reports.read(package)) == 1
    assert (package / ".local" / reports.FILE).stat().st_mode & 0o777 == 0o600
    for bad in [dict(doc, inputs=[key]), dict(doc, sources=[]), dict(doc, as_of="2025-01-01"),
                dict(doc, sources=[dict(doc["sources"][0], url="file:///private")])]:
        with pytest.raises(ValueError):
            reports.publish(package, "crypto", bad)
    for refs in [[], ["missing"], [key, key]]:
        with pytest.raises(ValueError):
            reports.publish(package, "manager", dict(doc, inputs=refs))
    manager = dict(doc, title="종합 판단", inputs=[key])
    reports.publish(package, "manager", manager)
    assert "분야 보고 &lt;script&gt;" in request("GET", path + "/desk/crypto")[1]
    assert "모의 결론" not in request("GET", path + "/desk/whale")[1]
    overview = request("GET", path)[1]
    assert "종합 판단" in overview and "#report-" + key in overview
    assert "2025-01-01 11:00 KST" in overview and "https://example.org/doc" in overview
    intel.update_json(package, "chat_crypto.json", [], lambda _: [
        dict(at=stamp, question="비공개 질문", reports={"crypto":{"status":"구형 모델", "text":"이전 분석"}})])
    assert "이전 분석" not in request("GET", path + "/desk/crypto")[1]
    legacy_page = request("GET", path + "/desk/crypto?legacy=1")[1]
    assert "이전 분석" in legacy_page and "비공개 질문" not in legacy_page


def test_chat_data_and_memory_isolation(local):
    from agents import desk_variables, research_chat
    from private_accounts import chat_service
    from private_accounts.local_model import ModelUnavailable
    directory, package = local
    intel.collect(package, fetcher=public_fixture)
    visited = []
    def scoped_public(source):
        visited.append(source["id"])
        return public_fixture(source)
    intel.collect(package, fetcher=scoped_public, domains=["whale"])
    assert "upbit" in visited and not {"dart","edgar","commons","registry"}.intersection(visited)
    board = intel.board(directory, package)
    from private_accounts import chat_page
    equity_sources = chat_page.position_sources(board, "equities", "/fixture")
    assert "ALPHA" in equity_sources and "UNIT" not in equity_sources
    assert "UNIT" in chat_page.position_sources(board, "whale", "/fixture")
    stamp = datetime.now(intel.KST).date().isoformat()
    desk_variables.save(package, "crypto", dict(variable="funding", subject="COINONLY", value="3",
                        unit="%", basis="8시간", origin="https://example.org/funding", as_of=stamp))
    ctx = research_chat.research_input(board, "crypto", "COINONLY", variables=desk_variables.read(package,"crypto"))
    assert any(f["value"]=="3 %" and f["asset"]=="COINONLY" for f in ctx["facts"])

    prompts = []
    def answer(messages):
        prompts.append(messages)
        return "시험 판단"
    previous = [dict(question="분리할 대화 표식", team=["crypto","equities"], reports={}, synthesis={"text":"다른 결론"})]
    reports, synthesis = chat_service.run_turn(board,"manager",["whale","equities"],"흐름",previous,answer,lambda s:None)
    assert list(reports) == ["whale","equities"] and synthesis
    joined = [json.dumps(m,ensure_ascii=False) for m in prompts]
    assert all("분리할 대화 표식" not in m for m in joined)
    assert "ALPHA" not in joined[0] and "UNIT" in joined[0] and "ALPHA" in joined[1]
    assert "COINONLY" not in "".join(joined)
    assert all('"account"' not in m[-1]["content"] for m in prompts[:2])
    previous = [dict(question="직전 질문", team=["equities"], reports={"equities":{"text":"직전 답변"}}, synthesis=None)]
    prompts.clear()
    _, summary = chat_service.run_turn(board,"equities",["equities"],"다시",previous,answer,lambda s:None)
    assert summary is None and len(prompts)==1 and prompts[0][1:3]==[
        dict(role="user",content="직전 질문"),dict(role="assistant",content="직전 답변")]
    def outage(_):
        raise ModelUnavailable("테스트 중단")
    reports, summary = chat_service.run_turn(board,"manager",["crypto"],"자료",[],outage,lambda s:None)
    assert reports["crypto"]["status"].startswith("자료 조회") and summary["status"].startswith("근거 대조")


def test_selected_personas_and_shared_source_refs(local):
    from agents import desk_variables, research_chat
    from agents.personas import PERSONAS
    from private_accounts import chat_page, chat_service

    directory, package = local
    board = intel.board(directory, package)
    variables = {}
    origin = "https://example.org/same-document"
    for desk, fields in desk_variables.FIELDS.items():
        desk_variables.save(package, desk, dict(variable=next(iter(fields)), subject="모의대상",
                            value="1", unit="단위", basis="측정 기준", origin=origin,
                            as_of=datetime.now(intel.KST).date().isoformat()))
        variables[desk] = desk_variables.read(package, desk)

    prompts = []
    def complete(messages):
        prompts.append(messages)
        return "모의 답변"

    for desk in intel.DOMAINS:
        reports, synthesis = chat_service.run_turn(board, desk, [desk], "점검", [], complete,
                                                   lambda _: None, variables=variables)
        assert list(reports) == [desk] and synthesis is None
        system = prompts[-1][0]["content"]
        assert [k for k, persona in PERSONAS.items() if persona.role in system] == [desk]
        assert not research_chat.shared_sources(reports)
        if desk == "us_small_cap_high_beta":
            state = reports[desk]["checks"]["모의대상"]
            assert "베타 미등록" in state and "시가총액 기준일" in state
            archived = chat_page.turn_view(dict(question="점검", at="now", reports=reports), False)
            assert state in archived and "질문 시점의 등록 자료 점검" in archived

    team = ["whale", "crypto"]
    reports, synthesis = chat_service.run_turn(board, "manager", team, "비교", [], complete,
                                               lambda _: None, variables=variables)
    assert PERSONAS["manager"].role in prompts[-1][0]["content"]
    overlap = research_chat.shared_sources(reports)
    assert set(overlap) == {origin} and set(overlap[origin]) == set(team)
    assert origin in prompts[-1][-1]["content"] and "shared_public_urls" in prompts[-1][-1]["content"]
    rendered = chat_page.turn_view(dict(question="비교", at="now", reports=reports, synthesis=synthesis), True)
    assert "여러 담당이 함께 인용한 원문" in rendered
    assert "선택한 담당의 주요 관측값" in rendered and "거래소 순유입" in rendered and "현물 호가 깊이" in rendered
    assert "이번 답변의 근거에 등록값 없음" in rendered
    assert all(ref in rendered for refs in overlap[origin].values() for ref in refs)


def test_crypto_common_observation_day_is_scoped_to_asset(local):
    from agents import desk_variables
    from private_accounts import chat_page

    directory, package = local
    for key, subject, day in [
        ("depth", "모의A", "2025-01-01"), ("funding", "모의A", "2025-01-01"),
        ("depth", "모의A", "2025-01-03"), ("funding", "모의B", "2025-01-03"),
    ]:
        desk_variables.save(package, "crypto", dict(variable=key, subject=subject, as_of=day, value="1",
                            unit="단위", basis="원문 관측 시각", origin="https://example.org/measure"))
    rows = desk_variables.read(package, "crypto")
    assert desk_variables.depth_funding_dates(rows, "asset") == {"모의A": "2025-01-01", "모의B": None}
    block = chat_page.variable_status("crypto", rows, intel.board(directory, package)["categories"])
    assert "공통 기준일 · 2025-01-01" in block and "공통 기준일 · 일치 자료 없음" in block
    assert "2025-01-03" in block and "기준일 경과" in block


def test_short_native_reply_does_not_show_split_korean_letter(tmp_path, monkeypatch):
    from private_accounts import local_model
    reply = "확인 자료".encode()[:-1]
    monkeypatch.setattr(local_model.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=reply))
    text = local_model.native_completion(tmp_path/"helper", tmp_path/"binary", tmp_path/"model", [])
    assert text.startswith("확인 자") and "글자 중간에서" in text and "�" not in text
