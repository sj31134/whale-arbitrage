"""Authenticated Contrarian Variant-Perception & High-Conviction 1-Stock Concentrated Strategy Workbench."""

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
            f'<div class="spread"><span class="badge-info">{e(a["badge"])}</span>'
            f'<span class="badge-pass">권장 집중도 {e(a["target_weight_range"])}</span></div>'
            f'<h3>{e(a["master"])}</h3>'
            f'<p><small><b>실증 트랙레코드:</b> {e(a["track_record"])}</small></p>'
            f'<div class="era-lesson">'
            f'<b>핵심 철학:</b> {e(a["core_quote"])}<br>'
            f'<b>① 대중의 시선 착시:</b> {e(a["crowd_blindspot"])}<br>'
            f'<b>② 독점 인사이트 공식:</b> {e(a["edge_formula"])}<br>'
            f'<b>③ 초집중 집행 규칙 ({e(a["horizon"])}):</b> {e(a["execution_rule"])} · 최소 손익배수 <b>{a["min_asymmetry"]:.1f}배+</b>'
            f'</div><small>{srcs}</small></article>'
        )

    paper_rows = "".join(
        f'<tr><td><b>{e(p["title"])}</b><br><small>{e(p["authors"])}</small></td>'
        f'<td>{e(p["finding"])}</td>'
        f'<td><a href="{e(p["url"])}" target="_blank" rel="noreferrer noopener">원전 확인 ↗</a></td></tr>'
        for p in contrarian.ACADEMIC_RESEARCH
    )
    return (
        '<section><h2>1. 조사·이론 · 백화점식 분산을 거부하고 ‘1~3종목 초집중’으로 거부를 일군 6대 대가 &amp; 학술 원전</h2>'
        '<p>기관형 메뉴가 추적오차를 줄이기 위해 5~10%씩 쪼개 담는다면, <b>이 메뉴는 분산투자 프레임을 철저히 배제합니다.</b> '
        '남들이 보지 못하는 시선 괴리(Variant Perception)와 무차입 순현금·독점 병목 하방이 확인되었을 때, '
        '<b>최고 확신 1~3개 종목(Best Ideas)에 집중자본의 30%~75%를 묵직하게 싣는 승부 전략실</b>입니다.</p>'
        f'<div class="era-grid">{"".join(cards)}</div>'
        '<details open><summary>왜 5%~8% 분산 대신 30%~75% 집중인가? · 학술 논문 &amp; 펀드 전수 실증 연구 (4대 원전)</summary>'
        '<div class="comparison"><table><thead><tr><th>논문 · 연구 원전</th><th>핵심 실증 결론 (과잉분산의 함정 vs 최고 확신 1종목의 알파)</th><th>출처</th></tr></thead>'
        f'<tbody>{paper_rows}</tbody></table></div></details></section>'
    )


def _validation_section():
    vm = contrarian.VALIDATION_MATRIX
    comp_rows = "".join(
        f"<tr><td><b>{e(axis)}</b></td><td>{e(maj)}</td><td><b>{e(con)}</b></td></tr>"
        for axis, maj, con in vm["comparison"]
    )
    grad_rows = "".join(
        f"<tr><td><b>{e(nm)}</b></td><td><span class='badge-muted'>{e(mult)}</span></td><td>{e(why)}</td></tr>"
        for nm, mult, why in contrarian.EX_TENBAGGER_GRADUATES
    )
    case_rows = "".join(
        f'<tr><td><b>{e(c["name"])}</b><br><small>{e(c["archetype"])}</small></td>'
        f'<td><span class="{"badge-warn" if "함정" in c["verdict"] else "badge-pass"}">{e(c["verdict"])}</span></td>'
        f'<td>{e(c["trough"])}<br>→ <b>{e(c["peak_or_now"])}</b></td>'
        f'<td><small><b>당시 대중 시선:</b> {e(c["crowd_then"])}<br><b>차세대 발굴에 이식할 초기 DNA:</b> {e(c["variant_edge"])}</small></td></tr>'
        for c in vm["cases"]
    )
    return (
        '<details open><summary>2. 전략·검증 · ‘이미 텐베거 난 종목 뒷북 금지(Anti-Hindsight)’ 원칙 및 초기 씨앗 DNA 추출</summary>'
        f'<p>{e(vm["summary"])}</p>'
        '<div class="comparison"><table><thead><tr><th>비교 축</th><th>기존 다수결·추세 전략 (/discover)</th><th>역발상·미개화 1종목 초집중 전략 (/contrarian)</th></tr></thead>'
        f'<tbody>{comp_rows}</tbody></table></div>'
        '<h3>실시간 레이더에서 영구 제외(졸업)시킨 기성 텐베거·초대형주 목록</h3>'
        '<div class="comparison"><table><thead><tr><th>기성 성공 종목</th><th>누적 상승 배수·시총 한계</th><th>실전 신규 발굴에서 제외한 이유</th></tr></thead>'
        f'<tbody>{grad_rows}</tbody></table></div>'
        '<h3>과거 대박 사례에서 추출한 ‘차세대 텐베거 초기 씨앗 DNA’ vs 가치함정 반증</h3>'
        '<div class="comparison"><table><thead><tr><th>교본 사례</th><th>결과</th><th>초기 미개화 바닥 → 이후 결과</th><th>우리가 지금 새 종목에서 찾아야 할 초기 DNA</th></tr></thead>'
        f'<tbody>{case_rows}</tbody></table></div></details>'
    )


def _gap_bars(scores):
    meta = (
        ("essence", "본질 해자·독점 병목 (함정방어)", 35),
        ("gap", "미개화 바닥·군중 외면 깊이", 35),
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
    ex_tb = item.get("ex_tenbagger", False)
    if ex_tb:
        shield_badge = '<span class="badge-warn">기성 급등주 제외 (5년 저점 대비 과열)</span>'
    elif overheated:
        shield_badge = '<span class="badge-warn">단기 과열 구간 (조정 대기)</span>'
    elif item["trap_shield_ok"]:
        shield_badge = '<span class="badge-pass">미개화 시선괴리 · 초집중 적격</span>'
    else:
        shield_badge = '<span class="badge-muted">괴리 심화 관찰 후보</span>'
    held_badge = ' <span class="badge-warn">내 보유 중</span>' if is_held else ""
    t1, t2, t3 = item["tranches"]
    sz = item.get("sizing") or contrarian.compute_position_sizing(
        upside_pct=item["upside_pct"],
        downside_pct=item["downside_pct"],
        blocked=overheated or ex_tb,
    )
    solv_lbl = item.get("solvency_label", contrarian.SOLVENCY_TIERS["backlog_float"]["label"])
    mult5 = item.get("mult_5y_low", 1.5)
    dd5y = item.get("dd5y", item["dd52"])
    seed_txt = item.get("seed_analogy", "")
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
        catalyst=f"[1종목 초집중·{item['archetype_badge']}] {item['moat_essence']}",
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
        f'<b>④ 과열·기성급등 브레이크 ({e(item["horizon"])}):</b> 지금 추격 금지 · '
        f'2차 조정선({_fmt_px(t2, ccy)})·3차 공포 바닥({_fmt_px(t3, ccy)}) 도달 시에만 재점검'
        if (overheated or ex_tb)
        else f'<b>④ 1종목 초집중 매집 공식 ({e(item["horizon"])}):</b> '
        f'목표 집중비중 <b>{sz["recommended_pct"]:.0f}%</b>를 3회 압축 투입 — '
        f'1차 {_fmt_px(t1, ccy)}(35%) &gt; 2차 투매 {_fmt_px(t2, ccy)}(40%) &gt; 3차 바닥 {_fmt_px(t3, ccy)}(25%)'
    )
    return (
        f'<article class="era-card">'
        f'<div class="spread"><div><span class="badge-info">#{rank} · {e(item["market"])}:{e(item["venue"])} · {e(item["archetype_badge"])}</span> '
        f'{shield_badge}{held_badge}</div>'
        f'<strong>괴리 총점 {item["total"]:.1f} / 100</strong></div>'
        f'<h3>{e(item["name"])} <small>({e(item["symbol"])})</small></h3>'
        f'<p><b>현재가 {_fmt_px(item["price"], ccy)}</b> '
        f'<small>(<b>5년 저점 대비 {mult5:.2f}배 미개화</b> · 52주고점 {item["dd52"]:+.1f}% · 5년고점 {dd5y:+.1f}% · RSI {item["rsi"]:.0f})</small><br>'
        f'하방 청산·순현금 바닥 <b>{_fmt_px(item["floor_price"], ccy)}</b>(-{item["downside_pct"]:.1f}%) vs '
        f'1차 리레이팅 목표 <b>{_fmt_px(item["target_price"], ccy)}</b>(+{item["upside_pct"]:.1f}%) · '
        f'슈퍼사이클 <b>{_fmt_px(item["bull_price"], ccy)}</b> → '
        f'<b>비대칭 손익배수 {item["asymmetry"]:.2f}배</b> · 안전마진 <b>{item["margin_pct"]:.1f}%</b><br>'
        f'<span class="badge-pass">권장 집중 비중: <b>{e(sz["grade_label"])}</b></span> '
        f'<small>(순수 켈리 최적치 {sz["kelly_full_pct"]:.1f}% · {e(sz["portfolio_guide"])})</small></p>'
        + _gap_bars(item["scores"])
        + '<div class="era-lesson">'
        + (f'<b>★ 차세대 씨앗 DNA:</b> {e(seed_txt)}<br>' if seed_txt else "")
        + f'<b>① 다수의 현재 편견·공포:</b> {e(item["crowd_fear"])}<br>'
        f'<b>② 대중이 놓친 독점 본질·변곡점:</b> {e(item["moat_essence"])}<br>'
        f'<b>③ 무차입 집중 생존력:</b> {e(solv_lbl)}<br>'
        f'{tranche_line}<br>'
        f'<b>⑤ 유일한 전량 철회 조건(Kill-Switch):</b> {e(item["kill_switch"])}'
        '</div>'
        f'<div class="spread"><a href="{e(item["source_url"])}" target="_blank" rel="noreferrer noopener">원문 시세·공시 확인 ↗</a>'
        f'<div><a class="chip" href="{builder_href}">이 종목으로 1종목 집중계약서 설계 ↓</a> '
        f'<a class="chip" href="{prefill}">가설 연구장 공식 등록 →</a></div></div></article>'
    )


def _builder_section(base, csrf, query, saved):
    q = query or {}
    open_attr = " open" if (q.get("pb_symbol") or q.get("done") == "saved" or not saved) else ""
    arch_opts = "".join(
        f'<option value="{e(k)}"{" selected" if q.get("pb_arch") == k else ""}>{e(v["badge"])} (권장 집중 {e(v["target_weight_range"])})</option>'
        for k, v in contrarian.ARCHETYPES.items()
    )
    def_solv = q.get("pb_solvency", "net_cash")
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
            status_badge = '<span class="badge-warn">집중 부적격 (차환·희석 위험 · 5% 정찰도 금지, 0% 기각)</span>'
        elif p["passes"]:
            status_badge = '<span class="badge-pass">1종목 초집중 승부 적격 (Best Idea 통과)</span>'
        else:
            status_badge = '<span class="badge-warn">비대칭 우위 부족 · 어중간한 진입 대신 추가 할인 대기</span>'
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
            catalyst=f"[1종목 초집중·{p['archetype_badge']}] {p['variant_insight']}",
            kill_switch=p["kill_switch"],
        )
        grade_lbl = sz.get("grade_label") or f"{sz['recommended_pct']:.0f}%"
        saved_cards.append(
            f'<article class="investment-report">'
            f'<div class="spread"><h3>{e(p["name"])} ({e(p["market"])}:{e(p["symbol"])}) · <small>{e(p["archetype_badge"])}</small></h3>'
            f'{status_badge}</div>'
            f'<p><b>진입 기준가 {_fmt_px(p["entry"], ccy)}</b> · 하방 바닥 <b>{_fmt_px(p["floor"], ccy)}</b>(-{p["downside_pct"]:.1f}%) · '
            f'본질 복원 목표 <b>{_fmt_px(p["target"], ccy)}</b>(+{p["upside_pct"]:.1f}%) → '
            f'<b>비대칭 배수 {p["asymmetry"]:.2f}배</b> · 안전마진 <b>{p["margin_pct"]:.1f}%</b> · 호흡 <b>{e(p["horizon"])}</b><br>'
            f'<span class="badge-pass">권장 집중 비중: <b>{e(grade_lbl)}</b></span> '
            f'<small>(순수 켈리 최적치 {sz.get("kelly_full_pct", 0):.1f}% · 재무생존: {e(solv_lbl)})</small></p>'
            f'<p><b>내림차순 3단 집중매집표:</b> 1차 진입(35%) <b>{_fmt_px(t1, ccy)}</b> &gt; 2차 군중투매(40%) <b>{_fmt_px(t2, ccy)}</b> &gt; 3차 바닥완성(25%) <b>{_fmt_px(t3, ccy)}</b></p>'
            f'<p><b>대중의 오해:</b> {e(p["crowd_view"])}<br>'
            f'<b>나만의 독점 인사이트(빈틈):</b> {e(p["variant_insight"])}<br>'
            f'<b>유일한 전량 철회 조건(Kill-Switch):</b> {e(p["kill_switch"])}</p>'
            f'<div class="spread"><small>설계 시각 {e(p["created"][:16].replace("T", " "))} · {chat_page.source_link(p["url"])}</small>'
            f'<a class="chip" href="{prefill}">이 집중 설계안 그대로 가설 연구장(/research) 등록 →</a></div></article>'
        )

    return (
        f'<section id="playbook-builder"><h2>4. 1종목 1투자 초집중 승부 설계기 (Best Idea 켈리 집중 계약서)</h2>'
        '<p>어설프게 5%씩 여러 종목 찔러보는 습관을 버리고, <b>정말 내 전 재산의 30%~75%를 무차입으로 실을 수 있는 단 하나의 미개화 종목인지</b> '
        '켈리 수학 공식과 재무생존 기준으로 끝장 검증하세요. 확신이 미달하면 소액 매수도 하지 않고 0%로 기각합니다.</p>'
        f'<details{open_attr}><summary>1종목 초집중 비대칭 시나리오 작성·검증하기</summary>'
        f'<form class="research-form" method="post" action="{e(base)}/desk/manager/contrarian-plan">'
        f'<input type="hidden" name="csrf" value="{e(csrf)}">'
        f'<label>시장<select name="market"><option value="KR"{mkt_kr_sel}>한국 (KRW)</option><option value="US"{mkt_us_sel}>미국 (USD)</option></select></label>'
        f'<label>종목코드·티커 (기성 텐베거 아닌 미개화 후보 권장)<input name="symbol" required maxlength="12" value="{e(q.get("pb_symbol", ""))}" placeholder="예: 214150, 058470, ACLS, LULU"></label>'
        f'<label>종목명<input name="name" required maxlength="80" value="{e(q.get("pb_name", ""))}" placeholder="예: 클래시스, 리노공업, Axcelis"></label>'
        f'<label>적용할 집중투자 대가 아키타입 (6종)<select name="archetype">{arch_opts}</select></label>'
        f'<label>무차입 고비중 집중을 버틸 재무생존 등급<select name="solvency">{solv_opts}</select></label>'
        f'<label>현재 진입 기준가격<input name="entry" type="number" min="0" step="any" required value="{e(q.get("pb_entry", ""))}"></label>'
        f'<label>하방 콘크리트 바닥가 (순현금·청산가치·대체원가 근거)<input name="floor" type="number" min="0" step="any" required value="{e(q.get("pb_floor", ""))}"></label>'
        f'<label>본질 복원 목표가치 (시선 괴리 해소 시 1차 리레이팅)<input name="target" type="number" min="0" step="any" required value="{e(q.get("pb_target", ""))}"></label>'
        f'<label>내 독점 인사이트 적중 확신도 (%, 기본 60%)<input name="win_prob" type="number" min="25" max="85" step="any" value="{e(q.get("pb_prob", "60"))}"></label>'
        f'<label>목표 보유 호흡 (Time Horizon)<input name="horizon" required maxlength="40" value="{e(q.get("pb_horizon", "18~36개월"))}"></label>'
        f'<label>① 지금 대중·기관 다수가 착각하거나 혐오에 빠진 이유<textarea name="crowd_view" rows="2" required placeholder="예: 단기 합병 비용·전통 업종 선입견으로 고점 대비 반토막 투매">{e(q.get("pb_crowd", ""))}</textarea></label>'
        f'<label>② 대중이 못 보는 나만의 미개화 독점 병목·수출 변곡점 인사이트<textarea name="variant_insight" rows="2" required placeholder="예: 고마진 반복 소모품 구조 + 미·중 신규 시장 인허가 초입">{e(q.get("pb_insight", ""))}</textarea></label>'
        f'<label>③ 주가 흔들림 대신 이 집중투자를 즉시 0%로 철회할 유일한 본질 훼손 조건<textarea name="kill_switch" rows="2" required placeholder="예: 핵심 소모품 출하 역성장 또는 대규모 주주배정 유상증자">{e(q.get("pb_kill", ""))}</textarea></label>'
        f'<label>검증 원문 URL (DART·SEC·IR·가격 출처 HTTPS)<input name="url" type="url" required value="{e(q.get("pb_url", ""))}" placeholder="https://dart.fss.or.kr/..."></label>'
        '<button>1종목 초집중 전략 검증 및 저장</button></form></details>'
        '<div id="my-playbooks">'
        + ("".join(saved_cards) if saved_cards else "<p><small>아직 저장한 1종목 초집중 전략이 없습니다. 위 미개화 후보 카드를 불러오거나 직접 작성해 보세요.</small></p>")
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
        f"<title>역발상 · 미개화 1종목 초집중 전략실 · Whale Tracking</title><style>{css}</style></head><body>"
        "<header><div><strong>Whale Tracking</strong><small>로컬 투자 관리 · 미개화 시선괴리 발굴 &amp; 1~3종목 초집중(30~75%) 설계</small></div></header>",
        chat_page.navigation(base, "contrarian"),
        '<main class="desk-main">',
        '<div class="spread"><div><h1>역발상 · 미개화 시선괴리 발굴 &amp; 1종목 초집중 전략실</h1>'
        "<p>이미 10~70배 올라 전 국민이 다 아는 기성 텐베거(SK하이닉스·삼양식품·HD현대일렉·NVDA 등) 뒷북 매매를 배제하고, "
        "<b>아직 5년 바닥권(1.1~3.4배)에 숨어 있는 차세대 독점·병목 씨앗을 찾아 무차입 30%~75% 초집중 승부를 설계합니다.</b></p></div>"
        f'<form method="post" action="{e(base)}/desk/manager/contrarian-run">'
        f'<input type="hidden" name="csrf" value="{e(csrf)}">'
        "<button>차세대 미개화 괴리 새로 스캔하기</button></form></div>",
    ]
    if done == "refreshed":
        out.append('<p role="status" class="badge-pass">기성 텐베거 제외 필터(5년 저점 대비 ≤3.6배)와 최신 5개년 낙폭·해자 데이터를 대조해 차세대 미개화 후보를 갱신했습니다.</p>')
    elif done == "saved":
        out.append('<p role="status" class="badge-pass">1종목 초집중 비대칭 전략을 켈리 공식으로 검증·저장했습니다. 아래 설계 카드에서 확인하세요.</p>')

    out.append(
        '<div class="rebalance-bar"><b>이 메뉴의 운용 헌장 (한 자릿수 5%~8% 백화점식 분산 금지!):</b> '
        '5% 비중으로 3배를 맞혀도 계좌는 고작 +10% 늘어날 뿐입니다. 이 메뉴는 기관식 추적오차 방어용 분산 메뉴가 아닙니다. '
        '<b>무차입 현물 100%(신용·레버리지 0%) + 순현금·독점 병목 바닥 확인</b>을 전제로, 집중투자 전용 계좌(승부 시드)의 '
        '<b>30%~75%를 최고 확신 1~3종목(Best Ideas)에만 실어 자본 계급을 바꾸는 대가형 독립 엔진</b>입니다. (확신이 부족한 종목은 5% 정찰도 하지 않고 0%로 패스합니다.)</div>'
    )

    out.append(_archetype_section())
    out.append(_validation_section())

    # Section 3: Next-Inflection Uncrowded Variant-Perception Radar
    out.append('<section id="contrarian-radar"><h2>3. 실시간 ‘차세대 미개화 시선괴리’ 발굴 레이더 (기성 텐베거 전면 제외)</h2>')
    out.append('<div class="chips"><small>시장:</small>')
    for m_code, m_lbl in (("all", "한·미 미개화 전체 (20선)"), ("KR", "한국 차세대 씨앗 (KRX·KOSDAQ)"), ("US", "미국 중형병목·딥밸류 (US)")):
        cls = "chip active" if market_filter == m_code else "chip"
        out.append(f'<a class="{cls}" href="{link(m_val=m_code)}">{m_lbl}</a>')
    inc_cls = "chip active" if include_held else "chip"
    out.append(
        f'<a class="{inc_cls}" href="{link(inc=not include_held)}">'
        f'{"내 보유 종목 숨기기" if include_held else "내 보유 종목도 미개화 기준 점검"}</a></div>'
    )
    out.append('<div class="chips"><small>6대 대가 아키타입 필터:</small>')
    out.append(f'<a class="{"chip active" if arch_filter == "all" else "chip"}" href="{link(a_val="all")}">전체 유형 (6종)</a>')
    for k, v in contrarian.ARCHETYPES.items():
        cls = "chip active" if arch_filter == k else "chip"
        out.append(f'<a class="{cls}" href="{link(a_val=k)}">{e(v["badge"])}</a>')
    out.append("</div>")

    if not all_cands:
        out.append(
            '<div class="rebalance-bar">우측 상단 <b>차세대 미개화 괴리 새로 스캔하기</b> 버튼을 누르거나 '
            '<code>python3 -m private_accounts contrarian --refresh</code>를 실행하면 미개화 후보 레이더가 생성됩니다.</div>'
        )
    else:
        out.append(
            '<div class="kpi-strip">'
            f'<div class="kpi-box info"><small>최근 미개화 스캔 시각</small><strong>{e(doc.get("updated", "")[:16].replace("T", " "))}</strong></div>'
            f'<div class="kpi-box pass"><small>초집중 적격 통과 (30~75%)</small><strong>{pass_count}종목</strong></div>'
            f'<div class="kpi-box info"><small>미개화 추적 후보 (5년저점 ≤3.6x)</small><strong>{len(filtered)}종목</strong></div>'
            f'<div class="kpi-box warn"><small>저장된 내 집중 승부안</small><strong>{len(saved_plans)}건</strong></div>'
            '</div><div class="era-grid">'
        )
        for idx, item in enumerate(filtered, 1):
            out.append(_candidate_card(idx, item, is_held(item), base))
        if not filtered:
            out.append("<p>선택한 필터에 해당하는 미개화 시선 괴리 종목이 없습니다.</p>")
        out.append("</div>")
    out.append("</section>")

    # Section 4: Interactive 1-Stock Bespoke High-Conviction Builder
    out.append(_builder_section(base, csrf, query, saved_plans))
    out.append("</main></body></html>")
    return "".join(out).encode()
