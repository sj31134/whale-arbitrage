"""Authenticated Contrarian Variant-Perception & 12-Month Catalyst 1-Stock Concentrated Workbench."""

from datetime import datetime, timedelta
from html import escape
from urllib.parse import urlencode

from agents import intelligence as intel
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


def _research_prefill(base, *, name, symbol, ccy, entry, floor, target, bull, url, catalyst, kill_switch, months=9):
    fmt = (lambda v: str(round(float(v)))) if ccy == "KRW" else (lambda v: f"{float(v):.2f}")
    due_day = (datetime.now(intel.KST).date() + timedelta(days=min(365, max(90, int(months) * 30)))).isoformat()
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
        due=due_day,
    )
    return e(base + "/research?" + urlencode(params) + "#create")


def _cot_guardrail_section():
    rows = "".join(
        f'<tr><td><code>{e(r["code"])}</code><br><b>{e(r["bias_name"])}</b></td>'
        f'<td>{e(r["cot_trace"])}</td>'
        f'<td>{e(r["why_fatal"])}</td>'
        f'<td><span class="badge-pass">코드 불변식 잠금</span> <b>{e(r["hard_guardrail"])}</b></td></tr>'
        for r in contrarian.AGENT_COT_POSTMORTEM
    )
    return (
        '<details><summary>에이전트 Chain-of-Thought(사고과정) 오류 복기 &amp; 3중 재발 방지 코드 하네스</summary>'
        '<p>이전 버전에서 왜 5~8% 분산 비중·기성 텐베거 재활용·3~5년 장기 홀딩 문구가 잘못 생성되었는지 에이전트의 실제 추론 로그(CoT)를 감사하여, '
        '동일 오류가 다시는 발생하지 않도록 <b>런타임 불변식(Invariant Assertion)</b>으로 영구 잠갔습니다.</p>'
        '<div class="comparison"><table><thead><tr>'
        '<th>CoT 오류 코드 · 인지 편향</th><th>이전 에이전트 CoT 추론 과정 원인</th><th>실전 투자에 미친 악영향</th><th>영구 재발 방지 코드 하네스</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div></details>'
    )


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
            f'<span class="badge-pass">집중 {e(a["target_weight_range"])} · 호흡 {e(a["horizon"])}</span></div>'
            f'<h3>{e(a["master"])}</h3>'
            f'<p><small><b>실증 트랙레코드:</b> {e(a["track_record"])}</small></p>'
            f'<div class="era-lesson">'
            f'<b>핵심 철학:</b> {e(a["core_quote"])}<br>'
            f'<b>① 대중의 시선 착시:</b> {e(a["crowd_blindspot"])}<br>'
            f'<b>② 12개월 내 승부 공식:</b> {e(a["edge_formula"])}<br>'
            f'<b>③ 초집중·시간손절 규칙 ({e(a["horizon"])}):</b> {e(a["execution_rule"])} · 최소 손익배수 <b>{a["min_asymmetry"]:.1f}배+</b>'
            f'</div><small>{srcs}</small></article>'
        )

    paper_rows = "".join(
        f'<tr><td><b>{e(p["title"])}</b><br><small>{e(p["authors"])}</small></td>'
        f'<td>{e(p["finding"])}</td>'
        f'<td><a href="{e(p["url"])}" target="_blank" rel="noreferrer noopener">원전 확인 ↗</a></td></tr>'
        for p in contrarian.ACADEMIC_RESEARCH
    )
    return (
        '<section><h2>1. 조사·이론 · Half-Kelly(25~50% × 2종목 압축) · 3M/6M 2단계 Time-Stop · Piotroski 6대 대가 &amp; 학술 원전</h2>'
        '<p>선행 재무·계량 논문 12편 실증 결과, <b>① 무작위 1종목 보유는 73% 확률로 국채에 패배(Bessembinder 2018)하며 Full Kelly(75%)는 추정오차 시 타격이 10~20배 치명적(MacLean·Thorp·Ziemba)</b>이고, '
        '<b>② Half-Kelly(k=0.5)는 성장률 75%를 보존하면서 변동성을 50% 줄입니다.</b> 따라서 이 메뉴는 <b>Piotroski 기대오차(가치함정 57% 차단)와 12개월 확정 촉매가 검증된 최선호 2축(각 ≤50%)만 압축 배팅</b>하며, '
        '<b>3개월(1분기) 1차 숫자 점검(역주행 시 즉시 컷) + 6개월(2개 분기) 본 Time-Stop(Frazzini·PEAD 3분기 표류 반영)</b>으로 고속 복리 회전합니다.</p>'
        f'<div class="era-grid">{"".join(cards)}</div>'
        '<details open><summary>선행 학술 논문 실증 · 왜 ‘Half-Kelly 2종목(≤50%) + 3M/6M Time-Stop + Piotroski 기대오차’인가? (핵심 4군 · 12편)</summary>'
        '<div class="comparison"><table><thead><tr><th>논문 · 실증 원전</th><th>핵심 계량 근거 (성장 75%·분산 -50% / 가치함정 57% 차단 / PEAD 3개 분기)</th><th>출처</th></tr></thead>'
        f'<tbody>{paper_rows}</tbody></table></div></details>'
        + _cot_guardrail_section()
        + "</section>"
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
        f'<td><small><b>당시 대중 시선:</b> {e(c["crowd_then"])}<br><b>1년 내 승부 핵심 교훈:</b> {e(c["variant_edge"])}</small></td></tr>'
        for c in vm["cases"]
    )
    return (
        '<details open><summary>2. 전략·검증 · ‘기성 텐베거 뒷북’과 ‘촉매 없는 만년 저평가 시간함정(Time Trap)’ 동시 배제 원칙</summary>'
        f'<p>{e(vm["summary"])}</p>'
        '<div class="comparison"><table><thead><tr><th>비교 축</th><th>기존 다수결·추세 전략 (/discover)</th><th>12개월 촉매 · 미개화 1종목 초집중 전략 (/contrarian)</th></tr></thead>'
        f'<tbody>{comp_rows}</tbody></table></div>'
        '<h3>실시간 레이더에서 영구 제외된 2대 기피군 (기성 텐베거 &amp; 무촉매 만년 저PBR 시간함정)</h3>'
        '<div class="comparison"><table><thead><tr><th>제외 유형 · 종목 예시</th><th>상태</th><th>1년 승부 레이더에서 제외한 이유</th></tr></thead>'
        f'<tbody>{grad_rows}</tbody></table></div>'
        '<h3>역사적 ‘첫 12개월 폭발 구간’ 해부 vs 시간함정 반증</h3>'
        '<div class="comparison"><table><thead><tr><th>사례</th><th>1년 내 결과</th><th>진입 시점 촉매 → 12개월 성과</th><th>신규 종목 발굴에 적용할 기준</th></tr></thead>'
        f'<tbody>{case_rows}</tbody></table></div></details>'
    )


def _gap_bars(scores):
    meta = (
        ("essence", "본질 해자·독점 병목 (함정방어)", 35),
        ("gap", "미개화 낙폭 + 12개월 촉매 임박도", 35),
        ("asymmetry", "1년 내 상방/하방 비대칭성", 30),
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
        shield_badge = '<span class="badge-warn">기성 급등주 제외 (5년저점 &gt;3.6배)</span>'
    elif overheated:
        shield_badge = '<span class="badge-warn">단기 과열 구간 (조정 대기)</span>'
    elif item["trap_shield_ok"]:
        shield_badge = '<span class="badge-pass">1년 내 촉매 확정 · 초집중 적격</span>'
    else:
        shield_badge = '<span class="badge-muted">촉매·괴리 관찰 후보</span>'
    held_badge = ' <span class="badge-warn">내 보유 중</span>' if is_held else ""
    t1, t2, t3 = item["tranches"]
    sz = item.get("sizing") or contrarian.compute_position_sizing(
        upside_pct=item["upside_pct"],
        downside_pct=item["downside_pct"],
        piotroski_3=item.get("piotroski_3", 2),
        blocked=overheated or ex_tb,
    )
    solv_lbl = item.get("solvency_label", contrarian.SOLVENCY_TIERS["backlog_float"]["label"])
    mult5 = item.get("mult_5y_low", 1.5)
    dd5y = item.get("dd5y", item["dd52"])
    cat_m = item.get("catalyst_months", 9)
    p3 = int(item.get("piotroski_3", 2))
    p3_badge = (
        f'<span class="badge-pass">Piotroski {p3}/3 · 기대오차 우위</span>'
        if p3 >= 3
        else (
            f'<span class="badge-warn">Piotroski {p3}/3 · 3개월 확인 필수</span>'
            if p3 == 2
            else '<span class="badge-warn">Piotroski 1/3 · 가치함정 차단</span>'
        )
    )
    gtier = item.get("gov_tier", "G1")
    gbadge_cls = "badge-pass" if gtier == "G0" else ("badge-info" if gtier == "G1" else "badge-warn")
    gov_badge = f'<span class="{gbadge_cls}">{e(gtier)} · {"청정(50%)" if gtier == "G0" else ("주의(≤35%)" if gtier == "G1" else "고위험(≤25%캡)")}</span>'
    gnote = item.get("gov_note", "5대 비재무 리스크 점검 대상")
    cat_txt = item.get("catalyst_12m", "")
    tstop_txt = item.get("time_stop", "")
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
        catalyst=f"[{cat_m}개월 내 촉매 · Piotroski {p3}/3 · {gtier}] {cat_txt}",
        kill_switch=f"[Time-Stop] {tstop_txt} / [거버넌스·본질훼손] {item['kill_switch']}",
        months=cat_m,
    )
    builder_params = urlencode(dict(
        pb_market=item["market"],
        pb_symbol=item["symbol"],
        pb_name=item["name"],
        pb_arch=item["archetype"],
        pb_solvency=item.get("solvency_tier", "backlog_float"),
        pb_gov=gtier,
        pb_fscore=str(p3),
        pb_entry=str(item["price"]),
        pb_floor=str(item["floor_price"]),
        pb_target=str(item["target_price"]),
        pb_horizon=f"{max(3, cat_m - 3)}~{cat_m}개월",
        pb_catalyst=cat_txt[:240],
        pb_tstop=tstop_txt[:200],
        pb_crowd=item["crowd_fear"][:220],
        pb_insight=item["moat_essence"][:240],
        pb_kill=item["kill_switch"][:200],
        pb_url=item["source_url"],
    ))
    builder_href = e(base + "/contrarian?" + builder_params + "#playbook-builder")
    tranche_line = (
        f'<b>⑥ 과열·함정·기성급등 브레이크:</b> 지금 추격 금지 · 재검토/조정선({_fmt_px(t2, ccy)}) 대기'
        if (overheated or ex_tb or p3 < 2)
        else f'<b>⑥ Half-Kelly · {e(gtier)} 상한 매집 ({e(item["horizon"])}):</b> '
        f'상한 적용 배정 비중 <b>{sz["recommended_pct"]:.0f}%</b> (Half-Kelly 수식 {sz.get("kelly_half_pct", 0):.1f}%) 3회 투입 — '
        f'1차 {_fmt_px(t1, ccy)}(35%) &gt; 2차 투매 {_fmt_px(t2, ccy)}(40%) &gt; 3차 바닥 {_fmt_px(t3, ccy)}(25%)'
    )
    return (
        f'<article class="era-card">'
        f'<div class="spread"><div><span class="badge-info">#{rank} · {e(item["market"])}:{e(item["venue"])} · {cat_m}개월 내 승부</span> '
        f'{shield_badge} {p3_badge} {gov_badge}{held_badge}</div>'
        f'<strong>괴리·촉매 총점 {item["total"]:.1f} / 100</strong></div>'
        f'<h3>{e(item["name"])} <small>({e(item["symbol"])} · {e(item["archetype_badge"])})</small></h3>'
        f'<p><b>현재가 {_fmt_px(item["price"], ccy)}</b> '
        f'<small>(<b>5년저점 대비 {mult5:.2f}배 미개화</b> · 52주고점 {item["dd52"]:+.1f}% · 5년고점 {dd5y:+.1f}% · RSI {item["rsi"]:.0f})</small><br>'
        f'하방 콘크리트 바닥 <b>{_fmt_px(item["floor_price"], ccy)}</b>(-{item["downside_pct"]:.1f}%) vs '
        f'<b>12개월 내 목표가 {_fmt_px(item["target_price"], ccy)}</b>(+{item["upside_pct"]:.1f}%) · '
        f'강세 오버슈팅 <b>{_fmt_px(item["bull_price"], ccy)}</b> → '
        f'<b>비대칭 손익배수 {item["asymmetry"]:.2f}배</b> · 안전마진 <b>{item["margin_pct"]:.1f}%</b><br>'
        f'<span class="badge-pass">권장 비중: <b>{e(sz["grade_label"])}</b></span> '
        f'<small>(Half-Kelly {sz.get("kelly_half_pct", 0):.1f}% · 5대리스크 상한 {sz.get("cap_pct", 50):.0f}%)</small></p>'
        + _gap_bars(item["scores"])
        + '<div class="era-lesson">'
        f'<b>★ [필수] 향후 {cat_m}개월 내 강제 재평가 촉매:</b> {e(cat_txt)}<br>'
        f'<b>① 다수의 현재 편견·공포:</b> {e(item["crowd_fear"])}<br>'
        f'<b>② 대중이 놓친 독점 본질:</b> {e(item["moat_essence"])}<br>'
        f'<b>③ 무차입 집중 생존력:</b> {e(solv_lbl)}<br>'
        f'<b>④ 5대 비재무 리스크(오너·승계·정부·산업·글로벌):</b> [{e(gtier)}] {e(gnote)}<br>'
        f'<b>⑤ 시간손절(Time-Stop · 자금 묶임 방지):</b> {e(tstop_txt)}<br>'
        f'{tranche_line}<br>'
        f'<b>⑦ 본질 훼손 즉시 철회(Kill-Switch):</b> {e(item["kill_switch"])}'
        '</div>'
        f'<div class="spread"><a href="{e(item["source_url"])}" target="_blank" rel="noreferrer noopener">원문 시세·공시 확인 ↗</a>'
        f'<div><a class="chip" href="{builder_href}">1년 승부 집중계약서 설계 ↓</a> '
        f'<a class="chip" href="{prefill}">가설 연구장(만기 ≤1년) 등록 →</a></div></div></article>'
    )


def _builder_section(base, csrf, query, saved):
    q = query or {}
    open_attr = " open" if (q.get("pb_symbol") or q.get("done") == "saved" or not saved) else ""
    arch_opts = "".join(
        f'<option value="{e(k)}"{" selected" if q.get("pb_arch") == k else ""}>{e(v["badge"])} ({e(v["horizon"])} · 집중 {e(v["target_weight_range"])})</option>'
        for k, v in contrarian.ARCHETYPES.items()
    )
    def_solv = q.get("pb_solvency", "net_cash")
    solv_opts = "".join(
        f'<option value="{e(k)}"{" selected" if def_solv == k else ""}>{e(v["label"])}</option>'
        for k, v in contrarian.SOLVENCY_TIERS.items()
    )
    def_gov = str(q.get("pb_gov", "G1"))
    gov_opts = "".join(
        f'<option value="{k}"{" selected" if def_gov == k else ""}>{e(v["label"])}</option>'
        for k, v in contrarian.GOVERNANCE_TIERS.items()
    )
    def_fscore = str(q.get("pb_fscore", "3"))
    fscore_opts = "".join(
        f'<option value="{v}"{" selected" if def_fscore == v else ""}>{lbl}</option>'
        for v, lbl in (
            ("3", "3/3점 · 수익성·현금·백로그 동시 개선 (Piotroski 기대오차 최고등급)"),
            ("2", "2/3점 · 마진/수주 과도기 (3개월 1차 숫자 반등 확인 조건)"),
            ("1", "1/3점 · 턴어라운드 초기 (신규 진입 보류 권장)"),
        )
    )
    mkt_kr_sel = " selected" if q.get("pb_market", "KR") == "KR" else ""
    mkt_us_sel = " selected" if q.get("pb_market") == "US" else ""

    saved_cards = []
    for p in saved:
        ccy = p["currency"]
        t1, t2, t3 = p["tranches"]
        solv_key = p.get("solvency", "backlog_float")
        p3_val = int(p.get("piotroski_3", 2))
        gtier_p = p.get("gov_tier", "G1")
        gnote_p = p.get("gov_note", contrarian.GOVERNANCE_AUDIT.get(p["symbol"], ("G1", "5대 비재무 리스크 점검 대상"))[1])
        solv_lbl = p.get("solvency_label", contrarian.SOLVENCY_TIERS.get(solv_key, contrarian.SOLVENCY_TIERS["backlog_float"])["label"])
        sz = p.get("sizing") or contrarian.compute_position_sizing(
            upside_pct=p["upside_pct"],
            downside_pct=p["downside_pct"],
            piotroski_3=p3_val,
            blocked=(solv_key == "distressed_block"),
        )
        if solv_key == "distressed_block":
            status_badge = '<span class="badge-warn">집중 부적격 (시간함정·희석 위험 · 0% 기각)</span>'
        elif p["passes"]:
            status_badge = f'<span class="badge-pass">Half-Kelly 2축 적격 · {e(gtier_p)} 통과</span>'
        else:
            status_badge = '<span class="badge-warn">기대오차/비대칭 우위 부족 · 추가 할인 대기</span>'
        grade_lbl = sz.get("grade_label") or f"{sz['recommended_pct']:.0f}%"
        cat_line = p.get("catalyst_12m", p["variant_insight"])
        tstop_line = p.get("time_stop", "3M 1차 점검(역주행 즉시 컷) / 6M 본 Time-Stop(무반응 시 전량 교체)")
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
            catalyst=f"[{p['horizon']} 촉매 · Piotroski {p3_val}/3 · {gtier_p}] {cat_line}",
            kill_switch=f"[Time-Stop] {tstop_line} / {p['kill_switch']}",
            months=p.get("horizon_months", 9),
        )
        saved_cards.append(
            f'<article class="investment-report">'
            f'<div class="spread"><h3>{e(p["name"])} ({e(p["market"])}:{e(p["symbol"])}) · <small>{e(p["archetype_badge"])}</small></h3>'
            f'{status_badge}</div>'
            f'<p><b>진입 기준가 {_fmt_px(p["entry"], ccy)}</b> · 하방 바닥 <b>{_fmt_px(p["floor"], ccy)}</b>(-{p["downside_pct"]:.1f}%) · '
            f'<b>12개월 내 목표가 {_fmt_px(p["target"], ccy)}</b>(+{p["upside_pct"]:.1f}%) → '
            f'<b>비대칭 배수 {p["asymmetry"]:.2f}배</b> · 안전마진 <b>{p["margin_pct"]:.1f}%</b> · 승부 기한 <b>{e(p["horizon"])}</b> · <b>Piotroski {p3_val}/3</b><br>'
            f'<span class="badge-pass">권장 비중: <b>{e(grade_lbl)}</b></span> '
            f'<small>(Half-Kelly {sz.get("kelly_half_pct", 0):.1f}% · 상한 {sz.get("cap_pct", 50):.0f}% · 재무생존: {e(solv_lbl)})</small></p>'
            f'<p><b>내림차순 3단 집중매집표:</b> 1차 진입(35%) <b>{_fmt_px(t1, ccy)}</b> &gt; 2차 군중투매(40%) <b>{_fmt_px(t2, ccy)}</b> &gt; 3차 바닥완성(25%) <b>{_fmt_px(t3, ccy)}</b></p>'
            f'<p><b>★ 12개월 내 확정 촉매:</b> {e(cat_line)}<br>'
            f'<b>5대 비재무 리스크([{e(gtier_p)}]):</b> {e(gnote_p)}<br>'
            f'<b>시간손절(Time-Stop):</b> {e(tstop_line)}<br>'
            f'<b>대중의 오해:</b> {e(p["crowd_view"])} / <b>독점 인사이트:</b> {e(p["variant_insight"])}<br>'
            f'<b>본질 훼손 철회 조건(Kill-Switch):</b> {e(p["kill_switch"])}</p>'
            f'<div class="spread"><small>설계 시각 {e(p["created"][:16].replace("T", " "))} · {chat_page.source_link(p["url"])}</small>'
            f'<a class="chip" href="{prefill}">이 1년 승부안 그대로 가설 연구장(/research) 등록 →</a></div></article>'
        )

    return (
        f'<section id="playbook-builder"><h2>4. Half-Kelly 2축 압축(≤50%) · 12개월 승부 계약서 설계기</h2>'
        '<p><b>13개월 초과 장기보유·5% 분산·단일 50% 초과 과베팅은 코드에서 모두 차단됩니다.</b> '
        'Piotroski 기대오차(2점 이상)와 12개월 확정 촉매, 그리고 <b>3개월 1차 숫자 점검 + 6개월 본 Time-Stop</b>이 결합된 최선호 2종목(각 ≤50%)만 설계하세요.</p>'
        f'<details{open_attr}><summary>1년 내 승부 · Half-Kelly 2축 압축 계약서 작성·검증하기</summary>'
        f'<form class="research-form" method="post" action="{e(base)}/desk/manager/contrarian-plan">'
        f'<input type="hidden" name="csrf" value="{e(csrf)}">'
        f'<label>시장<select name="market"><option value="KR"{mkt_kr_sel}>한국 (KRW)</option><option value="US"{mkt_us_sel}>미국 (USD)</option></select></label>'
        f'<label>종목코드·티커 (미개화·1년 촉매 후보)<input name="symbol" required maxlength="12" value="{e(q.get("pb_symbol", ""))}" placeholder="예: 058470, 240810, ONTO, MOH"></label>'
        f'<label>종목명<input name="name" required maxlength="80" value="{e(q.get("pb_name", ""))}" placeholder="예: 리노공업, 원익IPS, Onto Innovation"></label>'
        f'<label>적용할 1년 승부 대가 아키타입 (6종)<select name="archetype">{arch_opts}</select></label>'
        f'<label>무차입 Half-Kelly 재무생존 등급<select name="solvency">{solv_opts}</select></label>'
        f'<label>5대 비재무 리스크(오너·승계·정부·산업·글로벌)<select name="gov_tier">{gov_opts}</select></label>'
        f'<label>Piotroski 기대오차 관문 (가치함정 57% 차단)<select name="piotroski_3">{fscore_opts}</select></label>'
        f'<label>현재 진입 기준가격<input name="entry" type="number" min="0" step="any" required value="{e(q.get("pb_entry", ""))}"></label>'
        f'<label>하방 콘크리트 바닥가 (순현금·청산가치·수주 근거)<input name="floor" type="number" min="0" step="any" required value="{e(q.get("pb_floor", ""))}"></label>'
        f'<label>12개월 이내 복원 목표가치<input name="target" type="number" min="0" step="any" required value="{e(q.get("pb_target", ""))}"></label>'
        f'<label>내 인사이트 적중 확신도 (%, 기본 60%)<input name="win_prob" type="number" min="25" max="85" step="any" value="{e(q.get("pb_prob", "60"))}"></label>'
        f'<label>목표 승부 기한 (최대 12개월 이내만 허용 · 13개월↑ 입력 차단)<input name="horizon" required maxlength="40" value="{e(q.get("pb_horizon", "6~12개월"))}" placeholder="예: 6~9개월, 6~12개월"></label>'
        f'<label>★ [필수] 향후 12개월 내 주가를 깨울 확정 촉매·일정 (Dated Catalyst)<textarea name="catalyst_12m" rows="2" required maxlength="320" placeholder="예: 4Q 이연물량 인식 / 부산 EDC 신공장 가동">{e(q.get("pb_catalyst", ""))}</textarea></label>'
        f'<label>★ [필수] 2단계 시간손절 (3M 숫자 점검 + 6M 본 Time-Stop)<input name="time_stop" required maxlength="260" value="{e(q.get("pb_tstop", "3M 1차 점검: 영업익·수주 방향 역주행 시 조기 철수 / 6M 본 Time-Stop: 미확인 시 본전이어도 전량 교체"))}"></label>'
        f'<label>① 지금 대중이 착각하거나 공포에 빠진 이유<textarea name="crowd_view" rows="2" required maxlength="300" placeholder="예: 일회성 재고조정·합병비용을 구조적 쇠퇴로 오인해 반토막 투매">{e(q.get("pb_crowd", ""))}</textarea></label>'
        f'<label>② 대중이 놓친 독점 본질·병목 구조<textarea name="variant_insight" rows="2" required maxlength="400" placeholder="예: 영업이익률 50% 소모품 반복 매출 해자 및 무차입 순현금">{e(q.get("pb_insight", ""))}</textarea></label>'
        f'<label>③ 즉시 0%로 철수할 본질 훼손 조건 (Kill-Switch)<textarea name="kill_switch" rows="2" required maxlength="300" placeholder="예: 인허가 거절, 핵심 수주 해지, 주주배정 유상증자">{e(q.get("pb_kill", ""))}</textarea></label>'
        f'<label>검증 원문 URL (DART·SEC·IR·가격 출처 HTTPS)<input name="url" type="url" required value="{e(q.get("pb_url", ""))}" placeholder="https://dart.fss.or.kr/..."></label>'
        '<button>12개월 이내 초집중 전략 검증 및 저장</button></form></details>'
        '<div id="my-playbooks">'
        + ("".join(saved_cards) if saved_cards else "<p><small>아직 저장한 12개월 승부 초집중 전략이 없습니다. 위 후보 카드를 불러오거나 직접 작성해 보세요.</small></p>")
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
    fast_6m_count = sum(1 for c in filtered if c.get("trap_shield_ok") and c.get("catalyst_months", 12) <= 6)

    out = [
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>역발상 · Half-Kelly 2축 압축 12개월 촉매 전략실 · Whale Tracking</title><style>{css}</style></head><body>"
        "<header><div><strong>Whale Tracking</strong><small>로컬 투자 관리 · 12개월 확정촉매 &amp; Half-Kelly 2축 압축(25~50%) 승부실</small></div></header>",
        chat_page.navigation(base, "contrarian"),
        '<main class="desk-main">',
        '<div class="spread"><div><h1>역발상 · 12개월 촉매 미개화 발굴 &amp; Half-Kelly 2종목 압축 전략실</h1>'
        "<p><b>5~10년 존버, 5%~8% 백화점 분산, 그리고 Full Kelly(75%) 단일 몰빵을 모두 거부합니다.</b> "
        "Piotroski 기대오차(가치함정 57% 차단)와 5년 바닥권(≤3.6배)이 검증된 <b>서로 다른 12개월 확정 촉매 2종목에 Half-Kelly 각 25%~50%를 압축 배팅</b>하고 3M/6M Time-Stop으로 회전합니다.</p></div>"
        f'<form method="post" action="{e(base)}/desk/manager/contrarian-run">'
        f'<input type="hidden" name="csrf" value="{e(csrf)}">'
        "<button>12개월 촉매 · 미개화 괴리 스캔</button></form></div>",
    ]
    if done == "refreshed":
        out.append('<p role="status" class="badge-pass">Half-Kelly(25~50%) · Piotroski 기대오차 · ≤12개월 촉매 불변식 검증을 통과한 후보군을 갱신했습니다.</p>')
    elif done == "saved":
        out.append('<p role="status" class="badge-pass">12개월 승부 · Half-Kelly 2축 압축 계약서를 검증·저장했습니다.</p>')

    out.append(
        '<div class="rebalance-bar"><b>Half-Kelly 2축 압축 &amp; 2단계 Time-Stop 3대 철칙 (선행연구 12편 반영):</b> '
        '① <b>3M 숫자 점검 + 6M 본 Time-Stop:</b> 3개월 차에 선행지표(OPM·수주·통관)가 정반대 역주행이면 즉시 컷하고, 2개 분기(6개월) 내 무반응이면 본전이어도 전량 교체합니다. '
        '② <b>Piotroski 3점 &amp; 미개화 배제:</b> 5년 저점 대비 3.6배 초과 기성주와 마진·현금흐름 악화 가치함정(57%)을 차단합니다. '
        '③ <b>Half-Kelly 2종목 압축(25%~50%):</b> Full Kelly(75%) 추정오차·1종목 왜도 리스크를 막기 위해 성장률 75%를 지키는 Half-Kelly 기반 서로 다른 촉매 2종목(각 ≤50%)에 배정합니다.</div>'
    )

    out.append(_archetype_section())
    out.append(_validation_section())

    # Section 3: 12-Month Catalyst Uncrowded Radar
    out.append('<section id="contrarian-radar"><h2>3. 실시간 ‘3~12개월 내 촉매 임박’ 미개화 발굴 레이더</h2>')
    out.append('<div class="chips"><small>시장:</small>')
    for m_code, m_lbl in (("all", "한·미 12개월 촉매 전체 (20선)"), ("KR", "한국 1년 승부 씨앗 (10선)"), ("US", "미국 1년 승부 씨앗 (10선)")):
        cls = "chip active" if market_filter == m_code else "chip"
        out.append(f'<a class="{cls}" href="{link(m_val=m_code)}">{m_lbl}</a>')
    inc_cls = "chip active" if include_held else "chip"
    out.append(
        f'<a class="{inc_cls}" href="{link(inc=not include_held)}">'
        f'{"내 보유 종목 숨기기" if include_held else "내 보유 종목도 12개월 촉매 점검"}</a></div>'
    )
    out.append('<div class="chips"><small>6대 1년 승부 아키타입:</small>')
    out.append(f'<a class="{"chip active" if arch_filter == "all" else "chip"}" href="{link(a_val="all")}">전체 유형 (6종)</a>')
    for k, v in contrarian.ARCHETYPES.items():
        cls = "chip active" if arch_filter == k else "chip"
        out.append(f'<a class="{cls}" href="{link(a_val=k)}">{e(v["badge"])}</a>')
    out.append("</div>")

    if not all_cands:
        out.append(
            '<div class="rebalance-bar">우측 상단 <b>12개월 촉매 · 미개화 괴리 스캔</b> 버튼을 누르거나 '
            '<code>python3 -m private_accounts contrarian --refresh</code>를 실행하세요.</div>'
        )
    else:
        out.append(
            '<div class="kpi-strip">'
            f'<div class="kpi-box info"><small>최근 스캔 시각</small><strong>{e(doc.get("updated", "")[:16].replace("T", " "))}</strong></div>'
            f'<div class="kpi-box pass"><small>12개월 내 초집중 적격</small><strong>{pass_count}종목</strong></div>'
            f'<div class="kpi-box pass"><small>6개월 이내 임박 촉매</small><strong>{fast_6m_count}종목</strong></div>'
            f'<div class="kpi-box warn"><small>저장된 내 1년 승부안</small><strong>{len(saved_plans)}건</strong></div>'
            '</div><div class="era-grid">'
        )
        for idx, item in enumerate(filtered, 1):
            out.append(_candidate_card(idx, item, is_held(item), base))
        if not filtered:
            out.append("<p>선택한 필터에 해당하는 미개화 12개월 촉매 종목이 없습니다.</p>")
        out.append("</div>")
    out.append("</section>")

    out.append(_builder_section(base, csrf, query, saved_plans))
    out.append("</main></body></html>")
    return "".join(out).encode()
