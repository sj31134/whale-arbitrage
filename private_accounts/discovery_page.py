"""Authenticated non-portfolio leader discovery dashboard. Local portfolio filtering stays on Mac."""

from html import escape
from urllib.parse import urlencode

from agents.portfolio import normalize, portfolio_accounts
from . import chat_page, discovery, live_valuation

e = escape

AXIS_META = (
    ("flow", "수급·매집", 25),
    ("tech", "차트·상대강도", 25),
    ("value", "이슈·내재가치", 20),
    ("sns", "X·SNS 심리", 10),
    ("macro", "글로벌 흐름", 10),
    ("geo", "지정학·공급망", 10),
)


def _held_keys(directory, package):
    if directory is None and package is None:
        return set(), set()
    qb = live_valuation.read(package)
    accounts = portfolio_accounts(directory, package, quote_book=qb)
    codes, names = set(), set()
    for acc in accounts:
        for m in acc.get("marks", ()):
            sym = m["symbol"].strip()
            names.add(normalize(sym).replace(" ", ""))
            codes.add(sym.upper())
            if m.get("instrument"):
                codes.add(m["instrument"][1].upper())
    return codes, names


def _fmt_px(val, ccy):
    if val is None:
        return "—"
    return f"{val:,.0f}원" if ccy == "KRW" else f"${val:,.2f}"


def _grade_badge(item):
    total = item["total"]
    rsi = item["tech"]["rsi"]
    if rsi > 78:
        return '<span class="badge-warn">단기 과열 · 눌림목 대기</span>'
    if total >= 76:
        return '<span class="badge-pass">S급 주도 대장주 · 최우선 후보</span>'
    if total >= 66:
        return '<span class="badge-info">A급 수급·해자 우위 후보</span>'
    return '<span class="badge-muted">관찰 · 추세 확인 대기</span>'


def _axis_bars(scores):
    rows = []
    for key, label, cap in AXIS_META:
        val = scores.get(key, 0)
        pct = min(100.0, max(4.0, 100.0 * val / cap))
        cls = "best" if pct >= 75 else ("pos" if pct >= 50 else "neg")
        rows.append(
            f'<div class="era-line"><span><b>{e(label)}</b></span>'
            f'<div class="meter"><i class="{cls}" style="width:{pct:.0f}%"></i></div>'
            f'<span><b>{val:g}</b> / {cap}</span></div>'
        )
    return '<div class="era-bars">' + "".join(rows) + "</div>"


def _candidate_card(rank, item, is_held):
    ccy = item["currency"]
    tech = item["tech"]
    streak_badge = (
        '<span class="badge-pass">NEW 신규 포착</span>'
        if item.get("is_new")
        else f'<span class="badge-muted">{item.get("streak", 1)}일 연속 추적</span>'
    )
    delta = item.get("score_delta")
    delta_txt = f" ({delta:+.1f}점)" if delta is not None else ""
    held_tag = ' <span class="badge-warn">내 보유 중</span>' if is_held else ""
    srcs = " · ".join(
        f'<a href="{e(s["url"])}" target="_blank" rel="noreferrer noopener">{e(s["label"])} ↗</a>'
        for s in item.get("sources", ())
    )
    target_txt = (
        f" · 목표가 {_fmt_px(item['target_price'], ccy)} ({item['upside_pct']:+.1f}%)"
        if item.get("target_price") and item.get("upside_pct") is not None
        else ""
    )
    return (
        f'<article class="era-card">'
        f'<div class="spread"><div><span class="badge-info">#{rank} · {e(item["market"])} · {e(item["theme"])}</span> '
        f'{_grade_badge(item)} {streak_badge}{held_tag}</div>'
        f'<strong>총점 {item["total"]:.1f} / 100{e(delta_txt)}</strong></div>'
        f'<h3>{e(item["name"])} <small>({e(item["symbol"])})</small></h3>'
        f'<p><b>현재가 {_fmt_px(item["price"], ccy)}</b>{e(target_txt)} · '
        f'하방변동성 권장 비중上限 <b>{tech["down_cap"]}%</b></p>'
        + _axis_bars(item["scores"])
        + '<div class="era-lesson">'
        f'<b>① 수급·이슈·가치:</b> {e(item["flow_note"])} / {e(item["value_note"])}<br>'
        f'<b>② 기술적 진입 타이밍:</b> {e(tech["status"])} → <b>{e(tech["entry_hint"])}</b><br>'
        f'<b>③ SNS·글로벌·지정학:</b> {e(item["sns_note"])} · {e(item["macro_note"])} · {e(item["geo_note"])}<br>'
        f'<b>④ 가설 철회(손절) 조건:</b> {e(item["invalidate"])}'
        "</div>"
        f"<small>{srcs}</small></article>"
    )


def _sns_form(base, csrf, notes):
    opts = "".join(f"<option>{e(t)}</option>" for t in discovery.SNS_TONES)
    recent = "".join(
        f'<div class="row"><span class="badge-muted">{e(n["market"])}:{e(n["symbol"])}</span> '
        f'<b>{e(n["tone"])}</b> · {e(n["summary"])} '
        f'<small>{e(n["recorded"][:16].replace("T", " "))} · {chat_page.source_link(n["url"])}</small></div>'
        for n in notes[:8]
    )
    return (
        '<details id="sns-radar"><summary>X(트위터)·SNS 이슈 및 감성 직접 검증·등록 (루머·과열 필터)</summary>'
        "<p>X나 커뮤니티에서 급속도로 퍼지는 종목 이슈·호재·루머가 있다면 원문 링크와 분위기를 기록하세요. "
        "다음 대장주 분석 때 공식 공시·수급과 교차해 가점 또는 과열 경고를 즉시 반영합니다.</p>"
        f'<form class="research-form" method="post" action="{e(base)}/desk/manager/discover-sns">'
        f'<input type="hidden" name="csrf" value="{e(csrf)}">'
        '<label>시장<select name="market"><option value="KR">한국 (KR)</option><option value="US">미국 (US)</option></select></label>'
        '<label>종목코드·티커<input name="symbol" required maxlength="12" placeholder="012450 또는 PLTR"></label>'
        f'<label>SNS 감성 판정<select name="tone">{opts}</select></label>'
        '<label>핵심 주장·분위기 요약<input name="summary" required maxlength="240" placeholder="예: 유럽 대규모 추가 수주설 확산"></label>'
        '<label>X·게시물 원문 URL<input name="url" type="url" required placeholder="https://x.com/..."></label>'
        "<button>SNS 관측 저장 및 반영</button></form>"
        + (recent or "<small>아직 수동 등록한 X·SNS 검증 메모가 없습니다.</small>")
        + "</details>"
    )


def render(directory, package, base, csrf, query, css):
    doc = discovery.read(package)
    market_filter = query.get("market", "all")
    if market_filter not in ("all", "KR", "US"):
        market_filter = "all"
    theme_filter = query.get("theme", "")
    include_held = query.get("include_held") == "1"
    done = query.get("done")

    held_codes, held_names = _held_keys(directory, package)

    def is_held(item):
        return (
            item["symbol"].upper() in held_codes
            or normalize(item["name"]).replace(" ", "") in held_names
        )

    all_cands = doc.get("candidates", [])
    excluded_held = sum(1 for c in all_cands if is_held(c))
    themes = sorted({c["theme"] for c in all_cands})

    filtered = []
    for c in all_cands:
        if not include_held and is_held(c):
            continue
        if market_filter != "all" and c["market"] != market_filter:
            continue
        if theme_filter and c["theme"] != theme_filter:
            continue
        filtered.append(c)

    def link(m_val, t_val="", inc=include_held):
        params = {}
        if m_val != "all":
            params["market"] = m_val
        if t_val:
            params["theme"] = t_val
        if inc:
            params["include_held"] = "1"
        q_str = ("?" + urlencode(params)) if params else ""
        return e(base + "/discover" + q_str)

    ctx = doc.get("context", {})
    sns_top_txt = (
        ", ".join(f"{r['symbol']}({r['mentions']}건)" for r in ctx.get("sns_top", [])[:5])
        or "수집 대기"
    )

    out = [
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>신규 대장주 발굴 · Whale Tracking</title><style>{css}</style></head><body>",
        chat_page.navigation(base, "discover"),
        '<main class="desk-main">',
        '<div class="spread"><div><h1>포트폴리오 외 신규 대장주 발굴</h1>'
        "<p>내 계좌에 없는 외부 종목 가운데 <b>수급 · 기술적 상대강도 · 이슈/가치 · X/SNS 심리 · 글로벌 흐름 · 지정학</b> "
        "6대 변수가 동시에 모이는 시장 주도주를 매일 추적합니다.</p></div>"
        f'<form method="post" action="{e(base)}/desk/manager/discover-run">'
        f'<input type="hidden" name="csrf" value="{e(csrf)}">'
        "<button>오늘의 대장주 새로 분석하기</button></form></div>",
    ]
    if done == "refreshed":
        out.append('<p role="status" class="badge-pass">최신 공개 수급·차트·SNS·지정학 데이터를 반영해 대장주 순위를 갱신했습니다.</p>')
    elif done == "sns":
        out.append('<p role="status" class="badge-pass">X·SNS 관측을 저장하고 대장주 감성 점수에 반영했습니다.</p>')

    out.append(
        '<div class="guide-banner"><h2>오늘의 6대 변수 레이더 요약</h2>'
        '<div class="step-flow">'
        f'<div class="step-box"><b><span class="step-num">1</span>글로벌·환율 흐름</b>'
        f'<small>원·달러 {ctx.get("fx_rate", 0):,.1f}원 · 한국지수 20일 {ctx.get("kr_bench_ret20", 0):+.1f}% / 미국지수 20일 {ctx.get("us_bench_ret20", 0):+.1f}%</small></div>'
        f'<div class="step-box"><b><span class="step-num">2</span>지정학·정책 핵심</b>'
        f'<small>유엔 안보: {e(ctx.get("un_headline", "점검 대기")[:70])}<br>연준: {e(ctx.get("fed_headline", "점검 대기")[:60])}</small></div>'
        f'<div class="step-box"><b><span class="step-num">3</span>X · 글로벌 SNS 심리</b>'
        f'<small>X 공식 API: {e(ctx.get("x_status", "토큰 미설정"))}<br>커뮤니티 최다 언급: {e(sns_top_txt)}</small></div>'
        f'<div class="step-box"><b><span class="step-num">4</span>내 보유 종목 분리</b>'
        f'<small>전체 후보 {len(all_cands)}종목 중 <b>내 보유 {excluded_held}종목 자동 제외</b> · 순수 신규 후보만 집중 탐색</small></div>'
        "</div></div>"
    )

    # Filter chips
    out.append('<div class="chips">')
    for m_code, m_label in (("all", "전체 (한·미 통합)"), ("KR", "한국 대장주 (KRX)"), ("US", "미국 글로벌 대장주 (US)")):
        cls = "chip active" if market_filter == m_code and not theme_filter else "chip"
        out.append(f'<a class="{cls}" href="{link(m_code, "")}">{m_label}</a>')
    toggle_cls = "chip active" if include_held else "chip"
    out.append(
        f'<a class="{toggle_cls}" href="{link(market_filter, theme_filter, not include_held)}">'
        f'{"내 보유 종목 숨기기" if include_held else f"내 보유 종목({excluded_held}개) 함께 비교"}</a>'
    )
    out.append(f'<a class="chip" href="{e(base)}/research#create">가설 연구장에 새 후보 등록하기 →</a></div>')

    if themes:
        out.append('<div class="chips"><small>테마 필터:</small>')
        for th in themes:
            cls = "chip active" if theme_filter == th else "chip"
            out.append(f'<a class="{cls}" href="{link(market_filter, "" if theme_filter == th else th)}">{e(th)}</a>')
        out.append("</div>")

    if not doc.get("candidates"):
        out.append(
            '<section class="card"><h2>첫 대장주 스캔 대기</h2>'
            "<p>우측 상단 <b>오늘의 대장주 새로 분석하기</b> 버튼을 누르거나 터미널에서 "
            "<code>python3 -m private_accounts discover --refresh</code>를 실행하면 6대 변수 대장주 순위가 생성됩니다.</p></section>"
        )
    else:
        s_count = sum(1 for c in filtered if c["total"] >= 76 and c["tech"]["rsi"] <= 78)
        new_count = sum(1 for c in filtered if c.get("is_new"))
        out.append(
            '<div class="kpi-strip">'
            f'<div class="kpi-box info"><small>최근 분석 기준시각</small><strong>{e(doc.get("updated", "")[:16].replace("T", " "))}</strong></div>'
            f'<div class="kpi-box pass"><small>S급 주도 대장주 (≥76점)</small><strong>{s_count}종목</strong></div>'
            f'<div class="kpi-box info"><small>표시 중인 신규 후보</small><strong>{len(filtered)}종목</strong></div>'
            f'<div class="kpi-box warn"><small>오늘 새로 진입(NEW)</small><strong>{new_count}종목</strong></div>'
            "</div>"
        )
        out.append('<section><h2>포트폴리오 외 대장주 종합 순위</h2><div class="era-grid">')
        for idx, item in enumerate(filtered[:16], 1):
            out.append(_candidate_card(idx, item, is_held(item)))
        if not filtered:
            out.append("<p>선택한 시장·테마 조건에 해당하는 포트폴리오 외 종목이 없습니다.</p>")
        out.append("</div></section>")

    out.append(_sns_form(base, csrf, discovery.sns_notes(package)))

    # Daily tracking history summary
    hist = doc.get("history", {})
    if hist:
        out.append(
            '<details><summary>일자별 대장주 추적 이력 (최근 기록)</summary>'
            '<div class="comparison"><table><thead><tr><th>날짜</th><th>상위 포착 종목 (총점 · 연속일)</th></tr></thead><tbody>'
        )
        for d in sorted(hist, reverse=True)[:10]:
            day_map = hist[d]
            top_items = sorted(day_map.items(), key=lambda kv: -kv[1]["total"])[:5]
            summary = " · ".join(
                f'{v["name"]}({k.split(":")[1]}, {v["total"]:.1f}점, {v["streak"]}일차)'
                for k, v in top_items
            )
            out.append(f"<tr><td><b>{e(d)}</b></td><td>{e(summary)}</td></tr>")
        out.append("</tbody></table></div></details>")

    out.append("</main></body></html>")
    return "".join(out).encode()
