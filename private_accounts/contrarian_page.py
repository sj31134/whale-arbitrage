"""Authenticated Contrarian Variant-Perception & 1-Stock Bespoke Strategy Workbench."""

from html import escape
from urllib.parse import urlencode

from agents.portfolio import normalize, portfolio_accounts
from . import chat_page, contrarian, live_valuation

e = escape


def _fmt_px(val, ccy):
    if val is None or val == "":
        return "—"
    v = float(val)
    return f"{v:,.0f}원" if ccy == "KRW" else f"${v:,.2f}"


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


def _research_prefill(base, *, name, symbol, ccy, entry, floor, target, bull, url, catalyst, kill_switch):
    fmt = (lambda v: str(round(float(v)))) if ccy == "KRW" else (lambda v: f"{float(v):.2f}")
    params = dict(
        asset=f"{name} ({symbol})" if symbol not in name else name,
        currency=ccy,
        entry=fmt(entry),
        bear=fmt(floor),
        base=fmt(target),
        bull=fmt(bull),
        price_source=url,
        catalyst=catalyst[:220],
        invalidate=kill_switch[:200],
    )
    return e(base + "/research?" + urlencode(params) + "#create")


def _archetype_section():
    cards = []
    for a in contrarian.ARCHETYPES.values():
        srcs = " · ".join(
            f'<a href="{e(u)}" target="_blank" rel="noreferrer noopener">{e(lbl)} ↗</a>'
            for lbl, u in a["sources"]
        )
        cards.append(
            f'<article class="era-card">'
            f'<span class="badge-info">{e(a["badge"])}</span>'
            f'<h3>{e(a["master"])}</h3>'
            f'<p><small><b>실증 트랙레코드:</b> {e(a["track_record"])}</small></p>'
            f'<div class="era-lesson">'
            f'<b>핵심 철학:</b> {e(a["core_quote"])}<br>'
            f'<b>① 대중의 시선 착시:</b> {e(a["crowd_blindspot"])}<br>'
            f'<b>② 독점 인사이트 공식:</b> {e(a["edge_formula"])}<br>'
            f'<b>③ 1종목 집행 규칙 ({e(a["horizon"])}):</b> {e(a["execution_rule"])} · 최소 비대칭 손익비 <b>{a["min_asymmetry"]:.1f}배+</b>'
            f'</div><small>{srcs}</small></article>'
        )
    return (
        '<section><h2>1. 조사·분석 · 대중과 반대로 베팅해 압도적 부를 만든 3대 아키타입</h2>'
        '<p>기존 메뉴(<code>/discover</code> · <code>/quant</code>)가 수급·차트·컨센서스의 <b>다수결 과반수 동의(통계적 승률)</b>를 찾는다면, '
        '이 메뉴는 <b>다수의 오해가 만든 가격 왜곡과 기업의 본질 가치 사이의 거대한 빈틈(Variant Perception)</b>에 남들보다 한발 앞서 1종목 맞춤 전략을 설계합니다.</p>'
        f'<div class="era-grid">{"".join(cards)}</div></section>'
    )


def _validation_section():
    vm = contrarian.VALIDATION_MATRIX
    comp_rows = "".join(
        f"<tr><td><b>{e(axis)}</b></td><td>{e(maj)}</td><td><b>{e(con)}</b></td></tr>"
        for axis, maj, con in vm["comparison"]
    )
    case_rows = "".join(
        f'<tr><td><b>{e(c["name"])}</b><br><small>{e(c["archetype"])}</small></td>'
        f'<td><span class="{"badge-warn" if "함정" in c["verdict"] else "badge-pass"}">{e(c["verdict"])}</span></td>'
        f'<td>{e(c["trough"])}<br>→ <b>{e(c["peak_or_now"])}</b></td>'
        f'<td><small><b>당시 대중 시선:</b> {e(c["crowd_then"])}<br><b>본질 괴리/교훈:</b> {e(c["variant_edge"])}</small></td></tr>'
        for c in vm["cases"]
    )
    return (
        '<details open><summary>2. 전략·실증 검증 · 다수결 통계 vs 역발상 비대칭 비교 및 ‘가치함정(Value Trap)’ 반증 (2021~2026 실측)</summary>'
        f'<p>{e(vm["summary"])}</p>'
        '<div class="comparison"><table><thead><tr><th>비교 축</th><th>기존 다수결·합의 전략 (/discover · 모멘텀)</th><th>역발상·비대칭 1종목 집중 전략 (/contrarian)</th></tr></thead>'
        f'<tbody>{comp_rows}</tbody></table></div>'
        '<h3>실제 역사적 변곡점 적중 사례 vs 가치함정 반증 사례</h3>'
        '<div class="comparison"><table><thead><tr><th>종목 · 유형</th><th>검증 결과</th><th>공포 바닥 진입 → 이후 성과</th><th>대중 시선 vs 독점 인사이트 (반증 포함)</th></tr></thead>'
        f'<tbody>{case_rows}</tbody></table></div></details>'
    )


def _gap_bars(scores):
    meta = (
        ("essence", "본질 해자·생존력 (함정방어)", 35),
        ("gap", "대중 외면·가격괴리 깊이", 35),
        ("asymmetry", "상방/하방 비대칭 볼록성", 30),
    )
    rows = []
    for k, lbl, cap in meta:
        val = scores.get(k, 0)
        pct = min(100.0, max(5.0, 100.0 * val / cap))
        cls = "best" if pct >= 75 else ("pos" if pct >= 52 else "neg")
        rows.append(
            f'<div class="era-line"><span><b>{e(lbl)}</b></span>'
            f'<div class="meter"><i class="{cls}" style="width:{pct:.0f}%"></i></div>'
            f'<span><b>{val:g}</b> / {cap}</span></div>'
        )
    return '<div class="era-bars">' + "".join(rows) + "</div>"


def _candidate_card(rank, item, is_held, base):
    ccy = item["currency"]
    overheated = item.get("overheated", False)
    if overheated:
        shield_badge = '<span class="badge-warn">단기 과열·군중 동의 구간 (역발상 매수 잠금)</span>'
    elif item["trap_shield_ok"]:
        shield_badge = '<span class="badge-pass">해자·여신생존·비대칭 통과</span>'
    else:
        shield_badge = '<span class="badge-muted">괴리 형성 관찰 중</span>'
    held_badge = ' <span class="badge-warn">내 보유 중</span>' if is_held else ""
    t1, t2, t3 = item["tranches"]
    sz = item.get("sizing") or contrarian.compute_position_sizing(
        upside_pct=item["upside_pct"],
        downside_pct=item["downside_pct"],
        blocked=overheated,
    )
    solv_lbl = item.get("solvency_label", contrarian.SOLVENCY_TIERS["backlog_float"]["label"])
    solv_note = item.get("solvency_note", "")
    prefill = _research_prefill(
        base,
        name=item["name"],
        symbol=item["symbol"],
        ccy=ccy,
        entry=item["price"],
        floor=item["floor_price"],
        target=item["target_price"],
        bull=item["bull_price"],
        url=item["source_url"],
        catalyst=f"[역발상·{item['archetype_badge']}] {item['moat_essence']}",
        kill_switch=item["kill_switch"],
    )
    builder_params = urlencode(dict(
        pb_market=item["market"],
        pb_symbol=item["symbol"],
        pb_name=item["name"],
        pb_arch=item["archetype"],
        pb_solvency=item.get("solvency_tier", "backlog_float"),
        pb_entry=str(item["price"]),
        pb_floor=str(item["floor_price"]),
        pb_target=str(item["target_price"]),
        pb_horizon=item["horizon"],
        pb_crowd=item["crowd_fear"][:280],
        pb_insight=item["moat_essence"],
        pb_kill=item["kill_switch"],
        pb_url=item["source_url"],
    ))
    builder_href = e(base + "/contrarian?" + builder_params + "#playbook-builder")
    tranche_line = (
        f'<b>③ 과열 진입 브레이크 ({e(item["horizon"])}):</b> 현재 고점 근접·RSI 과열로 즉시 진입 금지 · '
        f'향후 2차 조정선({_fmt_px(t2, ccy)})·3차 공포 바닥({_fmt_px(t3, ccy)}) 도달 시에만 재점검'
        if overheated
        else f'<b>③ 1종목 내림차순 분할매집 공식 ({e(item["horizon"])}):</b> '
        f'1차 선발 {_fmt_px(t1, ccy)}(30%) &gt; 2차 투매 {_fmt_px(t2, ccy)}(40%) &gt; 3차 바닥 {_fmt_px(t3, ccy)}(30%) / {e(item["execution_rule"])}'
    )
    return (
        f'<article class="era-card">'
        f'<div class="spread"><div><span class="badge-info">#{rank} · {e(item["market"])} · {e(item["archetype_badge"])}</span> '
        f'{shield_badge}{held_badge}</div>'
        f'<strong>괴리 총점 {item["total"]:.1f} / 100</strong></div>'
        f'<h3>{e(item["name"])} <small>({e(item["symbol"])})</small></h3>'
        f'<p><b>현재가 {_fmt_px(item["price"], ccy)}</b> <small>(52주 고점 대비 {item["dd52"]:+.1f}% · 60일선 {item["pct60"]:+.1f}% · RSI {item["rsi"]:.0f})</small><br>'
        f'하방 바닥 <b>{_fmt_px(item["floor_price"], ccy)}</b>(-{item["downside_pct"]:.1f}%) vs '
        f'본질 복원 목표 <b>{_fmt_px(item["target_price"], ccy)}</b>(+{item["upside_pct"]:.1f}%) → '
        f'<b><abbr title="하방 손실폭 대비 상방 복원 수익률 배수">비대칭 손익배수</abbr> {item["asymmetry"]:.2f}배</b> · 안전마진 <b>{item["margin_pct"]:.1f}%</b><br>'
        f'<small><b>포지션 사이징(헤지펀드·전업 기준):</b> '
        f'<abbr title="승률 55% 가정 부분손실 1/4 켈리 비중과 1.2R 손실예산·재무등급 상한 중 최소치">권장 베팅 비중</abbr> '
        f'<b>계좌의 {sz["recommended_pct"]:.1f}%</b> '
        f'(1/4켈리 {sz["kelly_quarter_pct"]:.1f}% · 1.2R예산 {sz["r_budget_pct"]:.1f}% · 등급상한 {sz["cap_pct"]:.0f}%)</small></p>'
        + _gap_bars(item["scores"])
        + '<div class="era-lesson">'
        f'<b>① 다수의 현재 오해·공포:</b> {e(item["crowd_fear"])}<br>'
        f'<b>② 숨겨진 본질·독점 빈틈:</b> {e(item["moat_essence"])}<br>'
        f'{tranche_line}<br>'
        f'<b>④ 은행 여신심사 재무생존 체크:</b> {e(solv_lbl)}'
        + (f' — <small>{e(solv_note)}</small>' if solv_note else '')
        + f'<br><b>⑤ 유일한 가설 철회 데드라인(Kill-Switch):</b> {e(item["kill_switch"])}'
        '</div>'
        f'<div class="spread"><a href="{e(item["source_url"])}" target="_blank" rel="noreferrer noopener">원문 시세·재무 확인 ↗</a>'
        f'<div><a class="chip" href="{builder_href}">내 1종목 전략으로 커스텀 설계 ↓</a> '
        f'<a class="chip" href="{prefill}">가설 연구장 공식 등록 →</a></div></div></article>'
    )


def _builder_section(base, csrf, query, saved):
    q = query or {}
    open_attr = " open" if (q.get("pb_symbol") or q.get("done") == "saved" or not saved) else ""
    arch_opts = "".join(
        f'<option value="{e(k)}"{" selected" if q.get("pb_arch") == k else ""}>{e(v["badge"])} (최소 손익배수 {v["min_asymmetry"]:.1f}배+)</option>'
        for k, v in contrarian.ARCHETYPES.items()
    )
    def_solv = q.get("pb_solvency", "backlog_float")
    solv_opts = "".join(
        f'<option value="{e(k)}"{" selected" if def_solv == k else ""}>{e(v["label"])}</option>'
        for k, v in contrarian.SOLVENCY_TIERS.items()
    )
    mkt_kr_sel = " selected" if q.get("pb_market", "KR") == "KR" else ""
    mkt_us_sel = " selected" if q.get("pb_market") == "US" else ""

    saved_cards = []
    for p in saved:
        ccy = p["currency"]
        t1, t2, t3 = p["tranches"]
        solv_key = p.get("solvency", "backlog_float")
        solv_lbl = p.get("solvency_label", contrarian.SOLVENCY_TIERS.get(solv_key, contrarian.SOLVENCY_TIERS["backlog_float"])["label"])
        sz = p.get("sizing") or contrarian.compute_position_sizing(
            upside_pct=p["upside_pct"],
            downside_pct=p["downside_pct"],
            blocked=(solv_key == "distressed_block"),
        )
        if solv_key == "distressed_block":
            status_badge = '<span class="badge-warn">여신심사 부적격 (차환·희석 위험 · 1종목 집중 차단)</span>'
        elif p["passes"]:
            status_badge = '<span class="badge-pass">비대칭·안전마진·여신생존 통과 (실행 적격)</span>'
        else:
            status_badge = '<span class="badge-warn">비대칭 배수 부족 · 진입가 하향/재설계 권장</span>'
        prefill = _research_prefill(
            base,
            name=p["name"],
            symbol=p["symbol"],
            ccy=ccy,
            entry=p["entry"],
            floor=p["floor"],
            target=p["target"],
            bull=p["bull"],
            url=p["url"],
            catalyst=f"[1종목 비대칭·{p['archetype_badge']}] {p['variant_insight']}",
            kill_switch=p["kill_switch"],
        )
        saved_cards.append(
            f'<article class="investment-report">'
            f'<div class="spread"><h3>{e(p["name"])} ({e(p["market"])}:{e(p["symbol"])}) · <small>{e(p["archetype_badge"])}</small></h3>'
            f'{status_badge}</div>'
            f'<p><b>진입 기준가 {_fmt_px(p["entry"], ccy)}</b> · 하방 바닥 <b>{_fmt_px(p["floor"], ccy)}</b>(-{p["downside_pct"]:.1f}%) · '
            f'본질 복원 목표 <b>{_fmt_px(p["target"], ccy)}</b>(+{p["upside_pct"]:.1f}%) → '
            f'<b>비대칭 배수 {p["asymmetry"]:.2f}배</b> · 안전마진 <b>{p["margin_pct"]:.1f}%</b> · 호흡 <b>{e(p["horizon"])}</b><br>'
            f'<small><b>권장 베팅 비중(1/4켈리·1R 교집합):</b> <b>계좌의 {sz["recommended_pct"]:.1f}%</b> '
            f'(1/4켈리 {sz["kelly_quarter_pct"]:.1f}% · {p.get("risk_budget", 1.2):g}R예산 {sz["r_budget_pct"]:.1f}% · 상한 {sz["cap_pct"]:.0f}%) · '
            f'<b>재무생존 등급:</b> {e(solv_lbl)}</small></p>'
            f'<p><b>내림차순 3단 분할매집표:</b> 1차 정찰(30%) <b>{_fmt_px(t1, ccy)}</b> &gt; 2차 군중투매(40%) <b>{_fmt_px(t2, ccy)}</b> &gt; 3차 바닥확인(30%) <b>{_fmt_px(t3, ccy)}</b></p>'
            f'<p><b>대중의 오해:</b> {e(p["crowd_view"])}<br>'
            f'<b>나만의 독점 인사이트(빈틈):</b> {e(p["variant_insight"])}<br>'
            f'<b>유일한 철회 조건(Kill-Switch):</b> {e(p["kill_switch"])}</p>'
            f'<div class="spread"><small>설계 시각 {e(p["created"][:16].replace("T", " "))} · {chat_page.source_link(p["url"])}</small>'
            f'<a class="chip" href="{prefill}">이 설계안 그대로 가설 연구장(/research) 등록 →</a></div></article>'
        )

    return (
        f'<section id="playbook-builder"><h2>4. 1종목 1투자 맞춤 비대칭 전략 설계기 (1/4 켈리 사이징 &amp; 여신심사 내장)</h2>'
        '<p>위 괴리 카드에서 <b>내 1종목 전략으로 커스텀 설계</b>를 누르면 어려운 빈칸들이 자동으로 채워집니다. '
        '승률과 계좌 허용 손실(1R), 고금리 재무생존 등급을 검증해 <b>적정 베팅 비중(%)과 내림차순 3단 매집가</b>를 산출합니다.</p>'
        f'<details{open_attr}><summary>1종목 1투자 비대칭 시나리오 작성·검증하기</summary>'
        f'<form class="research-form" method="post" action="{e(base)}/desk/manager/contrarian-plan">'
        f'<input type="hidden" name="csrf" value="{e(csrf)}">'
        f'<label>시장<select name="market"><option value="KR"{mkt_kr_sel}>한국 (KRW)</option><option value="US"{mkt_us_sel}>미국 (USD)</option></select></label>'
        f'<label>종목코드·티커<input name="symbol" required maxlength="12" value="{e(q.get("pb_symbol", ""))}" placeholder="000660 또는 GOOG"></label>'
        f'<label>종목명<input name="name" required maxlength="80" value="{e(q.get("pb_name", ""))}" placeholder="예: SK하이닉스"></label>'
        f'<label>적용할 대가 아키타입<select name="archetype">{arch_opts}</select></label>'
        f'<label>은행 여신심사형 재무생존 등급 (고금리 차환·유증 방어)<select name="solvency">{solv_opts}</select></label>'
        f'<label>현재 진입 기준가격<input name="entry" type="number" min="0" step="any" required value="{e(q.get("pb_entry", ""))}"></label>'
        f'<label>하방 방어 바닥가 (순현금·대체원가·청산가치 근거)<input name="floor" type="number" min="0" step="any" required value="{e(q.get("pb_floor", ""))}"></label>'
        f'<label>본질 복원 목표가치 (괴리 해소 시)<input name="target" type="number" min="0" step="any" required value="{e(q.get("pb_target", ""))}"></label>'
        f'<label>예상 시나리오 적중 확률 (%, 기본 55%)<input name="win_prob" type="number" min="20" max="85" step="any" value="{e(q.get("pb_prob", "55"))}"></label>'
        f'<label>계좌 총자산 대비 이 종목 최대 허용 손실 예산 (1R %, 기본 1.2%)<input name="risk_budget" type="number" min="0.3" max="3.0" step="any" value="{e(q.get("pb_risk", "1.2"))}"></label>'
        f'<label>목표 보유 호흡 (Time Horizon)<input name="horizon" required maxlength="40" value="{e(q.get("pb_horizon", "18~24개월"))}"></label>'
        f'<label>① 지금 대중·다수가 오해하거나 공포에 빠진 이유 (남들의 착각)<textarea name="crowd_view" rows="2" required placeholder="예: 단기 레거시 적자와 매크로 관세 우려로 투매">{e(q.get("pb_crowd", ""))}</textarea></label>'
        f'<label>② 대중이 못 보는 나만의 본질·병목·빈틈 인사이트 (남들이 놓친 강점)<textarea name="variant_insight" rows="2" required placeholder="예: 차세대 물리적 병목 독점 점유율 및 선제 증설 완료">{e(q.get("pb_insight", ""))}</textarea></label>'
        f'<label>③ 차트 흔들림 대신 이 투자를 즉시 포기할 유일한 본질 훼손 조건 (유상증자·핵심 고객 이탈 등)<textarea name="kill_switch" rows="2" required placeholder="예: 핵심 고객사 이탈 공시 또는 주주가치 희석 유상증자">{e(q.get("pb_kill", ""))}</textarea></label>'
        f'<label>검증 원문 URL (DART·SEC·IR·가격 출처 HTTPS)<input name="url" type="url" required value="{e(q.get("pb_url", ""))}" placeholder="https://dart.fss.or.kr/..."></label>'
        '<button>1종목 비대칭 전략 검증 및 저장</button></form></details>'
        '<div id="my-playbooks">'
        + ("".join(saved_cards) if saved_cards else "<p><small>아직 저장한 1종목 맞춤 역발상 전략이 없습니다. 위 카드를 불러오거나 직접 작성해 보세요.</small></p>")
        + "</div></section>"
    )


def render(directory, package, base, csrf, query, css):
    doc = contrarian.read(package)
    arch_filter = query.get("archetype", "all")
    if arch_filter not in ("all", *contrarian.ARCHETYPES):
        arch_filter = "all"
    market_filter = query.get("market", "all")
    if market_filter not in ("all", "KR", "US"):
        market_filter = "all"
    include_held = query.get("include_held") == "1"
    done = query.get("done")

    held_codes, held_names = _held_keys(directory, package)

    def is_held(item):
        return (
            item["symbol"].upper() in held_codes
            or normalize(item["name"]).replace(" ", "") in held_names
        )

    all_cands = doc.get("candidates", [])
    filtered = [
        c for c in all_cands
        if (include_held or not is_held(c))
        and (market_filter == "all" or c["market"] == market_filter)
        and (arch_filter == "all" or c["archetype"] == arch_filter)
    ]

    def link(m_val=market_filter, a_val=arch_filter, inc=include_held):
        params = {}
        if m_val != "all":
            params["market"] = m_val
        if a_val != "all":
            params["archetype"] = a_val
        if inc:
            params["include_held"] = "1"
        q_str = ("?" + urlencode(params)) if params else ""
        return e(base + "/contrarian" + q_str)

    saved_plans = contrarian.playbooks(package)
    pass_count = sum(1 for c in filtered if c.get("trap_shield_ok"))

    out = [
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>역발상 · 1종목 비대칭 설계 · Whale Tracking</title><style>{css}</style></head><body>"
        "<header><div><strong>Whale Tracking</strong><small>로컬 투자 관리 · 역발상 괴리 &amp; 1종목 1전략 설계</small></div></header>",
        chat_page.navigation(base, "contrarian"),
        '<main class="desk-main">',
        '<div class="spread"><div><h1>역발상 · 시장 괴리 &amp; 1종목 1투자 전략실</h1>'
        "<p>다수결 통계 점수(모멘텀·컨센서스)가 놓치는 <b>시장의 오해와 기업의 본질 가치 사이의 빈틈(Variant Perception)</b>을 포착해, "
        "<b>캄투자일임 이호걸 · SK하이닉스 적자 바닥 선점형 · 마이클 버리</b> 방식으로 1종목 맞춤 비대칭 전략을 설계합니다.</p></div>"
        f'<form method="post" action="{e(base)}/desk/manager/contrarian-run">'
        f'<input type="hidden" name="csrf" value="{e(csrf)}">'
        "<button>시장 시선 괴리 새로 스캔하기</button></form></div>",
    ]
    if done == "refreshed":
        out.append('<p role="status" class="badge-pass">최신 52주 낙폭·60일선 이격·본질 해자 데이터를 대조해 역발상 시선 괴리 후보를 갱신했습니다.</p>')
    elif done == "saved":
        out.append('<p role="status" class="badge-pass">1종목 맞춤 비대칭 전략을 검증·저장했습니다. 아래 설계 카드에서 확인하세요.</p>')

    out.append(
        '<div class="rebalance-bar"><b>초보자·기관 통합 자금 바구니 규칙 (몰빵·가치함정 방지):</b> '
        '① <b>현금·단기금리(RP·SGOV) 버퍼 35%+</b>를 먼저 확보하고, '
        f'② 상승 추세가 확인된 주력 자금(45~50%)은 <a href="{e(base)}/discover"><b>신규 대장주 발굴(<code>/discover</code>)</b></a>에서 운용하며, '
        '③ <b>이 역발상 메뉴(<code>/contrarian</code>)는 전체 자산의 최대 10~15%(종목당 5~10% 상한 · 무차입 현물 100%)</b>만 배정하세요. '
        '고금리 차입 위험 기업이나 이미 급등한 과열 종목(RSI≥68)은 매수가 자동 잠깁니다.</div>'
    )

    out.append(_archetype_section())
    out.append(_validation_section())

    # Section 3: Live Variant-Perception Dislocation Radar
    out.append('<section id="contrarian-radar"><h2>3. 실시간 ‘다수의 시선 vs 본질’ 괴리 포착 레이더</h2>')
    out.append('<div class="chips"><small>시장:</small>')
    for m_code, m_lbl in (("all", "한·미 전체"), ("KR", "한국 (KRX)"), ("US", "미국 (US)")):
        cls = "chip active" if market_filter == m_code else "chip"
        out.append(f'<a class="{cls}" href="{link(m_val=m_code)}">{m_lbl}</a>')
    inc_cls = "chip active" if include_held else "chip"
    out.append(
        f'<a class="{inc_cls}" href="{link(inc=not include_held)}">'
        f'{"내 보유 종목 숨기기" if include_held else "내 보유 종목도 괴리 점수 함께 점검"}</a></div>'
    )
    out.append('<div class="chips"><small>아키타입 필터:</small>')
    out.append(f'<a class="{"chip active" if arch_filter == "all" else "chip"}" href="{link(a_val="all")}">전체 유형</a>')
    for k, v in contrarian.ARCHETYPES.items():
        cls = "chip active" if arch_filter == k else "chip"
        out.append(f'<a class="{cls}" href="{link(a_val=k)}">{e(v["badge"])}</a>')
    out.append("</div>")

    if not all_cands:
        out.append(
            '<div class="rebalance-bar">우측 상단 <b>시장 시선 괴리 새로 스캔하기</b> 버튼을 누르거나 '
            '<code>python3 -m private_accounts contrarian --refresh</code>를 실행하면 괴리 레이더가 생성됩니다.</div>'
        )
    else:
        out.append(
            '<div class="kpi-strip">'
            f'<div class="kpi-box info"><small>최근 괴리 스캔 시각</small><strong>{e(doc.get("updated", "")[:16].replace("T", " "))}</strong></div>'
            f'<div class="kpi-box pass"><small>해자·비대칭 통과 후보</small><strong>{pass_count}종목</strong></div>'
            f'<div class="kpi-box info"><small>표시 중인 괴리 종목</small><strong>{len(filtered)}종목</strong></div>'
            f'<div class="kpi-box warn"><small>저장된 내 1종목 전략</small><strong>{len(saved_plans)}건</strong></div>'
            '</div><div class="era-grid">'
        )
        for idx, item in enumerate(filtered, 1):
            out.append(_candidate_card(idx, item, is_held(item), base))
        if not filtered:
            out.append("<p>선택한 필터에 해당하는 시선 괴리 종목이 없습니다.</p>")
        out.append("</div>")
    out.append("</section>")

    # Section 4: Interactive 1-Stock Bespoke Playbook Builder
    out.append(_builder_section(base, csrf, query, saved_plans))
    out.append("</main></body></html>")
    return "".join(out).encode()
