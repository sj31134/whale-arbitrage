"""Local manager queue, feed provenance and prospective investment review."""
from decimal import Decimal
import secrets
from datetime import datetime, timedelta
import re
from html import escape
from urllib.parse import urlencode

from agents import intelligence as intel
from agents.equities.daily_bars import BSTOCKS
from agents.portfolio import CASH_NAMES, normalize, portfolio_accounts
from . import chat_page, live_panel, live_valuation, price_history, reports, research_book as book, store

e = escape


def stamp(value):
    if not value:
        return "기록 없음"
    return value if len(value) == 10 else chat_page.kst_time(value)


def feed_health(package):
    cache = intel.private_json(package, intel.CACHE, {})
    captures = intel.private_json(package, intel.CAPTURE_FILE, {})
    rows, fails, missing = [], 0, 0
    for cat in intel.catalog():
        for source in cat["sources"]:
            if "url" not in source:
                continue
            sid = source["id"]
            hit = cache.get(cat["id"] + "/" + sid, {})
            status = hit.get("status", "미수집")
            fails += int(bool(hit) and status != "수집 완료")
            missing += int(not hit)
            captured = captures.get("dart_recent" if sid == "dart" else sid, {})
            items = hit.get("items", [])
            observed = max((stamp(r["as_of"]) for r in items), default="기록 없음")
            if items and all(intel.outdated(r["as_of"], cat["stale_days"], datetime.now(intel.KST).date())
                             for r in items):
                observed += " · 기준일 경과"
            manual = (f'{stamp(captured["collected"])} · {len(captured["items"])}건'
                      if captured else "없음")
            if sid == "dart" and captured:
                manual += " · 최근공시 목록"
            cells = (source["label"], status, stamp(hit.get("attempt")), stamp(hit.get("collected")),
                     observed, manual)
            rows.append("<tr>" + "".join(f"<td>{e(v)}</td>" for v in cells) + "</tr>")
    return (f"<details><summary>공개 자동 원천 {len(rows)}개 · 최근 시도 실패 {fails} · 미수집 {missing}</summary>"
            '<div class="comparison"><table><thead><tr><th>원천</th><th>최근 시도 상태</th>'
            '<th>시도 시각</th><th>마지막 자동 성공</th><th>자동 자료의 최근 관측</th>'
            '<th>수동 보완 시각·범위</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div></details>")


def _fmt_num(val, ccy=""):
    if val is None:
        return "—"
    n = Decimal(val)
    if ccy == "KRW" or abs(n) >= 100:
        return f"{n:,.0f}"
    return f"{n:,.2f}"


def _kor_unit(val, ccy=""):
    if val is None or ccy != "KRW":
        return ""
    n = abs(Decimal(val))
    if n >= Decimal("100000000"):
        return f" (약 {n / Decimal('100000000'):,.2f}억 원)"
    if n >= Decimal("10000"):
        return f" (약 {n / Decimal('10000'):,.0f}만 원)"
    return ""


def _is_tax_sheltered(alias):
    low = (alias or "").lower()
    return any(tok in low for tok in ("isa", "pension", "irp", "연금", "퇴직", "절세"))


def _holding_prefill_href(base, h):
    ccy = h["ccy"]
    px = float(Decimal(h["price"]))
    fmt = (lambda v: str(round(v))) if ccy == "KRW" else (lambda v: f"{v:.2f}")
    inst = h.get("inst")
    code = inst[1] if inst else h["symbol"]
    src_url = (
        f"https://m.stock.naver.com/domestic/stock/{code}/total"
        if ccy == "KRW"
        else f"https://stockanalysis.com/stocks/{str(code).lower()}/"
    )
    params = dict(
        asset=f"{h['symbol']} ({code})" if code != h["symbol"] else h["symbol"],
        currency=ccy,
        entry=fmt(px),
        bear=fmt(px * 0.90),
        base=fmt(px * 1.26),
        bull=fmt(px * 1.48),
        price_source=src_url,
    )
    return e(base + "/research?" + urlencode(params) + "#create")


def _tech_snapshot(db, key, cur_price=None):
    if db is None or not key:
        return None
    rows, _ = price_history.series(db, key)
    if len(rows) < 20:
        return None
    closes = [float(r["closing"]) for r in rows]
    cur = float(cur_price) if cur_price is not None else closes[-1]
    if cur <= 0:
        return None
    series = closes + ([cur] if cur_price is not None and abs(cur - closes[-1]) > 1e-9 else [])
    ma20 = sum(series[-20:]) / 20
    ma60 = sum(series[-60:]) / 60 if len(series) >= 60 else None
    high60 = max(series[-60:]) if len(series) >= 60 else max(series)
    diffs = [b - a for a, b in zip(series[-15:], series[-14:])] if len(series) >= 15 else []
    rsi = None
    if len(diffs) == 14:
        up = sum(d for d in diffs if d > 0) / 14
        dn = sum(-d for d in diffs if d < 0) / 14
        rsi = 100.0 if dn == 0 else 100.0 - (100.0 / (1.0 + up / dn))
    pct20 = (cur / ma20 - 1) * 100
    pct60 = (cur / ma60 - 1) * 100 if ma60 else None
    dd60 = (cur / high60 - 1) * 100
    if ma60 and cur >= ma20 and cur >= ma60:
        label = "상승 추세 안착 (20·60일선 위)"
    elif cur >= ma20:
        label = f"단기 반등 전환 (20일선 +{pct20:.1f}% 위)"
    elif rsi is not None and rsi <= 33:
        label = f"심한 과매도 (RSI {rsi:.0f} · 반등 대기)"
    elif rsi is not None and rsi <= 50:
        label = f"바닥 반등 시도 (RSI {rsi:.0f} · 20일선 {pct20:+.1f}%)"
    else:
        label = f"추세선 아래 (20일선 {pct20:+.1f}%)"
    return dict(cur=cur, ma20=ma20, ma60=ma60, pct20=pct20, pct60=pct60, dd60=dd60, rsi=rsi, label=label)


def action_cockpit(directory, package, base, quote_book=None, accounts=None):
    """Plain-Korean loss post-mortem, market/technical verdict, and per-holding action table."""
    if package is None and directory is None and accounts is None:
        return ""
    qb = quote_book if quote_book is not None else live_valuation.read(package)
    accs = accounts if accounts is not None else portfolio_accounts(directory, package, include_pnl=True, quote_book=qb)
    if not any(a.get("marks") for a in accs):
        return ""

    # Map registered active hypotheses by normalized name and 6-digit KRX/US symbol
    idea_map = {}
    for row in book.entries(package):
        if row["result"]:
            continue
        a = row["a"]
        m = book.metrics(a)
        info = dict(a=a, m=m)
        idea_map[normalize(a["asset"]).replace(" ", "")] = info
        base_tok = normalize(a["asset"].split("·")[0].split("(")[0]).replace(" ", "")
        if base_tok:
            idea_map[base_tok] = info
        for ex_hit in re.findall(r"(?:NASDAQ|NYSE|AMEX|BINANCE|BINANCE_B|KRX):([0-9A-Z.\-]{1,10})", a["asset"].upper()):
            idea_map[ex_hit] = info
        for par_hit in re.findall(r"\(([0-9A-Z]{1,10})\)", a["asset"].upper()):
            idea_map[par_hit] = info
        for code_hit in re.findall(r"\b([0-9A-Z]{2,8})\b", a["asset"].upper()):
            if code_hit not in {"CLASS", "RWA", "TOKEN", "ETF", "ADR", "INC", "CORP", "USD", "KRW", "NASDAQ", "NYSE", "AMEX", "BINANCE", "KRX"}:
                idea_map.setdefault(code_hit, info)
        url_code = re.search(r"(?:code=|/stock/|symbol=|/krx/)(\d{6})", a["price_source"])
        if url_code:
            idea_map[url_code.group(1)] = info

    ccy_totals = {}
    holdings = []
    with live_valuation.connection(package) as db:
        has_bars = bool(db and db.execute("SELECT 1 FROM sqlite_master WHERE name='price_bar'").fetchone())
        kr_bench = _tech_snapshot(db if has_bars else None, ("KRX", "069500", "KRW"),
                                  (qb.match("kis", "069500", "KRW", ("stock:KR:069500",)) or {}).get("price"))
        us_bench = _tech_snapshot(db if has_bars else None, ("AMEX", "SPY", "USD"),
                                  (qb.match("kis", "SPY", "USD", ("stock:US:SPY",)) or {}).get("price"))
        for acc in accs:
            prov, alias = acc["provider"], acc["account"]
            for m in acc["marks"]:
                ccy = m["currency"]
                val = Decimal(m["value"]) if m["value"] is not None else None
                gain = Decimal(m["gain"]) if m.get("gain") is not None else None
                is_cash = m["symbol"].upper() in CASH_NAMES or m["state"].startswith("통화 잔액")
                bucket = ccy_totals.setdefault(ccy, dict(val=Decimal(0), cash=Decimal(0), net_gain=Decimal(0),
                                                         gross_loss=Decimal(0), losers=[], count=0))
                if val is not None:
                    bucket["val"] += val
                    if is_cash:
                        bucket["cash"] += val
                if is_cash:
                    continue
                bucket["count"] += 1
                if gain is not None:
                    bucket["net_gain"] += gain
                    if gain < 0:
                        bucket["gross_loss"] += -gain
                        bucket["losers"].append((gain, m["symbol"]))
                inst = m.get("instrument")
                hist_key = price_history.local_history_key(db if has_bars else None, prov, m) if has_bars else inst
                tech = _tech_snapshot(db if has_bars else None, hist_key, m.get("market_price") or m.get("price"))
                matched_idea = None
                for k_try in (
                    inst[1].upper() if inst else "",
                    normalize(m["symbol"]).replace(" ", ""),
                    m["symbol"].strip().upper(),
                ):
                    if k_try and k_try in idea_map:
                        matched_idea = idea_map[k_try]
                        break
                qty = Decimal(m["qty"])
                cost_unit = ((val - gain) / qty) if (val is not None and gain is not None and qty > 0) else None
                holdings.append(dict(
                    provider=prov, alias=alias, symbol=m["symbol"], ccy=ccy,
                    price=m["price"], val=val, gain=gain, rate=m.get("rate"),
                    weight=m.get("weight_pct"), breakeven=cost_unit,
                    idea=matched_idea, tech=tech, inst=inst,
                ))

    if not holdings:
        return ""

    # Multi-account & US-stock + Binance-RWA canonical duplicate map
    dup_map = {}
    for h in holdings:
        dkey = (h["ccy"], live_panel._canonical_symbol(h["provider"], h["symbol"]))
        dentry = dup_map.setdefault(dkey, dict(accs=set(), val=Decimal(0), has_rwa=False))
        dentry["accs"].add((h["provider"], h["alias"]))
        if h["provider"] == "binance" and h["symbol"].strip().upper() in BSTOCKS:
            dentry["has_rwa"] = True
        if h["val"] is not None:
            dentry["val"] += h["val"]

    # Build Box 1: Plain-Korean Loss Root-Cause Post-Mortem
    loss_bullets = []
    for ccy, b in sorted(ccy_totals.items()):
        if b["val"] <= 0:
            continue
        cash_pct = (b["cash"] / b["val"] * 100) if b["val"] > 0 else Decimal(0)
        rec_pct = (max(-b["net_gain"], Decimal(0)) / b["val"] * 100) if b["val"] > 0 else Decimal(0)
        top_losers = sorted(b["losers"], key=lambda x: x[0])[:3]
        if top_losers and b["gross_loss"] > 0:
            top_share = sum(-g for g, _ in top_losers) / b["gross_loss"] * 100
            names = ", ".join(e(s) for _, s in top_losers)
            loss_bullets.append(
                f"<li><b>{e(ccy)} 계좌 현황:</b> 순평가손익 <b>{_fmt_num(b['net_gain'], ccy)} {e(ccy)}</b>{_kor_unit(b['net_gain'], ccy)} "
                f"(현재 자산에서 <b>+{rec_pct:.1f}%</b> 수익이 나야 원금 복구) · "
                f"전체 손실의 <b>{top_share:.0f}%</b>가 <b>{names}</b>에서 발생했습니다.</li>"
            )
        else:
            loss_bullets.append(
                f"<li><b>{e(ccy)} 계좌 현황:</b> 보유 {b['count']}개 행 · 현금 비중 <b>{cash_pct:.1f}%</b></li>"
            )
    kr_cash_pct = (ccy_totals["KRW"]["cash"] / ccy_totals["KRW"]["val"] * 100) if ccy_totals.get("KRW", {}).get("val") else Decimal(0)
    total_names = len({(h["ccy"], h["symbol"]) for h in holdings})
    loss_bullets.append(
        f"<li><b>왜 손실이 커졌나 (구조적 원인):</b> ① 현금 방어막 부족(원화 현금 <b>{kr_cash_pct:.1f}%</b> vs 권장 <b>35%</b>)으로 "
        f"시장 급락을 그대로 맞았고, ② <b>{total_names}개 종목</b>으로 자금이 흩어져 있어 폭락 땐 동반 하락하고 반등 땐 약한 종목이 발목을 잡고 있습니다.</li>"
    )
    loss_bullets.append(
        "<li><b>수익 극대화 핵심 원리:</b> 상승 여력이 낮은 종목을 '본전 올 때까지' 붙잡고 있으면 복구가 가장 늦습니다. "
        "<b>반등하는 날 비핵심주를 팔아 현금 총알을 만들고, 실적이 뒷받침되는 1등 주도주 2~3개로 압축</b>해야 가장 빠르고 크게 복구됩니다.</li>"
    )

    # Build Box 2: Whole-Market & Technical Analysis Verdict
    tech_bullets = []
    if kr_bench:
        kr_phase = ("상승 추세 전환 (2단계)" if (kr_bench["ma60"] and kr_bench["cur"] >= kr_bench["ma60"])
                    else "바닥 반등 시도 중 · 아직 추세선 아래 (1단계 방어·압축 구간)")
        tech_bullets.append(
            f"<li><b>한국 시장 차트(KODEX 200 기준):</b> <b>{kr_phase}</b> · "
            f'<abbr title="최근 20거래일 평균 주가(단기 추세선)">20일선</abbr> 대비 <b>{kr_bench["pct20"]:+.1f}%</b>'
            + (f', <abbr title="최근 60거래일 평균 주가(중기 수급선)">60일선</abbr> 대비 <b>{kr_bench["pct60"]:+.1f}%</b>' if kr_bench["pct60"] is not None else "")
            + (f', <abbr title="0~100 단기 과열·침체 지표 (30 이하 과매도, 70 이상 과열)">RSI</abbr> <b>{kr_bench["rsi"]:.0f}</b>' if kr_bench["rsi"] is not None else "")
            + "</li>"
        )
        if kr_bench["pct20"] < 0:
            tech_bullets.append(
                "<li><b>지금 취할 시장 전술 (11/27 장마감 복기 반영):</b> 투매 공포는 진정됐으나 아직 20일·60일 추세선 아래입니다. "
                "① <b>장 초반(09:00~09:30) 흔들기 매도·칼손절은 금지</b>하고, ② 반등장에서도 탄력이 약한 '최우선 현금화 종목'부터 정리하되 "
                "외국인·기관 수급이 오후까지 가속되는 추세일에는 <b>15:10~15:20 마감 동시호가 전후</b>에 매도 및 핵심주 동시교체(Switch)를 실행하세요.</li>"
            )
        else:
            tech_bullets.append(
                "<li><b>지금 취할 시장 전술:</b> 단기 20일 추세선 위로 올라섰습니다. 비핵심주 정리 자금을 15:15 수급 확인 종가 선발진입(40%)과 20일선 눌림(60%)으로 핵심 종목에 실으세요.</li>"
            )
    else:
        tech_bullets.append("<li><b>시장 차트 점검:</b> 지수 이동평균선 확인 전까지는 현금 버퍼 35%와 소수 핵심주 압축 원칙을 우선합니다.</li>")
    if us_bench:
        tech_bullets.append(
            f'<li><b>미국 시장 차트(SPY 기준):</b> <abbr title="최근 20거래일 평균 주가">20일선</abbr> 대비 <b>{us_bench["pct20"]:+.1f}%</b>'
            + (f', <abbr title="0~100 단기 과열·침체 지표">RSI</abbr> <b>{us_bench["rsi"]:.0f}</b>' if us_bench["rsi"] is not None else "")
            + " · 해외·코인 자산도 20일선 안착 확인 전까지는 무리한 물타기보다 핵심주 유지가 유리합니다.</li>"
        )

    # Classify each holding into unmistakable action buckets (Core / Semi-Core Hold / Priority Trim / Watch)
    rows_html = []
    counts = {"core": 0, "semicore": 0, "trim": 0, "watch": 0}
    trim_general_krw = Decimal(0)
    trim_sheltered_krw = Decimal(0)

    def _is_semicore(idea_obj):
        if not idea_obj or idea_obj["m"]["qualifies"]:
            return False
        mi = idea_obj["m"]
        return mi["expected"] >= Decimal("20") and mi["margin"] >= Decimal("15")

    def sort_key(h):
        if h["idea"] and h["idea"]["m"]["qualifies"]:
            tier = 0
        elif _is_semicore(h["idea"]):
            tier = 1
        elif h["idea"] and not h["idea"]["m"]["qualifies"]:
            tier = 2
        elif h["ccy"] == "KRW":
            tier = 3
        else:
            tier = 4
        loss_rank = float(h["gain"]) if h["gain"] is not None else 0.0
        return (tier, loss_rank, h["symbol"])

    for h in sorted(holdings, key=sort_key):
        idea, tech, ccy = h["idea"], h["tech"], h["ccy"]
        sheltered = _is_tax_sheltered(h["alias"])
        sym_up = h["symbol"].strip().upper()
        is_rwa = h["provider"] == "binance" and sym_up in BSTOCKS
        dkey = (ccy, live_panel._canonical_symbol(h["provider"], h["symbol"]))
        dup = dup_map.get(dkey)
        dup_lbl = "본주+RWA 합산" if (dup and dup["has_rwa"]) else "다계좌"
        dup_badge = (
            f'<br><small class="badge-muted">{dup_lbl} {len(dup["accs"])}곳 합산 {_fmt_num(dup["val"], ccy)} {e(ccy)}</small>'
            if dup and len(dup["accs"]) >= 2
            else ""
        )
        rwa_badge = ""
        rwa_tip = ""
        if is_rwa and h.get("price") is not None:
            under_t = "BRK-B" if sym_up[:-1] == "BRKB" else sym_up[:-1]
            uq = qb.match("kis", under_t, "USD", (f"stock:US:{under_t}",))
            if uq and Decimal(uq["price"]) > 0:
                peg = (Decimal(h["price"]) / Decimal(uq["price"]) - 1) * 100
                rwa_badge = f' <span class="badge-info">RWA · 본주대비 {peg:+.2f}%</span>'
                if abs(peg) >= Decimal("2"):
                    rwa_tip = f" <b>(개장 전 RWA 괴리 {peg:+.2f}% · 23:30 본장 개장 전 시장가 추격 금지, 중복 축소 시 본주보다 RWA(왕복 50bp·수탁위험) 우선 정리 유리)</b>"
            else:
                rwa_badge = ' <span class="badge-info">미국주식 RWA 토큰</span>'
        shelter_badge = ' <span class="badge-info">절세계좌 보호</span>' if sheltered else ""
        extra_badges = shelter_badge + rwa_badge
        gross = ccy_totals.get(ccy, {}).get("gross_loss", Decimal(0))
        loss_share = (f" · 손실비중 {(-h['gain'] / gross * 100):.0f}%"
                      if h["gain"] is not None and h["gain"] < 0 and gross > 0 else "")
        if idea and idea["m"]["qualifies"]:
            counts["core"] += 1
            badge = '<span class="badge-pass">1순위 · 핵심 집중·보유</span>' + extra_badges
            m_info, a_info = idea["m"], idea["a"]
            close_slot = "마감 20분 전(정규 05:40 / 단축장 02:40 KST)" if ccy == "USD" else "15:15 종가"
            open_avoid = "개장 첫 30분(23:30~00:00 KST) 호가 왜곡" if ccy == "USD" else "장초반 급등"
            pullback_note = (
                f"20일선({_fmt_num(tech['ma20'], ccy)}) 눌림(60%) 또는 수급 확인 {close_slot} 선발교체(40%)"
                if tech else f"{close_slot} 수급 확인 또는 눌림목"
            )
            dup_rwa_note = (
                " 단, 증권사 미국 본주와 기초자산이 중복된 상태이므로 추가 집중은 수수료·수탁 측면에서 본주 계좌로 일원화하고 RWA 비중 확대를 자제하세요."
                if (is_rwa and dup and len(dup["accs"]) >= 2) else ""
            )
            guide = (
                f"<b>팔지 말고 집중할 대장주.</b> 내재가치({_fmt_num(a_info['base'], ccy)}) 대비 저평가"
                f"(기대수익 <b>{m_info['expected']:+.1f}%</b>, "
                f'<abbr title="내재가치 대비 현재 주가 할인율(20% 이상 권장)">안전마진</abbr> {m_info["margin"]:.0f}%). '
                f"{open_avoid} 추격만 피하고, 비핵심주 정리 자금으로 {pullback_note}로 모아 수익을 극대화하세요."
                + dup_rwa_note + rwa_tip
            )
        elif _is_semicore(idea):
            counts["semicore"] += 1
            badge = '<span class="badge-info">준코어 · 반등 추세 유예</span>' + extra_badges
            m_info, a_info = idea["m"], idea["a"]
            res_note = f"20일선({_fmt_num(tech['ma20'], ccy)}) 저항 구간" if tech else "단기 목표 저항 구간"
            guide = (
                f"<b>성급한 조기 매도 금지(11/27 복기 보정).</b> 기대수익(<b>{m_info['expected']:+.1f}%</b>)은 높으나 "
                f"최근 급락 변동성 할인 때문에 안전마진({m_info['margin']:.1f}% vs 기준 20%)만 소폭 미달한 낙폭과대 탄력주입니다. "
                f"수급 유입 시 강한 반등 탄력이 나오므로 2순위 약세주보다 뒤로 미루고, {res_note} 도달 시에만 일부 현금화·실적 목표가 재산정을 진행하세요."
                + rwa_tip
            )
        elif idea and not idea["m"]["qualifies"]:
            counts["trim"] += 1
            if ccy == "KRW" and h["val"] is not None:
                if sheltered:
                    trim_sheltered_krw += h["val"]
                else:
                    trim_general_krw += h["val"]
            badge = '<span class="badge-warn">2순위 · 최우선 현금화</span>' + extra_badges
            m_info, a_info = idea["m"], idea["a"]
            tax_tip = (
                " <b>(절세계좌 유의: 계좌 밖 인출 시 비과세 한도가 줄어드니 출금 대신 계좌 내 핵심주·지수ETF로 교체하세요.)</b>"
                if sheltered else ""
            )
            timing_rule = (
                "개장 첫 30분(23:30~00:00 KST) 스프레드 확대 구간은 피하되, 장중 반등 구간(00:30~02:50 KST)에 지정가 분할 매도해 달러 현금 버퍼와 미국 1순위 대장주 교체 재원으로 바꾸세요."
                if ccy == "USD"
                else "장 초반(09:00~09:30) 흔들기는 피하되, 반등일 오후장 또는 외인 수급 가속 시 <b>15:10~15:20 마감 동시호가</b>에 우선 매도해 현금 35%와 1순위 대장주 자금으로 바꾸세요."
            )
            guide = (
                f"<b>현금 버퍼 최우선 재원.</b> 기준 내재가치({_fmt_num(a_info['base'], ccy)}) 대비 기대수익({m_info['expected']:+.1f}%)·"
                f"안전마진({m_info['margin']:.1f}%)이 모두 낮고 시장 반등 대비 탄력도 약합니다. "
                + timing_rule + tax_tip + rwa_tip
            )
        elif ccy == "KRW":
            counts["trim"] += 1
            if h["val"] is not None:
                if sheltered:
                    trim_sheltered_krw += h["val"]
                else:
                    trim_general_krw += h["val"]
            w_dec = Decimal(h["weight"]) if h.get("weight") is not None else Decimal(0)
            prefill_btn = (
                f' <a class="chip" href="{_holding_prefill_href(base, h)}">원클릭 가설 검증 채우기 →</a>'
                if h.get("price") is not None
                else ""
            )
            if w_dec >= Decimal(10):
                badge = '<span class="badge-warn">가설 미등록 주요 보유주 · 검증 시급</span>' + shelter_badge
                guide = (
                    f"계좌 비중 <b>{w_dec:.1f}%</b>를 차지하는 주요 보유주이나 아직 3관문 내재가치 시나리오가 등록되지 않았습니다. "
                    "막연한 보유나 감정적 손절 대신 목표가·철회 조건부터 검증한 뒤 핵심 유지 또는 반등 축소를 결정하세요."
                    + prefill_btn
                )
            else:
                badge = '<span class="badge-warn">비중 점검 · 반등 시 축소 검토</span>' + shelter_badge
                ma_txt = f"20일선({_fmt_num(tech['ma20'], ccy)}) 부근 반등 시 " if tech else "장중 반등 시 "
                tax_tip = " 절세계좌이므로 출금 대신 계좌 내 핵심주 교체가 유리합니다." if sheltered else ""
                guide = (
                    f"핵심 3관문 미확정 소액·분산 종목입니다. 계좌 압축을 위해 {ma_txt}정리하여 "
                    "현금 버퍼 및 1순위 핵심주로 일원화하는 것이 복구에 유리합니다."
                    + tax_tip + prefill_btn
                )
        else:
            counts["watch"] += 1
            badge = '<span class="badge-info">해외·코인 · 추세 확인</span>' + shelter_badge
            us_prefill = (
                f' <a class="chip" href="{_holding_prefill_href(base, h)}">USD 가설 검증 채우기 →</a>'
                if (ccy == "USD" and h["provider"] not in store.CRYPTO and h.get("price") is not None)
                else ""
            )
            if tech:
                guide = (
                    f"{e(tech['label'])}. 20일 평균선({_fmt_num(tech['ma20'], ccy)}) 회복 전까지 성급한 물타기를 멈추고, "
                    "시초 30분(23:30~00:00 KST) 변동성 진정 및 20일선 안착 확인 후 비중을 결정하세요."
                    + us_prefill
                )
            else:
                guide = "변동성이 큰 해외·디지털 자산입니다. 추가 물타기 없이 현 비중 내에서 추세 회복을 먼저 확인하세요." + us_prefill

        cur_vs_be = f"현재 {_fmt_num(h['price'], ccy)}<br><small>본전 {_fmt_num(h['breakeven'], ccy)}</small>"
        pnl_txt = (f"<b>{_fmt_num(h['gain'], ccy)}</b> {e(ccy)}{_kor_unit(h['gain'], ccy)}<br>"
                   f"<small>{h['rate']:+.1f}%{loss_share}</small>"
                   if h["gain"] is not None and h["rate"] is not None
                   else f"{_fmt_num(h['gain'], ccy)} {e(ccy)}")
        tech_txt = (f"{e(tech['label'])}<br><small>60일 고점 대비 {tech['dd60']:+.1f}%</small>"
                    if tech else "<small>일봉 축적 중 · 현재가 연결됨</small>")
        rows_html.append(
            f"<tr><td>{badge}</td>"
            f"<td><b>{e(h['symbol'])}</b><br><small>{e(store.PROVIDERS[h['provider']])} · {e(h['alias'])}</small>{dup_badge}</td>"
            f"<td class='num'>{cur_vs_be}</td>"
            f"<td class='num'>{pnl_txt}</td>"
            f"<td>{tech_txt}</td>"
            f"<td class='cockpit-why'>{guide}</td></tr>"
        )

    rebalance_html = ""
    kr_b = ccy_totals.get("KRW")
    if kr_b and kr_b["val"] > 0:
        kr_total, kr_cash = kr_b["val"], kr_b["cash"]
        kr_target = kr_total * Decimal("0.35")
        kr_deficit = max(Decimal(0), kr_target - kr_cash)
        deployable = max(Decimal(0), kr_cash + trim_general_krw - kr_target)
        if kr_deficit > 0:
            reb_main = (
                f"<div><b>현금 35% 목표 시뮬레이터:</b> 현재 원화 현금 <b>{_fmt_num(kr_cash, 'KRW')}원{_kor_unit(kr_cash, 'KRW')} ({kr_cash_pct:.1f}%)</b> → "
                f"<b>목표 35% 달성까지 +{_fmt_num(kr_deficit, 'KRW')}원{_kor_unit(kr_deficit, 'KRW')} 추가 현금화 필요</b></div>"
                f"<small>일반계좌 축소 후보 정리 시 최대 <b>{_fmt_num(trim_general_krw, 'KRW')}원{_kor_unit(trim_general_krw, 'KRW')}</b> 확보 가능 · "
                f"현금 버퍼 35%를 먼저 채운 뒤 1순위 핵심·신규 대장주 교체 가용액 <b>{_fmt_num(deployable, 'KRW')}원{_kor_unit(deployable, 'KRW')}</b>"
                + (
                    f" · 절세계좌(ISA·연금) 내 조정분 {_fmt_num(trim_sheltered_krw, 'KRW')}원{_kor_unit(trim_sheltered_krw, 'KRW')}은 인출 없이 계좌 내 교체 권장"
                    if trim_sheltered_krw > 0 else ""
                )
                + "</small>"
            )
        else:
            surplus = kr_cash - kr_target
            reb_main = (
                f"<div><b>현금 35% 목표 시뮬레이터:</b> 원화 현금 <b>{_fmt_num(kr_cash, 'KRW')}원{_kor_unit(kr_cash, 'KRW')} ({kr_cash_pct:.1f}%)</b>로 "
                f"방어 버퍼 확보 완료 · 즉시 활용 가능한 초과 현금 <b>{_fmt_num(surplus, 'KRW')}원{_kor_unit(surplus, 'KRW')}</b></div>"
            )
        rebalance_html = f'<div class="rebalance-bar">{reb_main}</div>'

    # US Evening Session Readiness Banner (live 24/7 xStocks lead indicators + USD cash check)
    us_b = ccy_totals.get("USD")
    x_rows = {r["symbol"].upper(): r for r in qb.rows_by_venue.get("KRAKEN_X", ())}
    lead_parts = []
    for x_sym, base_sym, lbl in (("SPYX", "SPY", "S&P500 선행(SPYx)"), ("QQQX", "QQQ", "나스닥100 선행(QQQx)"), ("NVDAX", "NVDA", "엔비디아 선행(NVDAx)")):
        xr = x_rows.get(x_sym)
        br = qb.match("kis", base_sym, "USD", (f"stock:US:{base_sym}",))
        if xr and br and Decimal(br["price"]) > 0:
            xp, bp = Decimal(xr["price"]), Decimal(br["price"])
            gap = (xp / bp - 1) * 100
            lead_parts.append(f"{lbl} <b>${xp:,.2f}</b> ({gap:+.2f}%)")
    if us_b or lead_parts:
        today_kst = datetime.now(intel.KST).date().isoformat()
        session_tag = (
            "오늘 밤 23:30 개장 ~ 익일 03:00 조기폐장 (추수감사절 익일 3.5시간 단축장 · 얇은 호가 주의)"
            if today_kst == "2026-11-27"
            else "정규장 23:30 개장 ~ 익일 06:00 마감 (KST)"
        )
        usd_cash_txt = ""
        if us_b and us_b["val"] > 0:
            u_pct = us_b["cash"] / us_b["val"] * 100
            usd_cash_txt = f" · 내 달러(USD) 현금 <b>${_fmt_num(us_b['cash'], 'USD')} ({u_pct:.1f}%)</b>"
        lead_line = ("24시간 토큰주가 직전 종가 대비 · " + " · ".join(lead_parts)) if lead_parts else "개장 전 선물·반도체(SOXX·NVDA) 호가 점검"
        rebalance_html += (
            '<div class="networth-banner">'
            f'<div><b>저녁 미국장 실전 준비 ({session_tag}):</b> {lead_line}{usd_cash_txt}</div>'
            '<small>① <b>23:30~00:00 시초 갭업 추격·투매 금지</b> → '
            '② <b>00:30~02:00 장중 지지 확인</b> → '
            '③ <b>마감 20분 전</b> 안전마진 미달 약세주 달러 현금화 및 '
            f'<a href="{e(base)}/discover?market=US">미국 S급 대장주</a> 선발교체</small></div>'
        )

    return (
        '<section id="action-cockpit" class="cockpit">'
        '<div class="cockpit-head"><div><h2>한눈에 보는 내 계좌 손실 복기 &amp; 오늘 행동 답안지</h2>'
        '<small>어려운 용어 없이 · ① 왜 손실 났나 → ② 지금 시장 차트가 어떤가 → ③ 얼마를 현금화해 어디에 집중할까</small></div>'
        f'<a class="btn" href="{e(base)}/discover">내 포트폴리오 외 신규 대장주 발굴 보기 →</a></div>'
        + rebalance_html
        + '<div class="cockpit-grid">'
        '<article class="cockpit-box alert"><h3>1. 내 포트폴리오 손실 원인 복기</h3><ul>'
        + "".join(loss_bullets)
        + '</ul></article>'
        '<article class="cockpit-box"><h3>2. 시장 전체 &amp; 기술적 분석 결론</h3><ul>'
        + "".join(tech_bullets)
        + '</ul></article></div>'
        '<div class="kpi-strip">'
        f'<div class="kpi-box pass"><small>1순위 핵심 집중·보유</small><strong>{counts["core"]}개 보유 행</strong></div>'
        f'<div class="kpi-box info"><small>준코어 · 반등 추세 유예</small><strong>{counts["semicore"]}개 보유 행</strong></div>'
        f'<div class="kpi-box warn"><small>2순위 최우선 현금화 대상</small><strong>{counts["trim"]}개 보유 행</strong></div>'
        f'<div class="kpi-box info"><small>추세 확인할 해외·코인 행</small><strong>{counts["watch"]}개 보유 행</strong></div>'
        '</div>'
        '<details open><summary>3. 내 보유 전 종목 행동 지침표 (위에서부터 순서대로 대응하세요)</summary>'
        '<div class="comparison"><table class="cockpit-table"><thead><tr>'
        '<th>지금 할 행동</th><th>종목 · 계좌</th><th>현재가 / 본전단가</th><th>현재 평가손익</th>'
        '<th>기술적 차트 위치</th><th>왜 이렇게 해야 하나 &amp; 구체적 매매 타이밍</th>'
        '</tr></thead><tbody>'
        + "".join(rows_html)
        + '</tbody></table></div><small>직접 자동주문은 보류되어 있으며, 위 지침은 실시간 시세·일봉 기술적 지표·내재가치 시나리오를 결합한 로컬 의사결정 가이드입니다.</small></details>'
        '</section>'
    )


def manager_panel(package, base):
    today = datetime.now(intel.KST).date().isoformat()
    ideas = book.entries(package)
    pending = [row for row in ideas if not row["result"]]
    due = sum(row["due"] <= today for row in pending)
    qualifying = sum(book.metrics(row["a"])["qualifies"] for row in pending)
    return (f'<section><h2>오늘의 투자 검토</h2><p><a href="{e(base)}/research">가설 연구장</a>'
            f' · 평가일 도래 {due}건 · 추적 중 {len(pending)}건 (3관문 집중 후보 {qualifying}건) · 평가 완료 {len(ideas)-len(pending)}건</p>'
            f'<div class="chips"><a class="chip" href="{e(base)}/discover">신규 대장주 발굴 (6대 변수)</a>'
            f'<a class="chip" href="{e(base)}/contrarian">역발상·1종목 비대칭 설계</a>'
            f'<a class="chip" href="{e(base)}/research">1. 시나리오·3관문 점검</a>'
            f'<a class="chip" href="{e(base)}/strategies">2. 4대 위기 백테스트·레짐 규칙</a>'
            f'<a class="chip" href="{e(base)}/quant">3. 종목별 변동성·차트 검증</a>'
            f'<a class="chip" href="{e(base)}/portfolio#stress">보유분 하방 스트레스</a>'
            f'<a class="chip" href="{e(base)}/portfolio#performance">입출금 조정 계좌 성과</a></div>'
            + feed_health(package) + "</section>")


def field(key, label, kind="text", attrs="", val=""):
    v_attr = f' value="{e(val)}"' if val != "" else ""
    return f'<label>{e(label)}<input name="{key}" type="{kind}" required{v_attr} {attrs}></label>'


def price(key, label, val=""):
    return field(key, label, "number", 'min="0" step="any"', val=val)


def form(base, csrf, action, key):
    return (f'<form class="research-form" method="post" action="{e(base)}/desk/manager/{action}">'
            f'<input type="hidden" name="csrf" value="{e(csrf)}">'
            f'<input type="hidden" name="idea" value="{e(key)}">')


def obs_field(val=""):
    return field("observed", "두 가격의 공통 기준시각 (KST)", "datetime-local", 'step="1"', val=val)


def new_form(ledger, base, csrf, query=None, package=None):
    eligible = sorted((r for r in ledger.values() if r["sources"]), key=lambda r: r["as_of"], reverse=True)
    if not eligible:
        return "<p>원문 근거가 있는 분야 보고서를 게시하면 가설을 등록할 수 있습니다.</p>"
    q = query or {}
    ccy = (q.get("currency") or "KRW").strip().upper()[:3]
    qb = live_valuation.read(package) if package is not None else None
    if ccy == "USD":
        def_bench = q.get("benchmark") or "SPDR S&P 500 ETF (SPY)"
        spy_q = qb.match("kis", "SPY", "USD", ("stock:US:SPY",)) if qb else None
        def_bpx = q.get("benchmark_entry") or (str(spy_q["price"]) if spy_q else "")
        def_bsrc = q.get("benchmark_source") or "https://stockanalysis.com/etf/spy/"
        def_fees, def_slip = q.get("fees") or "10", q.get("slip") or "10"
    else:
        def_bench = q.get("benchmark") or "KODEX 200 (069500)"
        k200_q = qb.match("kis", "069500", "KRW", ("stock:KR:069500",)) if qb else None
        def_bpx = q.get("benchmark_entry") or (str(k200_q["price"]) if k200_q else "")
        def_bsrc = q.get("benchmark_source") or "https://m.stock.naver.com/domestic/stock/069500/total"
        def_fees, def_slip = q.get("fees") or "28", q.get("slip") or "12"
    now_kst = datetime.now(intel.KST)
    def_obs = q.get("observed") or now_kst.strftime("%Y-%m-%dT%H:%M:%S")
    def_due = q.get("due") or (now_kst.date() + timedelta(days=180)).isoformat()

    preferred_desk = "equities" if ccy in ("KRW", "USD") else ""
    selected_rid = next((r["id"] for r in eligible if r.get("desk") == preferred_desk), eligible[0]["id"])
    choices = "".join(
        f'<option value="{e(r["id"])}"{" selected" if r["id"] == selected_rid else ""}>'
        f'{e(stamp(r["as_of"]))} · [{e(r["desk"])}] {e(r["title"])}</option>'
        for r in eligible
    )

    preview_html = ""
    if all(q.get(k) for k in ("entry", "bear", "base", "bull")):
        try:
            cand_a = dict(
                entry=str(Decimal(q["entry"])),
                bear=str(Decimal(q["bear"])),
                base=str(Decimal(q["base"])),
                bull=str(Decimal(q["bull"])),
                fees=str(Decimal(def_fees)),
                slip=str(Decimal(def_slip)),
            )
            cand_m = book.metrics(cand_a)
            preview_html = (
                '<div class="rebalance-bar"><b>자동 채움 시나리오 3관문 사전 시뮬레이션</b> · '
                '아래 목표가·약세가를 수정한 뒤 저장하면 내 가설 연구장에 확정 등록됩니다.'
                + gate_cards(cand_m)
                + price_gauge(cand_a, cand_m)
                + "</div>"
            )
        except Exception:
            preview_html = ""

    cat_val = e(q.get("catalyst", ""))
    inv_val = e(q.get("invalidate", ""))
    return (
        preview_html
        + form(base, csrf, "idea", secrets.token_hex(16))
        + '<label>근거 보고서<select name="report">' + choices + "</select></label>"
        + field("asset", "평가 대상 (종목명·코드)", val=q.get("asset", ""))
        + field("currency", "평가통화 (KRW / USD)", attrs='placeholder="KRW" maxlength="3"', val=ccy)
        + field("benchmark", "같은 통화 비교지수·대안 (자동 채움)", val=def_bench)
        + obs_field(val=def_obs)
        + price("entry", "대상 진입 기준가격", val=q.get("entry", ""))
        + price("benchmark_entry", "비교지수 현재값", val=def_bpx)
        + field("price_source", "대상 가격 원문 URL", "url", val=q.get("price_source", ""))
        + field("benchmark_source", "비교지수 원문 URL", "url", val=def_bsrc)
        + price("bear", "약세 시나리오 가격 · 확률 20%", val=q.get("bear", ""))
        + price("base", "기준 내재가치 목표가 · 확률 50%", val=q.get("base", ""))
        + price("bull", "강세 시나리오 목표가 · 확률 30%", val=q.get("bull", ""))
        + price("fees", "왕복 수수료·세금 (bp · 100bp=1%, 국내 기본 28)", val=def_fees)
        + price("slip", "왕복 슬리피지 (bp · 100bp=1%, 기본 12)", val=def_slip)
        + f'<label>예상 촉매와 핵심 투자 근거<textarea name="catalyst" rows="2" required placeholder="실적·수주·해자 근거">{cat_val}</textarea></label>'
        + f'<label>가설을 철회할 관측 조건 (손절 기준)<textarea name="invalidate" rows="2" required placeholder="수주 취소, 점유율 훼손 등">{inv_val}</textarea></label>'
        + field("due", "평가 만기 예정일 (기본 +6개월)", "date", val=def_due)
        + '<button>가설과 최초 가정 저장</button></form>'
    )


def outcome_form(row, base, csrf):
    if not row["start"]:
        return ('<details><summary>등록 이후 가격으로 모의 추적 시작</summary>' + form(base, csrf, "start", row["id"])
                + obs_field() + price("exit", "대상 추적 시작가격") + price("benchmark_exit", "비교지수 시작값")
                + field("source", "가격 원문", "url") + field("benchmark_source", "비교지수 원문", "url")
                + '<button>시작 관측 확정</button></form></details>')
    opts = "".join(f"<option>{e(v)}</option>" for v in book.VERDICTS)
    return ('<details><summary>관측 결과로 평가 종료</summary>' + form(base, csrf, "assess", row["id"])
            + obs_field() + price("exit", "대상 평가가격") + price("benchmark_exit", "비교지수 평가값")
            + field("source", "평가가격 원문", "url") + field("benchmark_source", "비교지수 평가값 원문", "url")
            + f'<label>판정<select name="verdict">{opts}</select></label>' + field("reason", "관측 근거·조기 종료 사유")
            + '<button>결과 확정</button></form></details>')


def price_gauge(a, m):
    vals = [float(Decimal(a[k])) for k in ("bear", "entry", "base", "bull")]
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return ""

    def x(v):
        return 26 + 548 * (v - lo) / (hi - lo)

    xb, xe, xbase, xbull = (x(v) for v in vals)
    down_left, down_w = min(xb, xe), abs(xe - xb)
    up_left, up_w = min(xe, xbull), abs(xbull - xe)
    svg = (
        '<svg viewBox="0 0 600 46" role="img" aria-label="시나리오 가격 범위">'
        '<rect x="26" y="20" width="548" height="8" rx="4" fill="#e5ecef"/>'
        f'<rect x="{down_left:.1f}" y="20" width="{down_w:.1f}" height="8" rx="4" fill="#df7a67"/>'
        f'<rect x="{up_left:.1f}" y="20" width="{up_w:.1f}" height="8" rx="4" fill="#7fc8b2"/>'
        f'<circle cx="{xb:.1f}" cy="24" r="6" fill="#c4493a"><title>약세 {e(a["bear"])}</title></circle>'
        f'<circle cx="{xe:.1f}" cy="24" r="7" fill="#17223b"><title>기준가 {e(a["entry"])}</title></circle>'
        f'<circle cx="{xbase:.1f}" cy="24" r="6" fill="#0d7a5f"><title>내재가치 {e(a["base"])}</title></circle>'
        f'<circle cx="{xbull:.1f}" cy="24" r="6" fill="#0b5cab"><title>강세 {e(a["bull"])}</title></circle>'
        "</svg>"
    )
    return (
        '<div class="price-gauge">' + svg + '<div class="gauge-legend">'
        f'<span>약세(20%) <b>{e(a["bear"])}</b> ({m["bear"]:+.1f}%)</span>'
        f'<span>진입 기준가 <b>{e(a["entry"])}</b></span>'
        f'<span>기준 내재가치(50%) <b>{e(a["base"])}</b></span>'
        f'<span>강세(30%) <b>{e(a["bull"])}</b></span></div>'
        '<small>약세선은 기계적 자동 손절선이 아니라 현금 버퍼 및 기업 가설 훼손 공시 점검선입니다.</small></div>'
    )


def gate_cards(m):
    exp_ok = m["expected"] >= 12
    pay_ok = m["payoff"] is not None and m["payoff"] >= 3
    mar_ok = m["margin"] >= 20
    payoff = f'{m["payoff"]:.2f}배' if m["payoff"] is not None else "산정 보류"
    items = (
        ("관문 1 · 기대수익률 (≥12%)", f'{m["expected"]:+.2f}%', exp_ok),
        ("관문 2 · 손익비 (≥3.0배)", payoff, pay_ok),
        ("관문 3 · 안전마진 (≥20%)", f'{m["margin"]:.2f}%', mar_ok),
    )
    cards = "".join(
        f'<div class="gate-card {"ok" if ok else "ng"}"><small>{label}</small>'
        f'<b>{val}</b><span class="{"badge-pass" if ok else "badge-warn"}">{"통과" if ok else "기준 미달"}</span></div>'
        for label, val, ok in items
    )
    return f'<div class="gate-grid">{cards}</div>'


def show(row, ledger, base, csrf):
    a, result = row["a"], row["result"]
    m = book.metrics(a)
    report = ledger.get(row["report"])
    badge = ('<span class="badge-pass">집중 후보 · 3관문 통과</span>'
             if m["qualifies"] else '<span class="badge-warn">축소·관망 · 기준 미달</span>')
    out = [f'<article class="investment-report"><h3>{e(a["asset"])} · {e(a["currency"])} {badge}</h3>'
           f'<p>등록 {e(stamp(row["created"]))} · 평가 예정 {e(row["due"])} · 비교 대상 {e(a["benchmark"])}</p>']
    if report:
        out.append(f'<a href="{e(base)}/desk/{e(report["desk"])}?all=1#report-{e(report["id"])}">{e(report["title"])}</a>')
    else:
        out.append("<strong>참조 보고서 확인 필요</strong>")
    payoff = f'{m["payoff"]:.2f}배' if m["payoff"] is not None else "산정 보류"
    gate = "세 수치 기준 충족" if m["qualifies"] else "미충족 또는 산정 보류"
    out.append(gate_cards(m) + price_gauge(a, m))
    out.append(f'<p>비용 후 기대수익률 <b>{m["expected"]:+.2f}%</b> · 약세 {m["bear"]:+.2f}% · '
               f'손익비 {payoff} · 안전마진 {m["margin"]:.2f}% · {gate}</p>'
               f'<p>촉매 · {e(a["catalyst"])}<br>철회 조건 · {e(a["invalidate"])}</p>'
               f'<details><summary>최초 가정과 가격 원문</summary><p>{e(stamp(a["observed"]))} · '
               f'대상 {e(a["entry"])} / 지수 {e(a["benchmark_entry"])} · 약세/기준/강세 '
               f'{e(a["bear"])} / {e(a["base"])} / {e(a["bull"])} · 수수료·세금 {e(a["fees"])}bp, '
               f'체결 비용 {e(a["slip"])}bp</p>대상 {chat_page.source_link(a["price_source"])} · '
               f'지수 {chat_page.source_link(a["benchmark_source"])}</details>')
    if row["start"]:
        start = row["start"]
        out.append(f'<p>모의 추적 시작 · {e(stamp(start["observed"]))} · 대상 {e(start["exit"])} '
                   f'{chat_page.source_link(start["source"])} / 지수 {e(start["benchmark_exit"])} '
                   f'{chat_page.source_link(start["benchmark_source"])}</p>')
    if result:
        net, bench, excess = book.performance(row)
        verdict_cls = "badge-pass" if result["verdict"] == "가설 지지" else "badge-warn"
        out.append(f'<p><span class="{verdict_cls}">{e(result["verdict"])}</span> · 평가 {e(stamp(result["observed"]))} · '
                   f'대상 순수익률 {net:+.2f}% / 지수 {bench:+.2f}% / 초과 {excess:+.2f}%p</p>'
                   f'<p>{e(result["reason"])} · 대상 {e(result["exit"])} {chat_page.source_link(result["source"])} · '
                   f'지수 {e(result["benchmark_exit"])} {chat_page.source_link(result["benchmark_source"])}</p>')
    else:
        out.append(outcome_form(row, base, csrf))
    return "".join(out) + "</article>"


def comparison(rows):
    groups = {}
    for row in rows:
        a = row["a"]
        if not row["result"]:
            key = (a["currency"], a["benchmark"], a["observed"], a["benchmark_entry"], row["due"])
            groups.setdefault(key, []).append((a["asset"], book.metrics(a)))
    out = []
    for (currency, benchmark, observed, entry, due), members in groups.items():
        if len(members) < 2:
            continue
        peak = max(abs(float(m["expected"])) for _, m in members) or 1.0
        out.append(f'<h3>{e(benchmark)} · {e(currency)}</h3><p>{e(stamp(observed))} '
                   f'기준 {e(entry)} · {e(due)} 평가 예정 · 기대수익률 높은 순 정렬</p><div class="comparison"><table><thead><tr>'
                   '<th>후보</th><th>판정</th><th>비용 후 기대수익률</th><th>약세 수익률</th><th>안전마진</th></tr></thead><tbody>')
        for name, m in sorted(members, key=lambda item: item[1]["expected"], reverse=True):
            width = min(100.0, max(4.0, 100.0 * abs(float(m["expected"])) / peak))
            cls = " neg" if m["expected"] < 0 else ""
            status = ('<span class="badge-pass">집중 후보</span>'
                      if m["qualifies"] else '<span class="badge-warn">기준 미달</span>')
            bar = f'<span class="inline-meter"><i class="{cls.strip()}" style="width:{width:.0f}%"></i></span>'
            out.append(f'<tr><td><b>{e(name)}</b></td><td>{status}</td><td>{bar}{m["expected"]:+.2f}%</td>'
                       f'<td>{m["bear"]:+.2f}%</td><td>{m["margin"]:.2f}%</td></tr>')
        out.append("</tbody></table></div>")
    return "<section><h2>동일 조건 후보 비교</h2>" + "".join(out) + "</section>" if out else ""


def archive_controls(package, base, csrf):
    if package is None:
        return ""
    root = package / ".local"
    folder = root / "research-archives"
    saved = (sorted((p.name for p in folder.iterdir() if re.fullmatch(r"\d{8}-\d{6}-\d{6}", p.name)
                     and not p.is_symlink() and p.is_dir()), reverse=True)
             if not folder.is_symlink() and folder.is_dir() else [])
    def start(action):
        return (f'<form method="post" action="{e(base)}/desk/manager/{action}">'
                f'<input type="hidden" name="csrf" value="{e(csrf)}">')
    recovery = ""
    if saved:
        recovery = (start("recover") + '<label>독립 복구할 스냅샷<select name="snapshot_id">'
                    + "".join(f'<option>{s}</option>' for s in saved)
                    + "</select></label><button>복구본 생성 및 검증</button></form>")
    today = datetime.now(intel.KST).date()
    return ('<details id="archives"><summary>연구 백업과 공개 수급 노트</summary>'
            '<p>연구 스냅샷에는 가설·모의 결과·게시 보고서가 들어갑니다. '
            '복구 시 별도 폴더에 사본을 만들고 보고서 연결을 검사합니다.</p>'
            + start("snapshot") + '<button>연구 스냅샷 저장</button></form>' + recovery
            + start("market-note") + f'<label>공개 수급 노트 날짜<input type="date" name="day" value="{today}" required></label>'
            '<button>로컬 Markdown 저장</button></form><small>공개 노트 폴더 · private_accounts/.local/market-notes</small></details>')


def render(package, base, csrf, css, done=None, query=None):
    q = query or {}
    ledger = reports.read(package)
    rows = book.entries(package)
    today = datetime.now(intel.KST).date().isoformat()
    groups = [("평가일 도래", [r for r in rows if not r["result"] and r["due"] <= today]),
              ("추적 중", [r for r in rows if not r["result"] and r["due"] > today]),
              ("평가 완료", [r for r in rows if r["result"]])]
    pending_rows = groups[0][1] + groups[1][1]
    qualifying = sum(book.metrics(r["a"])["qualifies"] for r in pending_rows)
    closed = groups[-1][1]
    wins = sum(book.performance(r)[2] > 0 for r in closed)
    guide = (
        '<div class="guide-banner"><h2>초보자용 가설 연구장 활용법 · 왜 투자 전에 시나리오를 적나요?</h2>'
        '<p>폭락장에서는 모든 종목이 싸 보이지만 실제로는 내재가치 대비 안전마진이 큰 소수 핵심주만 빠르게 회복합니다. '
        '매수·집중 전에 숫자로 시나리오를 고정해 두면 장중 공포나 급등락에 흔들리지 않습니다.</p>'
        '<div class="step-flow">'
        '<div class="step-box"><b><span class="step-num">1</span>시나리오 고정</b>'
        '<small>약세(20%)·기준 내재가치(50%)·강세(30%) 가격과 가설 철회 공시 조건을 미리 적습니다.</small></div>'
        '<div class="step-box"><b><span class="step-num">2</span>3대 관문 선별</b>'
        '<small>기대수익률 ≥12% · 손익비 ≥3배 · 안전마진 ≥20%를 모두 통과한 초록 배지 종목에만 집중합니다.</small></div>'
        '<div class="step-box"><b><span class="step-num">3</span>현금 버퍼·만기 채점</b>'
        '<small>단순 가격 흔들림(-10%)에 기계적으로 손절하지 않고 현금 버퍼로 견디되, 만기·공시 시점에 지수와 성적을 비교합니다.</small></div>'
        '</div></div>'
    )
    kpis = (
        '<div class="kpi-strip">'
        f'<div class="kpi-box info"><small>전체 등록 가설</small><strong>{len(rows)}건</strong></div>'
        f'<div class="kpi-box pass"><small>3관문 통과 · 집중 후보</small><strong>{qualifying}건</strong></div>'
        f'<div class="kpi-box warn"><small>기준 미달 · 축소·대기</small><strong>{len(pending_rows) - qualifying}건</strong></div>'
        f'<div class="kpi-box info"><small>검증 완료 (지수 초과)</small><strong>{len(closed)}건 ({wins}건)</strong></div>'
        '</div>'
    )
    open_attr = " open" if (q.get("open") == "create" or q.get("asset")) else ""
    out = [f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" '
           f'content="width=device-width,initial-scale=1"><title>가설 연구장</title><style>{css}</style></head><body>'
           '<header><div><strong>Whale Tracking</strong><small>로컬 투자 관리 · 가설 연구장</small></div></header>',
           chat_page.navigation(base, "research"), '<main class="desk-main"><h1>가설 연구장</h1>'
           '<p>현금 매수 가정의 가격수익률을 같은 통화·기간의 지수와 비교합니다. '
           '배당·이자·임대료를 제외하며, 분할·병합은 양 시점에 같은 조정 기준을 적용하세요.</p>',
           guide, kpis,
           f'<p>검증 완료 {len(closed)}건 · 비교지수 초과 {wins}건 · 전체 등록 {len(rows)}건</p>',
           f'<details id="create"{open_attr}><summary>새 투자 가설 등록 (비교지수·수수료 자동 채움 지원)</summary>'
           '<p>기대수익률 12%는 입력한 평가기간 기준입니다. 약세 손실과 기준 이익이 있는 경우 '
           '확률가중 손익비 3배를 검사하며 안전마진 기준은 20%입니다. 등록한 가정은 결과와 함께 보존합니다.</p>',
           new_form(ledger, base, csrf, query=q, package=package), "</details>", comparison(rows)]
    for name, group in groups:
        out.append(f"<section><h2>{name} · {len(group)}건</h2>")
        out.extend(show(r, ledger, base, csrf) for r in group)
        out.append("</section>")
    messages = {"snapshot": "연구 스냅샷을 저장하고 연결을 검증했습니다.",
                "recover": "운영 원장과 별도로 복구 사본을 검증했습니다.",
                "market-note": "공개 수급 노트를 저장했습니다."}
    if done in messages:
        out.append(f'<p role="status">{messages[done]}</p>')
    return ("".join(out) + archive_controls(package, base, csrf) + "</main></body></html>").encode()
