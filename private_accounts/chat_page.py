"""Render saved investment reports and local monitoring controls."""

import secrets
from datetime import datetime
from html import escape
from urllib.parse import urlsplit

from agents import desk_variables, intelligence as intel, research_chat as research
from . import history_panel, daily_review, desk_feedback, live_panel, market_panel as daily_market_panel, reports


def e(value):
    return escape(str(value), quote=True)


def navigation(base, active):
    core_rooms = {"manager", "tournament", "portfolio", "discover", "contrarian"}
    lab_rooms = {"research", "strategies", "quant"}
    items = [
        ("manager", "★ 종합 상황판", f"{base}/desk/manager"),
        ("tournament", "🏆 최종 우승", base + "/tournament"),
        ("portfolio", "내 계좌·포트폴리오", base + "/portfolio"),
        ("discover", "신규 대장주 발굴", base + "/discover"),
        ("contrarian", "역발상·1종목 비대칭", base + "/contrarian"),
        ("research", "가설 연구장", base + "/research"),
        ("strategies", "전략·백테스트", base + "/strategies"),
        ("quant", "퀀트·차트 검증", base + "/quant"),
    ]
    items.extend((room, name, f"{base}/desk/{room}") for room, name in research.NAMES.items() if room != "manager")
    links = []
    for idx, (room, name, link) in enumerate(items):
        if idx in (5, 8):
            links.append('<span class="nav-sep" aria-hidden="true">|</span>')
        cls = ' class="nav-core"' if room in core_rooms else (' class="nav-lab"' if room in lab_rooms else "")
        cur = ' aria-current="page"' if room == active else ""
        links.append(f'<a href="{e(link)}"{cls}{cur}>{e(name)}</a>')
    return '<nav class="desk-tabs" aria-label="투자 에이전트">' + "".join(links) + "</nav>"


def source_link(source):
    parsed = urlsplit(source)
    if parsed.scheme == "https" and parsed.hostname:
        return f'<a href="{e(source)}" target="_blank" rel="noreferrer noopener">{e(parsed.hostname)} 원문</a>'
    return e(source)


def market_panel(package):
    check = intel.latest_market_check(package)
    if not check:
        return ""
    def kst(stamp):
        return datetime.fromisoformat(stamp).astimezone(intel.KST).strftime("%Y-%m-%d %H:%M:%S")

    out = ['<section class="market-check"><h2>공개 시장 점검</h2>',
           f'<p>한국시간 기준 {kst(check["cutoff"])} · 원문 확인 {kst(check["verified_at"])}</p><div class="market-grid">']
    for row in check["rows"]:
        out.append(f'<div><b>{e(row["title"])}</b><strong>{e(row["value"])}</strong>'
                   f'<small>{e(row["analysis"])} · {kst(row["as_of"])}</small>'
                   f'<small>{source_link(row["origin"])}</small></div>')
    out.append("</div>")
    reports = intel.private_json(package, daily_review.FILE, {})
    if reports:
        report = reports[max(reports)]
        dates = {(a["source"], a["as_of"]) for a in report.get("account_dates", [])}
        for source, stamp in sorted(dates):
            label = "계좌 엑셀 수정" if source == "workbook" else "계좌 스냅샷 기준"
            out.append(f'<small>{label} · {kst(stamp)} KST</small> ')
    return "".join(out) + "</section>"


def evidence(facts):
    if not facts:
        return "<p>배정된 관측값이 없습니다.</p>"
    out = []
    for f in facts:
        subject = f.get("asset") or f["scope"]
        out.append(
            f'<div class="row"><b>{e(subject)} · {e(f["title"])}</b> · {e(f["value"])}'
            f'<small>{e(f["ref"])} · {e(f["scope"])} · 기준일 {e(f["as_of"])}'
            + (' · <strong class="elapsed">기준일 경과</strong>' if f["stale"] else "")
            + f' · {source_link(f["source"])}</small><small>{e(f.get("analysis", ""))}</small></div>'
        )
    return "".join(out)


def selected_metrics(reports):
    focus = {"whale": ("exchange_net",), "crypto": ("depth", "funding"),
             "equities": ("cashflow", "constituents"), "real_estate": ("sale", "senior_right"),
             "us_small_cap_high_beta": ("cap", "beta")}
    out = ['<details open><summary>선택한 담당의 주요 관측값</summary>']
    for desk, result in reports.items():
        for key in focus[desk]:
            label = desk_variables.FIELDS[desk][key][0]
            matches = [f for f in result["facts"] if f["title"] == label and f["scope"] == "분야 등록 자료"]
            out.append(f'<div class="row"><b>{e(research.NAMES[desk])} · {e(label)}</b>')
            if matches:
                for f in matches:
                    age = " · 기준일 경과" if f["stale"] else ""
                    out.append(f'<small>{e(f["asset"])} · {e(f["value"])} · {e(f["as_of"])}{age}'
                               f' · {source_link(f["source"])} · {e(f["ref"])}</small>')
            else:
                out.append("<small>이번 답변의 근거에 등록값 없음</small>")
            out.append("</div>")
    return "".join(out) + "</details>"


def turn_view(turn, manager):
    out = [
        f'<article class="exchange"><div class="question"><small>내 질문 · {e(turn["at"])}</small>'
        f'<p>{e(turn["question"])}</p></div>'
    ]
    if manager:
        result = turn["synthesis"]
        out.append(
            f'<div class="answer"><b>투자 매니저</b><small>{e(result["status"])}</small>'
            f'<p>{e(result["text"])}</p></div>'
        )
        out.append('<div class="comparison"><table><caption>이번 질문에 참여한 담당의 근거</caption>'
                   '<thead><tr><th>담당</th><th>자료 행</th><th>공통 시장</th><th>기준일 경과</th></tr></thead><tbody>')
        for desk, report in turn["reports"].items():
            facts = report["facts"]
            market = sum(f["scope"] == "공통 시장 자료" for f in facts)
            old = sum(bool(f["stale"]) for f in facts)
            out.append(f'<tr><th scope="row">{e(research.NAMES[desk])}</th>'
                       f'<td>{len(facts)}</td><td>{market}</td><td>{old}</td></tr>')
        out.append("</tbody></table></div>")
        out.append(selected_metrics(turn["reports"]))
        overlap = research.shared_sources(turn["reports"])
        if overlap:
            out.append('<div class="overlap"><b>여러 담당이 함께 인용한 원문</b><ul>')
            for url, grouped in overlap.items():
                refs = " · ".join(f'{research.NAMES[k]} ({", ".join(v)})' for k, v in grouped.items())
                out.append(f"<li>{source_link(url)} · {e(refs)}</li>")
            out.append("</ul></div>")
        elif len(turn["reports"]) > 1:
            out.append("<small>둘 이상의 담당이 인용한 동일 원문 주소 · 0건</small>")
    for desk, data in turn["reports"].items():
        name = e(research.NAMES[desk])
        checks = data.get("checks", {})
        snapshot = ""
        if checks:
            items = "".join(f'<li>{e(asset)} · {e(state)}</li>' for asset, state in checks.items())
            snapshot = '<div class="overlap"><b>질문 시점의 등록 자료 점검</b><ul>' + items + "</ul></div>"
        answer = (
            f'<div class="answer"><b>{name}</b><small>{e(data["status"])}</small>{snapshot}<p>{e(data["text"])}</p>'
            f'<details><summary>검토 근거 {len(data["facts"])}건</summary>{evidence(data["facts"])}</details></div>'
        )
        out.append(f"<details><summary>{name} 담당 의견</summary>{answer}</details>" if manager else answer)
    return "".join(out) + "</article>"


def variable_status(room, rows, categories):
    today = datetime.now(intel.KST).date()
    by_asset = {}
    for r in rows:
        if r.get("key"):
            by_asset.setdefault(r["asset"], {}).setdefault(r["key"], []).append(r)
    if not by_asset:
        labels = " · ".join(label for label, _ in desk_variables.FIELDS[room].values())
        return (f'<p class="empty-chat">확보한 분야 변수가 없습니다.</p><p>{e(labels)}</p>'
                '<a href="#variable-form">첫 변수 등록</a>')
    pairs = desk_variables.depth_funding_dates(rows, "asset") if room == "crypto" else {}
    out = []
    for asset, recorded in sorted(by_asset.items()):
        out.append(f'<details class="variable-status"><summary>{e(asset)} · 변수 {len(recorded)}/{len(desk_variables.FIELDS[room])}</summary>')
        if room == "crypto":
            common = pairs.get(asset)
            day = e(common) if common else "일치 자료 없음"
            if common and intel.outdated(common, categories["market_flow"]["stale_days"], today):
                day += ' · <strong class="elapsed">기준일 경과</strong>'
            out.append(f'<p>호가·펀딩 최근 공통 기준일 · {day}</p>'
                       '<small>거래소와 관측 시각은 각 원문의 측정 기준에서 확인하세요.</small>')
        out.append("<ul>")
        for key, (label, cid) in desk_variables.FIELDS[room].items():
            observations = sorted(recorded.get(key, []), key=lambda r: r["as_of"], reverse=True)
            if not observations:
                out.append(f'<li>{e(label)} · <span>미등록</span></li>')
                continue
            out.append(f"<li>{e(label)}")
            for r in observations:
                old = intel.outdated(r["as_of"], categories[cid]["stale_days"], today)
                age = ' · <strong class="elapsed">기준일 경과</strong>' if old else ""
                out.append(f'<small>{e(r["value"])} · {e(r["as_of"])}{age} · {source_link(r["origin"])}'
                           f'<br>측정 기준 · {e(r["analysis"])}</small>')
            out.append("</li>")
        out.append("</ul></details>")
    return "".join(out)


def position_sources(board, room, base):
    positions = [p for p in board["positions"] if room in p["tasks"]]
    out = [f'<details><summary>보유 종목별 원문 · {len(positions)}행</summary>']
    if not positions:
        out.append("<p>이 담당에 배정된 보유 행이 없습니다.</p>")
    for p in positions:
        sources = [row for cid, group in p["direct"].items() for row in group
                   if cid != "exposure" and room in board["categories"][cid]["agents"]
                   and research.source_allowed(row, room)
                   and (not row.get("domains") or room in row["domains"]) and row["origin"].startswith("https://")]
        sources.sort(key=lambda r: (not r["stale"], r["as_of"]), reverse=True)
        out.append(f'<div class="row"><a href="{e(base)}/portfolio?position={e(p["id"])}#position">'
                   f'{e(p["symbol"])} · {e(p["currency"])}</a> · 연결 근거 {len(sources)}건')
        for r in sources[:3]:
            age = " · 기준일 경과" if r["stale"] else ""
            out.append(f'<small>{e(r["title"])} · {e(r["as_of"])}{age} · {source_link(r["origin"])}</small>')
        out.append("</div>")
    return "".join(out) + "</details>"


def feedback_panel(package, room, base, csrf, opened):
    url = f'{e(base)}/desk/{room}'
    rows = desk_feedback.entries(package, room)
    pending = sum(not r["done"] for r in rows)
    out = [f'<details id="feedback" class="feedback-panel"{" open" if opened else ""}>'
           f'<summary>대시보드 개선 의견 · 미처리 {pending}건</summary>',
           f'<form method="post" action="{url}/feedback"><input type="hidden" name="csrf" value="{e(csrf)}">'
           f'<input type="hidden" name="request_id" value="{secrets.token_hex(16)}">'
           '<label>개선할 항목<select name="topic">']
    out.extend(f'<option>{e(t)}</option>' for t in desk_feedback.TOPICS)
    out.append('</select></label><label>투자 매니저와 공유할 화면 개선 의견'
               '<textarea name="comment" rows="2" maxlength="400" required></textarea></label>'
               '<button type="submit">의견 등록</button></form>')
    if room == research.MANAGER:
        out.append("<h3>전체 담당의 개선 의견</h3>")
    for row in rows:
        state = "반영 완료" if row["done"] else "미처리"
        out.append(f'<div class="row"><b>{e(research.NAMES[row["room"]])} · {e(row["topic"])}</b>'
                   f'<p>{e(row["comment"])}</p><small>{e(row["at"])} · {state}</small>')
        if room == research.MANAGER:
            out.append(f'<form method="post" action="{url}/feedback-state">'
                       f'<input type="hidden" name="csrf" value="{e(csrf)}">'
                       f'<input type="hidden" name="entry" value="{e(row["id"])}">'
                       f'<button name="done" value="{int(not row["done"])}">'
                       + ("다시 열기" if row["done"] else "반영 완료 표시") + "</button></form>")
        out.append("</div>")
    review = desk_feedback.walkthrough(room)
    if review:
        out.append('<details class="walkthrough"><summary>페르소나 모의 사용 점검 결과</summary>'
                   '<p>로컬 모델이 모의 자료로 분석실을 사용한 뒤 남긴 의견을 요약했습니다.</p>')
        for item in review:
            out.append(f'<div class="row"><b>{e(research.NAMES[item["desk"]])}</b><p>{e(item["feedback"])}</p>'
                       f'<small>반영 내용 · {e(item["change"])}</small></div>')
        out.append("</details>")
    return "".join(out) + "</details>"


def kst_time(value):
    return datetime.fromisoformat(value).astimezone(intel.KST).strftime("%Y-%m-%d %H:%M KST")


def report_view(row, ledger, base, *, open_first=False):
    opened = " open" if open_first else ""
    out = [f'<details{opened} class="investment-report" id="report-{e(row["id"])}">'
           f'<summary>{e(row["title"])} <small>{e(row["status"])} · {e(kst_time(row["as_of"]))}</small></summary>'
           f'<p>{e(row["conclusion"])}</p>'
           f'<dl><dt>하방 위험</dt><dd>{e(row["downside"])}</dd>'
           f'<dt>재검토 조건</dt><dd>{e(row["revisit"])}</dd></dl>']
    if row["sources"]:
        out.append('<details><summary>판단 근거 · ' + str(len(row["sources"])) + '건</summary><ul>')
        for src in row["sources"]:
            link = " · " + source_link(src["url"]) if src.get("url") else ""
            out.append(f'<li>{e(src["label"])} · {e(kst_time(src["as_of"]))}{link}</li>')
        out.append("</ul></details>")
    else:
        out.append("<small>확인된 근거 없음</small>")
    for key in row["inputs"]:
        member = ledger[key]
        out.append(f'<a class="desk-link" href="{e(base)}/desk/{e(member["desk"])}?all=1#report-{e(key)}">'
                   f'{e(research.NAMES[member["desk"]])} · {e(member["title"])}</a>')
    return "".join(out) + "</details>"


def manager_research(board, ordered, base):
    from . import monitor
    out = ['<section id="manager-desks" data-watch><h2>담당 애널리스트</h2>'
           '<p class="desk-section-note">분야별 최신 결과</p><div class="analyst-directory">']
    for desk in intel.DOMAINS:
        latest = next((r for r in ordered if r["desk"] == desk), None)
        count = sum(desk in p["tasks"] for p in board["positions"])
        out.append(f'<a href="{e(base)}/desk/{desk}" class="analyst-link"><strong>{e(research.NAMES[desk])}</strong>'
                   f'<small>담당 보유 행 {count} · {e(latest["status"]) if latest else "게시 대기"}</small>')
        if latest:
            out.append(f'<span>{e(latest["title"])}</span><small>{e(kst_time(latest["as_of"]))}</small>')
        out.append('</a>')
    out.append('</div></section>')
    out.append(monitor.category_panel(board["categories"], base, compact=True))
    return "".join(out)


def manager_sections(directory, package, base, screen, *, ordered=None, research_update=True, position=None, frame="day"):
    from . import live_valuation, research_page, tournament_page
    book = live_valuation.read(package)
    board = intel.board(directory, package, quote_book=book) if research_update else None
    accounts = board["accounts"] if board else live_panel.portfolio_accounts(directory, package, quote_book=book)
    banner = tournament_page.champion_banner(package, base)
    cockpit = research_page.action_cockpit(directory, package, base, quote_book=book, accounts=accounts)
    panel = live_panel.panel(directory, package, book, accounts, manager_base=base)
    panel += history_panel.position_history(package, accounts, base, position, frame, manager=True, screen=screen)
    panel = banner + cockpit + '<div class="account-workspace">' + panel + "</div>"
    if board is not None:
        if ordered is None:
            ordered = sorted(reports.read(package).values(), key=lambda r:(r["as_of"],r["published"]), reverse=True)
        panel += manager_research(board, ordered, base)
    return panel + daily_market_panel.render(package, base, screen)


def render(directory, package, base, csrf, room, css, show_all=False, feedback_open=False, show_legacy=False, screen="all", position=None, frame="day"):
    ledger = reports.read(package)
    ordered = sorted(ledger.values(), key=lambda r: (r["as_of"], r["published"]), reverse=True)
    rows = [r for r in ordered if r["desk"] == room]
    manager = room == research.MANAGER
    spec = research.profile(room)
    persona = spec["persona"]
    url = f"{base}/desk/{room}"
    out = [
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{e(research.NAMES[room])} · Whale Tracking</title><style>{css}</style>{live_panel.script(base)}</head>"
        + ('<body class="manager-desk">' if manager else '<body>'),
        "<header><div><strong>Whale Tracking</strong><small>로컬 투자 관리</small></div></header>",
        navigation(base, room), '<main class="desk-main">',
        f'<div class="desk-title"><h1>{e(research.NAMES[room])}</h1><details><summary>담당 역할·판단 기준</summary>'
        f'<b>{e(persona.role)}</b><p>{e(persona.lens)}</p>'
        f'<p>{e(persona.reconsider)}</p></details></div>',
        ('<nav class="manager-jumps" aria-label="매니저 화면 섹션"><a href="#tournament-champions">🏆 최종 우승</a>'
         '<a href="#action-cockpit">오늘 행동 답안지</a>'
         f'<a href="{e(base)}/discover">포트폴리오 외 신규 대장주 발굴</a>'
         f'<a href="{e(base)}/contrarian">역발상·1종목 비대칭 설계</a>'
         f'<a href="{e(base)}/strategies#mistake-notes">실전 복기·오답노트</a>'
         '<a href="#live-values">내 포트폴리오</a>'
         '<a href="#price-history">가격 이력</a><a href="#manager-desks">담당 애널리스트</a><a href="#analysts">데이터 범주</a>'
         '<a href="#market-desk">주식 시장 브리핑</a><a href="#desk-results">종합 보고서</a></nav>'
         + manager_sections(directory, package, base, screen, ordered=ordered, position=position, frame=frame)) if manager else "",
        '<div class="desk-grid"><section class="chat-card">',
    ]
    if manager:
        from . import research_page
        out.append(research_page.manager_panel(package, base))
    out.append('<h2 id="desk-results">' + ("투자 매니저 종합 결과" if manager else "담당 분석 결과") + "</h2>")
    if not rows:
        out.append("<p>아직 게시된 분석 결과가 없습니다. Codex에서 이 담당에게 작업을 지시하면 완료한 결과가 여기에 표시됩니다.</p>")
    for idx, row in enumerate(rows if show_all else rows[:3]):
        out.append(report_view(row, ledger, base, open_first=(idx == 0)))
    if not show_all and len(rows) > 3:
        out.append(f'<a href="{e(url)}?all=1">전체 보고서 {len(rows)}건 보기</a>')
    if manager:
        if intel.latest_market_check(package):
            out.append("<details><summary>공개 시장 점검 기록</summary>" + market_panel(package) + "</details>")
    # Preserve access to earlier conclusions without displaying or replaying chat prompts.
    archive = f"chat_{room}.json"
    if show_legacy:
        legacy = intel.private_json(package, archive, [])
        out.append('<details open id="legacy"><summary>이전 로컬 모델 분석 기록</summary>')
        for turn in reversed(legacy):
            result = turn.get("synthesis") if manager else turn.get("reports", {}).get(room)
            if result:
                out.append(f'<div class="row"><small>{e(turn["at"])} · {e(result["status"])}</small>'
                           f'<p>{e(result["text"])}</p></div>')
        out.append("</details>")
    elif package is not None and (package / ".local" / archive).is_file():
        out.append(f'<a class="desk-link" href="{e(url)}?legacy=1#legacy">이전 로컬 모델 분석 기록 열기</a>')
    out.append(feedback_panel(package, room, base, csrf, feedback_open))
    out.append('</section><aside class="desk-aside">')
    if manager:
        out.append(f'<h2>포트폴리오 관리</h2><a class="desk-link" href="{e(base)}/portfolio#live-values">보유 종목 현재가</a>'
                   f'<a class="desk-link" href="{e(base)}/portfolio#holdings">보유 종목별 담당·근거</a>'
                   f'<a class="desk-link" href="{e(base)}/portfolio#daily">일일 투자 검토</a>'
                   f'<a class="desk-link" href="{e(base)}/portfolio#stress">하방 스트레스</a>'
                   f'<a class="desk-link" href="{e(base)}/portfolio#performance">입출금 조정 성과</a>'
                   f'<a class="desk-link" href="{e(base)}/portfolio#calendar">현금 일정</a>'
                   f'<a class="desk-link" href="{e(base)}/portfolio#analysts">정보 원천과 수집 상태</a>'
                   f'<a class="desk-link" href="{e(base)}/accounts">계좌별 보유 현황</a>')
    else:
        variables = desk_variables.read(package, room)
        board = intel.board(directory, package, live=True)
        ctx = research.research_input(board, room, variables=variables)
        out.append(
            f"<h2>담당 변수</h2><p>{e(research.VARIABLES[room])}</p>"
            f'<details><summary>판단 기준</summary><b>후보 검토</b><p>{e(spec["candidate"])}</p>'
            f'<b>가설 재검토 조건</b><p>{e(spec["review"])}</p></details>'
            '<h3>대상별 변수 점검</h3>'
        )
        out.append('<div id="desk-variables" data-watch>' + variable_status(room, variables, board["categories"]))
        if room == "crypto":
            from agents import public_variables
            states = intel.private_json(package, public_variables.CACHE, {})
            out.append("<details><summary>공개 표본 수집 상태</summary>")
            for key, feed_url in public_variables.URLS.items():
                state = states.get(key, {})
                key_name = key.rsplit("_", 1)[0] if key != "depth" else key
                name = desk_variables.FIELDS[room][key_name][0]
                asset = key.rsplit("_", 1)[-1] if key != "depth" else "BTC·ETH"
                success = kst_time(state["success"]) if state.get("success") else "기록 없음"
                out.append(f'<div class="row">{e(asset)} · {e(name)} · {e(state.get("status", "미수집"))}'
                           f'<small>마지막 자동 성공 {e(success)} · {source_link(feed_url)}</small></div>')
            out.append("</details>")
        out.append("</div>")
        if room == "us_small_cap_high_beta":
            checks = desk_variables.small_cap_checks(variables, [h["symbol"] for h in ctx["holdings"]],
                                                      board["categories"], datetime.now(intel.KST).date())
            if checks:
                out.append("<h3>소형·고베타 분류 점검</h3><small>출처가 확인된 변수 기준</small>")
                for asset, state in checks.items():
                    out.append(f'<div class="row"><b>{e(asset)}</b> · {e(state)}</div>')
        out.append(position_sources(board, room, base))
        if room == "real_estate":
            out.append(f'<p><a href="{e(base)}/portfolio#calendar">포트폴리오 현금 일정 확인</a></p>')
        out.append(f'<h3>자료 연결</h3><p>배정된 보유 행 {len(ctx["holdings"])}개 · 정보 범주 {len(ctx["inputs"])}개</p>')
        for cat in ctx["inputs"].values():
            out.append(
                "<details><summary>" + e(cat["title"]) + "</summary><p>" + e(cat["question"]) + "</p>"
            )
            market = cat["market_example"]
            if market:
                age = ' · <strong class="elapsed">기준일 경과</strong>' if market["stale"] else ""
                out.append(f'<div class="row"><b>공통 시장 관측 · {e(market["title"])}</b> · {e(market["value"])}'
                           f'<small>{e(market["as_of"])}{age} · {source_link(market["origin"])}</small></div>')
            else:
                out.append("<small>이 범주에 배정된 공통 시장 관측값이 없습니다.</small>")
            for s in cat["sources"]:
                stamp = s["collected"] or "확보 기록 없음"
                out.append(
                    f'<div class="row">{e(s["name"])}<small>{e(s["status"])} · {e(stamp)}</small></div>'
                )
            out.append("</details>")
        out.append("<details><summary>분야 변수 기록·추가</summary>")
        for row in variables:
            if row.get("key"):
                continue
            out.append(
                f'<div class="row">{e(row["asset"])} {e(row["title"])} · {e(row["value"])}'
                f'<small>{e(row["as_of"])} · {e(row["analysis"])}</small></div>'
            )
        out.append(
            f'<form id="variable-form" method="post" action="{e(url)}/variable">'
            f'<input type="hidden" name="csrf" value="{e(csrf)}">'
            '<label>분야 변수<select name="variable">'
            + "".join(
                f'<option value="{key}">{e(label)}</option>'
                for key, (label, _) in desk_variables.FIELDS[room].items()
            )
            + "</select></label>"
        )
        for key, label, kind, limit in (
            ("subject", "대상 자산·시장", "text", 90),
            ("as_of", "관측 기준일", "date", 10),
            ("value", "관측값", "text", 100),
            ("unit", "단위", "text", 40),
            ("basis", "측정 기간·비교 기준", "text", 180),
            ("origin", "공개 원문 주소", "url", 600),
        ):
            out.append(
                f'<label>{label}<input type="{kind}" name="{key}" maxlength="{limit}" required></label>'
            )
        out.append('<button type="submit">변수 저장</button></form></details>')
    out.append("</aside></div></main></body></html>")
    return "".join(out).encode()
