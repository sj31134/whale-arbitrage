"""Server-rendered private dashboard. Only same-origin updates, with no third-party assets or client storage."""

from collections import Counter
from decimal import Decimal, localcontext
from html import escape
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from agents import intelligence as intel
from agents.portfolio import CASH_NAMES
from . import (
    account_performance,
    chat_page,
    daily_review,
    history_panel,
    live_panel,
    live_valuation,
    research_book,
    research_page,
    store,
)

CSS = Path(__file__).with_name("monitor.css").read_text()
ROLES = {
    "auto": "자동 배정",
    **{k: v for k, v in intel.LABELS.items() if k != "whale"},
    "cash": "현금",
    "other": "기타",
}


def e(value):
    return escape(str(value), quote=True)


def tag(value, warn=False):
    return f'<span class="tag{" flag" if warn else ""}">{e(value)}</span>'


def metric(label, value):
    return (
        f'<article class="card"><small>{e(label)}</small><strong class="metric">{e(value)}</strong></article>'
    )


def fmt(value):
    return "미평가" if value is None else f"{Decimal(value):,f}"


def market_marks_panel(package):
    marks = intel.private_json(package, "portfolio_market_marks.json", {})
    out = ['<section id="current-marks"><h2>보유 종목 현재가</h2>']
    if not marks.get("rows"):
        return "".join(out) + "<p>저장된 보유 종목 시세 점검이 없습니다.</p></section>"
    out.append(f'<p>시세 점검 {e(chat_page.kst_time(marks["checked"]))} · '
               f'수량 기준 엑셀 수정 {e(chat_page.kst_time(marks["balances_as_of"]))}</p>'
               '<p>예상 손익과 원가 회복 단가는 보유 수량 기준이며 세금과 수수료를 제외합니다.</p>'
               '<div class="comparison"><table><thead><tr>')
    columns = ("계좌", "엑셀 종목", "시장 종목 · 코드", "식별 상태", "통화", "현재가",
               "시세 기준시각", "추정 평가손익", "원가 회복 단가")
    out.extend(f"<th>{label}</th>" for label in columns)
    out.append("</tr></thead><tbody>")
    for row in marks["rows"]:
        identified = " · ".join(x for x in (row.get("name"), row.get("code")) if x)
        unit = row.get("unit_target")
        fields = (f'{store.PROVIDERS[row["provider"]]} · {row["account"]}', row["symbol"],
                  identified or "미확인", row["match"], row["currency"], fmt(row["price"]),
                  chat_page.kst_time(row["stamp"]) if row.get("stamp") else "미확인",
                  fmt(row["pnl"]), f"{Decimal(unit):,.6f}".rstrip("0").rstrip(".") if unit is not None else "미확인")
        out.append("<tr>" + "".join(f"<td>{e(v)}</td>" for v in fields) + "</tr>")
    out.append("</tbody></table></div></section>")
    return "".join(out)


def totals(accounts):
    values, incomplete = {}, set()
    with localcontext() as ctx:
        ctx.prec = 100
        for a in accounts:
            for c, v in a["totals"].items():
                if v is None:
                    incomplete.add(c)
                else:
                    values[c] = values.get(c, Decimal(0)) + Decimal(v)
    return [
        (
            c,
            (fmt(values[c]) if c in values else "미평가")
            + (" · 일부 계좌 미평가" if c in incomplete else ""),
        )
        for c in sorted(values.keys() | incomplete)
    ]


def concentration_panel(positions, package, route):
    ideas = [r for r in research_book.entries(package) if not r["result"]] if package else []
    qualifying = sum(research_book.metrics(r["a"])["qualifies"] for r in ideas)
    buckets = {}
    for p in positions:
        if p["weight_pct"] is None:
            continue
        key = (p["provider"], p["account"], p["currency"])
        b = buckets.setdefault(key, dict(cash=Decimal(0), weights=[]))
        w = Decimal(p["weight_pct"])
        if p["role"] == "cash" or p["symbol"].upper() in CASH_NAMES:
            b["cash"] += w
        else:
            b["weights"].append(w)
    out = [
        '<section id="concentration-guide" class="guide-banner">'
        "<h2>소수 집중 · 현금 버퍼 실전 점검</h2>"
        "<p>하락·고변동장(1단계)에서는 계좌별 <b>현금 버퍼 35% 이상</b>을 확보해 바닥권 손절(휩소)을 막고, "
        "주식 비중은 <b>가설 3관문을 통과한 소수 핵심 종목</b>으로 압축합니다.</p>"
        f'<div class="chips"><a class="chip" href="{e(route)}/research">'
        f"가설 연구장 · 집중 후보 {qualifying}건 / 추적 {len(ideas)}건</a>"
        f'<a class="chip" href="{e(route)}/strategies#historical-backtests">4대 위기 백테스트 비교</a>'
        f'<a class="chip" href="{e(route)}/quant">종목별 권장 비중·차트</a></div>'
    ]
    if buckets:
        out.append(
            '<div class="comparison"><table><thead><tr><th>계좌 · 통화</th><th>보유 종목 수</th>'
            "<th>상위 2종목 집중도</th><th>현재 현금 비중</th><th>1단계 현금 버퍼(≥35%) 점검</th></tr></thead><tbody>"
        )
        for (provider, alias, currency), b in sorted(buckets.items()):
            top2 = sum(sorted(b["weights"], reverse=True)[:2], Decimal(0))
            cash = b["cash"]
            ok = cash >= Decimal(35)
            badge = (
                '<span class="badge-pass">버퍼 확보</span>'
                if ok
                else '<span class="badge-warn">비중 미달 종목 정리로 현금 보강 권장</span>'
            )
            out.append(
                f"<tr><td>{e(store.PROVIDERS[provider])} · {e(alias)} · {e(currency)}</td>"
                f'<td>{len(b["weights"])}종목</td><td>{top2:.1f}%</td><td><b>{cash:.1f}%</b></td><td>{badge}</td></tr>'
            )
        out.append("</tbody></table></div>")
    return "".join(out) + "</section>"


def stress_panel(positions, route, scenario):
    presets = {
        "pullback": ("조정 가정", {"equities": -10, "crypto": -20, "real_estate": -5, "cash": 0}),
        "severe": ("급락 가정", {"equities": -30, "crypto": -50, "real_estate": -20, "cash": 0}),
    }
    name, shocks = presets.get(scenario, presets["pullback"])
    buckets = {}
    for p in positions:
        key = (p["provider"], p["account"], p["currency"])
        b = buckets.setdefault(key, dict(change=Decimal(0), coverage=Decimal(0), missing=0, as_of=p["as_of"]))
        role = p["role"]
        if role == "us_small_cap_high_beta":
            role = "equities"
        if not role:
            if p["symbol"].upper() in CASH_NAMES:
                role = "cash"
            elif "crypto" in p["tasks"]:
                role = "crypto"
            elif "real_estate" in p["tasks"]:
                role = "real_estate"
            elif p["tasks"].get("equities") == "보유 분석":
                role = "equities"
        if p["weight_pct"] is None or role not in shocks:
            b["missing"] += 1
            continue
        weight = Decimal(p["weight_pct"])
        b["coverage"] += weight
        b["change"] += weight * shocks[role] / 100
    out = ['<section id="stress" data-watch><h2>보유분 하방 스트레스</h2><div class="chips">']
    for k, (label, _) in presets.items():
        out.append(f'<a class="chip" href="{e(route)}/portfolio?stress={k}#stress">{label}</a>')
    out.append(f'</div><p>{name} · 주식 {shocks["equities"]}% / 코인 {shocks["crypto"]}% / '
               f'실물 {shocks["real_estate"]}% / 현금 0%. 가상 가격 충격이며 환율·차입·거래 비용은 고정합니다.</p>')
    if not buckets:
        return "".join(out) + "<p>평가할 보유 자료가 없습니다.</p></section>"
    out.append('<div class="comparison"><table><thead><tr><th>계좌 · 평가통화</th><th>수량 기준시각</th>'
               '<th>반영 비중</th><th>미분류·미평가</th><th>반영분의 손익 기여</th></tr></thead><tbody>')
    for (provider, alias, currency), b in sorted(buckets.items()):
        value = f'{b["change"]:+.2f}%p' if b["coverage"] > 0 else "산정 보류"
        out.append(f'<tr><td>{e(store.PROVIDERS[provider])} · {e(alias)} · {e(currency)}</td>'
                   f'<td>{e(chat_page.kst_time(b["as_of"]))}</td><td>{b["coverage"]:.2f}%</td>'
                   f'<td>{b["missing"]}행</td><td>{value}</td></tr>')
    return "".join(out) + "</tbody></table></div></section>"


def item(row):
    origin = row["origin"]
    link = (
        f'<a href="{e(origin)}" target="_blank" rel="noreferrer noopener">원문</a>'
        if urlsplit(origin).scheme == "https"
        else e(origin)
    )
    return (
        f'<div class="row"><b>{e(row["title"])}</b> · {e(row["value"])} '
        + (tag("기준일 경과", True) if row["stale"] else "")
        + f'<small>{e(row["analysis"])}</small><small>{e(row["as_of"])} · {e(row["source"])} · {link}</small></div>'
    )


def options(choices, current=None):
    return "".join(
        f'<option value="{e(k)}" {"selected" if k == current else ""}>{e(v)}</option>'
        for k, v in choices.items()
    )


def form(route, csrf, action, label, fields="", position="", section="", extra=""):
    def hidden(name, value):
        return f'<input type="hidden" name="{name}" value="{e(value)}">'

    return (
        f'<form method="post" action="{e(route)}/manage">'
        + hidden("csrf", csrf)
        + hidden("action", action)
        + hidden("position", position)
        + extra
        + (f"<h3>{e(section)}</h3>" if section else "")
        + fields
        + f'<button type="submit">{e(label)}</button></form>'
    )


def position_detail(p, categories, route, csrf, quote_book=None):
    pid = p["id"]

    def save(action, button, fields, section):
        return form(route, csrf, action, button, fields, pid, section)

    hint = ""
    if quote_book is not None and quote_book.match(p["provider"], p["symbol"], p["currency"], p["tags"]) is None:
        cands = live_valuation.suggest_identifiers(quote_book, p["provider"], p["symbol"], p["currency"])
        if cands:
            items = ", ".join(f"<code>{e(code)}</code> ({e(name)})" for code, name in cands)
            hint = f'<p><span class="badge-warn">시세 미연결 후보</span> 상장 종목명과 철자가 다를 수 있습니다 · {items}</p>'

    controls = save(
        "role",
        "담당 저장",
        '<label>주 담당<select name="role">' + options(ROLES, p["role"] or "auto") + "</select></label>",
        "담당 배정",
    )
    controls += save(
        "tags",
        "연결어 저장",
        hint + f'<small>시세 연결 형식 · stock:KR:국내코드 / stock:US:미국티커 / token:XT:토큰티커. 기초주식 연결은 underlying:US:티커.</small><label>공개 티커·CIK·주제 (쉼표로 구분)<input name="tags" maxlength="500" value="{e(", ".join(p["tags"]))}"></label>',
        "원천 식별자",
    )
    controls += save(
        "evidence",
        "근거 저장",
        '<label>정보 범주<select name="category">'
        + options({k: v["title"] for k, v in categories.items()})
        + "</select></label>"
        '<label>제목<input name="title" required maxlength="200"></label><label>관측값·단위<input name="value" required maxlength="220"></label>'
        '<label>기준일<input type="date" name="day" required></label><label>원문 주소<input type="url" name="source" required></label>'
        '<label>해석·재검토 조건<textarea name="analysis" required maxlength="450"></textarea></label>',
        "종목 근거 기록",
    )
    controls += save(
        "cash-date",
        "일정 저장",
        '<label>일정명<input name="title" required maxlength="120"></label>'
        f'<label>필요 금액 ({e(p["currency"])})<input name="amount" inputmode="decimal" required></label>'
        '<label>필요일<input type="date" name="day" required></label>',
        "현금 일정",
    )

    def list_evidence(groups):
        return "".join(
            f'<details><summary>{e(categories[k]["title"])} · {len(rows)}건</summary>'
            + "".join(item(r) for r in rows)
            + "</details>"
            for k, rows in groups.items()
        )

    return (
        f'<section id="position" class="card"><div id="position-summary" data-watch><h2>{e(p["symbol"])}</h2><p>{e(store.PROVIDERS[p["provider"]])} · {e(p["account"])} · {e(p["as_of"])} · {e(p["currency"])} 내 비중 {e(p["weight_pct"] or "미평가")}</p>'
        + "".join(tag(intel.LABELS[k] + " · " + v) for k, v in p["tasks"].items())
        + "<h3>종목 직접 근거</h3>"
        + list_evidence(p["direct"])
        + "<h3>분야 공통 참고</h3>"
        + (list_evidence(p["context"]) or "<p>연결된 공통 관측 없음</p>")
        + '</div><details><summary>담당·연결어·근거·현금 일정 관리</summary><div class="forms">'
        + controls
        + "</div></details></section>"
    )


def daily_panel(package, route):
    reports = intel.private_json(package, daily_review.FILE, {})
    if not reports:
        return ""
    r = reports[max(reports)]
    out = ['<section id="daily"><h2>일일 투자 검토</h2>',
           f'<p>생성 {e(r["generated"])} · 보유분 평가손익. 실현손익·입출금 이력은 포함하지 않습니다.</p>']
    if r["missing_providers"]:
        out.append("<p>잔고 미수집 · " + e(", ".join(store.PROVIDERS[k] for k in r["missing_providers"])) + "</p>")
    if r.get("valuation_basis"):
        out.append(f'<small>{e(r["valuation_basis"])}</small>')
    overnight = r.get("overnight_watch")
    if overnight:
        out.append(f'<h3>미국 반도체 장 마감 · 한국 시초가 위험</h3><p><b>{e(overnight["state"])}</b>'
                   f' · 미국 거래일 {e(overnight["day"])}</p>')
        for symbol, sample in overnight["samples"].items():
            out.append(f'<a href="{e(sample["source"])}" rel="noreferrer noopener" target="_blank">'
                       f'{e(symbol)} {sample["change_pct"]:+.2f}%</a> · 확인 {e(live_panel.time(sample["checked"]))} ')
        out.append('<p>SOXX와 NVDA 종가가 각각 5% 이상 하락하면 현금 유지 대안과 시초가 체결비용을 재검토합니다. '
                   '두 표본은 노출이 겹칩니다. 보유 판단에는 별도 근거가 필요합니다. 국내 반도체의 시장 대비 강도와 외국인 순매수 회복 여부를 확인합니다.</p>')
    watch = r.get("price_watch")
    if watch:
        out.append('<details><summary>보유 주식 하락 경보</summary>'
                   '<p>종가가 이틀 연속 60일선 아래이고 60거래일 최고 종가에서 10% 이상 하락하면 보유 가설을 재검토합니다.</p>'
                   f'<small>{e(watch["state"])}</small>')
        for item in watch["rows"]:
            out.append(f'<div class="row"><b>{e(item["symbol"])}</b> · {e(item["status"])}'
                       f'<small>{e(item["venue"])} · 마지막 검증 종가 {e(item["day"])}</small></div>')
        out.append('</details>')
    for ccy, c in r["currencies"].items():
        pct = c["recovery_pct"]
        out.append(f'<details><summary>{e(ccy)} · 확인분 순평가손익 {e(fmt(c["net"]))} · 확인 {c["known"]}/{c["total"]}행</summary>'
                   + f'<p>손실 종목 합계(절댓값) {e(fmt(c["gross_loss"]))} · 확인된 보유분 원가 회복에 필요한 수익률 '
                   + (e(pct) + "%" if pct is not None else "계산 보류") + '</p>')
        for row in c["losses"]:
            url = route + "?position=" + row["id"] + "#position"
            out.append(f'<div class="row"><a href="{e(url)}">{e(row["symbol"])}</a> · {e(store.PROVIDERS[row["provider"]])} · {e(row["account"])} · '
                       f'{e(fmt(row["pnl"]))} {e(ccy)} · 확인된 손실 중 {e(row["loss_share_pct"])}%'
                       f'<small>{("엑셀 수정시각" if row["source"] == "workbook" else "잔고 기준시각")} {e(row["as_of"])} · ' +
                       (e(row["valuation_state"]) + " · " + live_panel.time(row.get("quote_at")) + " · " if row.get("valuation_state") else "") +
                       ("최근 직접 근거 " + e(row["evidence"][0]["title"]) if row["evidence"] else "최신 직접 근거 확인 필요") + "</small></div>")
        out.append("</details>")
    if "observations" in r:
        compared = r["compared_to"]
        heading = f'{compared} 검토 이후 새로 확인하거나 수정한 종목 근거' if compared else '첫 검토에서 확인한 종목 근거'
        observations = r["new_observations"] if compared else r["observations"]
        out.append(f'<details><summary>{e(heading)} · {len(observations)}건</summary>')
        for obs in observations:
            target = route + "?position=" + obs["position"] + "#position"
            out.append(f'<div class="row"><a href="{e(target)}">{e(obs["symbol"])}</a> · {e(obs["title"])} · {e(obs["value"])}'
                       f'<small>{e(obs["as_of"])} · {e(obs["analysis"])}</small></div>')
        if not observations:
            out.append("<p>이 조건에 해당하는 직접 관측이 없습니다.</p>")
        out.append("</details>")
    out.append('<details><summary>공개 자금 흐름과 테마 검토</summary><p>같은 출처·시장·기간·단위 안에서 순유입이 큰 순서입니다. 펀드별 수치는 해당 상품의 관측값입니다.</p>')
    for f in r["flows"]:
        out.append(f'<div class="row"><b>{e(f["theme"])}</b> · {e(f["net"])} {e(f["unit"])}<small>{e(f["market"])} · {e(f["period"])} · '
                   f'{e(f["as_of"])} · {e(f["metric"])} · <a href="{e(f["source"])}" rel="noreferrer noopener" target="_blank">원문</a></small></div>')
    if not r["flows"]:
        out.append("<p>이 날짜에 확인된 공개 수급 수치가 없습니다.</p>")
    out.append("</details></section>")
    return "".join(out)


def category_panel(cats, route, *, compact=False):
    title = "데이터 범주" if compact else "정보 분석"
    out = [f'<section id="analysts" data-watch><h2>{title}</h2><div class="analysts">']
    for cid, c in cats.items():
        n = len(c["observations"])
        pending = any(r["status"] not in ("수집 완료", "로컬 계산") for r in c["runs"])
        target = e(route + "/portfolio?" + urlencode({"category":cid}) + "#sources")
        if compact:
            out.append(f'<a class="category-link" href="{target}"><b>{e(c["title"])}</b>'
                       f'<small>관측 {n}건{" · 원천 확인 필요" if pending else ""}</small></a>')
        else:
            out.append(f'<article class="card"><h3>{e(c["title"])}</h3><p>{e(c["assessment"])}</p>'
                       f'<div>{tag(str(n)+"건",not n)}{tag("원천 확인 필요",True) if pending else ""}</div>'
                       f'<a href="{target}">원천·관측 보기</a></article>')
    return "".join(out) + '</div></section>'


def render(directory, package, route, csrf, query):
    book = live_valuation.read(package)
    b = intel.board(directory, package, quote_book=book)
    accounts, positions, cats = b["accounts"], b["positions"], b["categories"]
    active = query.get("agent")
    provider = query.get("provider")
    chosen = next((p for p in positions if p["id"] == query.get("position")), None)

    def href(params, anchor):
        return e(
            route + "/portfolio"
            + ("?" + urlencode({k: v for k, v in params.items() if v}) if any(params.values()) else "")
            + "#"
            + anchor
        )

    def chip(name, params, selected):
        return (
            f'<a class="chip{" active" if selected else ""}" href="{href(params,"holdings")}">{e(name)}</a>'
        )

    cov = {a["provider"] for a in accounts}
    counts = Counter(task for p in positions for task in p["tasks"])
    out = [
        '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        "<title>투자 관리 · Whale Tracking</title><style>" + CSS + "</style>" + live_panel.script(route) + "</head><body>",
        '<header><div><strong>Whale Tracking</strong><small>로컬 전용 · 직접 거래 보류</small></div></header>',
        chat_page.navigation(route, "portfolio"), '<main><div class="chips"><a class="chip" href="#live-values">보유 종목 현재가</a><a class="chip" href="#holdings">보유 현황</a><a class="chip" href="#price-history">가격 이력</a>'
        '<a class="chip" href="#analysts">정보 분석</a><a class="chip" href="#calendar">현금 일정</a>'
        '<a class="chip" href="#stress">하방 스트레스</a><a class="chip" href="#performance">입출금 조정 성과</a>'
        f'<a class="chip" href="{e(route)}/accounts">계좌 원장</a></div>',
        '<section><div class="spread"><div><h1>투자 관리</h1></div>',
        f'<div class="chips"><a class="chip" href="{e(route)}/portfolio">계좌 다시 읽기</a>'
        + form(route, csrf, "refresh", "정보 범주 갱신")
        + "</div>"
        + '</div><div class="metrics" id="portfolio-counts" data-watch>',
        metric("자료가 있는 기관", f"{len(cov)} / {len(store.PROVIDERS)}"),
        metric("계좌", len(accounts)),
        metric("보유 행 · 계좌별", len(positions)),
        metric("정보가 있는 범주", f'{sum(bool(c["observations"]) for c in cats.values())} / {len(cats)}'),
        "</div></section>",
        research_page.action_cockpit(directory, package, route, quote_book=book, accounts=accounts),
        concentration_panel(positions, package, route),
        live_panel.panel(directory, package, book, accounts, detail_base=route),
        history_panel.position_history(package, accounts, route, query.get("position"),query.get("frame","day")),
    ]
    if set(store.PROVIDERS) - cov:
        out.append(
            "<p>미수집 기관 · " + e(", ".join(n for k, n in store.PROVIDERS.items() if k not in cov)) + "</p>"
        )
    out.append("<details><summary>이전 수동 시세 점검</summary>" + market_marks_panel(package) + "</details>")
    out.append(chat_page.market_panel(package))
    out.append(daily_panel(package, route + "/portfolio"))
    out.append(stress_panel(positions, route, query.get("stress")))
    out.append(account_performance.panel(package, route, csrf))
    if chosen:
        out.append(position_detail(chosen, cats, route, csrf, quote_book=book))
    out.append(
        '<section id="holdings" data-watch><h2>포트폴리오</h2><div class="chips">'
        + chip("모든 담당", dict(provider=provider), not active)
    )
    out.extend(
        chip(f"{label} {counts[key]}", dict(agent=key, provider=provider), active == key)
        for key, label in intel.LABELS.items()
    )
    out.append('</div><div class="chips">' + chip("모든 기관", dict(agent=active), not provider))
    out.extend(
        chip(name, dict(provider=k, agent=active), k == provider)
        for k, name in store.PROVIDERS.items()
        if k in cov
    )
    out.append(
        '</div><div class="panel"><table><thead><tr><th>종목</th><th>계좌</th><th>담당</th><th>통화 내 비중</th><th>직접 근거</th><th>기준일</th></tr></thead><tbody>'
    )
    visible = [
        p
        for p in positions
        if (not active or active in p["tasks"]) and (not provider or p["provider"] == provider)
    ]
    for p in visible:
        labels = [
            intel.LABELS[k] + (" · 유형 확인" if "상품 유형" in t else "") for k, t in p["tasks"].items()
        ]
        out.append(
            f'<tr><td><a href="{href(dict(position=p["id"],agent=active,provider=provider),"position")}">{e(p["symbol"])}</a></td>'
            f'<td>{e(store.PROVIDERS[p["provider"]])} · {e(p["account"])}</td><td>'
            + ("".join(tag(x) for x in labels) or "현금·기타")
            + f'</td><td>{e(p["currency"])} · {e(p["weight_pct"]+"%" if p["weight_pct"] is not None else "미평가")}</td>'
            f'<td>{sum(map(len,p["direct"].values()))}</td><td>{e(p["as_of"][:10])}</td></tr>'
        )
    if not visible:
        out.append('<tr><td colspan="6">이 조건에 배정된 보유 행이 없습니다.</td></tr>')
    out.append('</tbody></table></div></section>')
    out.append(category_panel(cats, route))
    if query.get("category") in cats:
        c = cats[query["category"]]
        out.append(
            f'<section class="panel" id="sources"><h2>{e(c["title"])}</h2><p>담당 · '
            + e(", ".join(intel.LABELS[k] for k in c["agents"]))
            + "</p>"
        )
        if c["id"] != "exposure":
            out.append(
                form(
                    route,
                    csrf,
                    "refresh",
                    "이 범주 갱신",
                    extra=f'<input type="hidden" name="category" value="{e(c["id"])}">',
                )
            )
        for r in c["runs"]:
            out.append(
                f'<div class="row"><b>{e(r["label"])}</b> · {e(r["status"])} · {r["count"]}건 · 기준일 경과 {r["stale"]}건<small>최근 시도 {e(r["attempt"] or "—")} · 마지막 자료 확보 {e(r["collected"] or "—")} · {e(r.get("via") or "")}</small></div>'
            )
        out.extend(item(r) for r in sorted(c["observations"], key=lambda r: r["as_of"], reverse=True))
        out.append("</section>")
    out.append('<section id="calendar"><h2>현금 일정</h2>')
    if not b["cash_dates"]:
        out.append(
            "<p>등록된 일정이 없습니다. 보유 종목에서 만기·보증금 반환 등 현금이 필요한 날짜를 등록할 수 있습니다.</p>"
        )
    for r in sorted(b["cash_dates"], key=lambda r: r["day"]):
        out.append(
            f'<div class="card spread"><div><b>{e(r["day"])} · {e(r["title"])}</b><p>{e(store.PROVIDERS[r["provider"]])} · {e(r["account"])} · {e(fmt(r["amount"]))} {e(r["currency"])}</p></div>'
            + form(
                route,
                csrf,
                "remove-date",
                "일정 해제",
                extra=f'<input type="hidden" name="entry" value="{e(r["id"])}">',
            )
            + "</div>"
        )
    return "".join(out + ["</section></main></body></html>"]).encode()
