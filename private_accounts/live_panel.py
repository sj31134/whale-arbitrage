"""Private, server-rendered valuation and market variable panels."""
from datetime import datetime
from decimal import Decimal
from html import escape

from agents import intelligence as intel, market_prices
from agents.portfolio import portfolio_accounts
from . import live_valuation, store


def e(value):
    return escape(str(value), quote=True)


def fmt(value):
    if value is None:
        return "—"
    n = Decimal(value)
    digits = 2 if abs(n) >= 1 else 8
    return f"{n:,.{digits}f}".rstrip("0").rstrip(".") if n else "0"


def signed(value):
    if value is None:
        return "—"
    direction = "gain" if value > 0 else "loss" if value < 0 else "flat"
    return f'<span class="amount-{direction}">{"+" if value > 0 else ""}{fmt(value)}</span>'


def time(value):
    if not value:
        return "기록 없음"
    if len(value) == 10:
        return e(value)
    return e(datetime.fromisoformat(value).astimezone(intel.KST).strftime("%Y.%m.%d %H:%M:%S KST"))


def script(base):
    return f'<script defer src="{e(base)}/live.js"></script>'


def networth_reference(accounts, book):
    """Reference-only KRW-converted total net worth & Kimchi premium badge. Keeps accounting denominators separate."""
    if not accounts or book is None or not book.fx:
        return ""
    fx = Decimal(book.fx["price"])
    usdt_rate = Decimal(book.usdt_usd["price"]) if getattr(book, "usdt_usd", None) else Decimal(1)
    total_krw = Decimal(0)
    gain_krw = Decimal(0)
    has_foreign = False
    has_gain = False
    for a in accounts:
        for m in a.get("marks", ()):
            if m["value"] is None:
                continue
            mult = Decimal(1)
            if m["currency"] == "USD":
                mult, has_foreign = fx, True
            elif m["currency"] == "USDT":
                mult, has_foreign = fx * usdt_rate, True
            total_krw += Decimal(m["value"]) * mult
            if m.get("gain") is not None:
                gain_krw += Decimal(m["gain"]) * mult
                has_gain = True
    if not has_foreign or total_krw <= 0:
        return ""
    man_won = total_krw / Decimal(10000)
    gain_txt = f" · 환산 총평가손익 {signed(gain_krw)}원" if has_gain else ""
    kimp_txt = ""
    up_btc = book.match("upbit", "BTC", "KRW")
    bn_btc = book.match("binance", "BTC", "USDT")
    if up_btc and bn_btc and Decimal(bn_btc["price"]) > 0:
        fair_krw = Decimal(bn_btc["price"]) * usdt_rate * fx
        kimp = (Decimal(up_btc["price"]) / fair_krw - 1) * 100
        kimp_txt = f' <span class="badge-info">BTC 김치프리미엄 {kimp:+.2f}%</span>'
    return (
        '<div class="networth-banner">'
        f'<div><small>환율({fmt(fx)}원/USD) 반영 전체 계좌 단순 합산 참고치</small> '
        f'<strong>총 {fmt(total_krw)}원 (약 {man_won:,.0f}만 원)</strong>{gain_txt}{kimp_txt}</div>'
        '<small>계좌·통화별 공식 비중 분모와는 분리된 통합 참고 지표입니다.</small></div>'
    )


def _canonical_symbol(provider, sym):
    from agents.equities.daily_bars import BSTOCKS
    from agents.portfolio import normalize
    up = sym.strip().upper()
    if provider == "binance" and up in BSTOCKS and len(up) >= 3:
        up = up[:-1]
    if up == "GOOGL":
        return "GOOG"
    return normalize(up).replace(" ", "") or up


def multi_account_overlap(accounts):
    """Highlight non-cash symbols (including US stock + Binance RWA bStock pairs) split across 2+ accounts."""
    from agents.equities.daily_bars import BSTOCKS
    from agents.portfolio import CASH_NAMES
    grouped = {}
    for a in accounts or ():
        for m in a.get("marks", ()):
            sym = m["symbol"].strip()
            if sym.upper() in CASH_NAMES or m["state"].startswith("통화 잔액") or m["value"] is None:
                continue
            key = (m["currency"], _canonical_symbol(a["provider"], sym))
            entry = grouped.setdefault(key, dict(symbols=[], total=Decimal(0), accs=set(), has_rwa=False))
            if sym not in entry["symbols"]:
                entry["symbols"].append(sym)
            entry["total"] += Decimal(m["value"])
            entry["accs"].add(f'{store.PROVIDERS[a["provider"]]}({a["account"]})')
            if a["provider"] == "binance" and sym.upper() in BSTOCKS:
                entry["has_rwa"] = True
    overlaps = [
        f'<b>{e(" + ".join(v["symbols"]))}</b> {len(v["accs"])}개 계좌 합산 {fmt(v["total"])} {e(ccy)}'
        + (' <span class="badge-warn">본주+RWA 기초자산 중복</span>' if v["has_rwa"] else "")
        for (ccy, _), v in sorted(grouped.items())
        if len(v["accs"]) >= 2
    ]
    if not overlaps:
        return ""
    return (
        '<div class="networth-banner"><small>다계좌·본주+RWA 중복 보유 합산 (동일 통화 참고): '
        + " · ".join(overlaps[:6])
        + "</small></div>"
    )


def networth_and_cards(accounts, book):
    return networth_reference(accounts, book) + multi_account_overlap(accounts) + currency_cards(accounts)


def currency_cards(accounts):
    buckets = {}
    for account in accounts:
        for m in account["marks"]:
            buckets.setdefault(m["currency"], []).append(m)
    out = ['<div class="value-grid">']
    for currency, marks in sorted(buckets.items()):
        complete = all(m["value"] is not None for m in marks)
        total = sum(m["value"] for m in marks if m["value"] is not None)
        gains = [m["gain"] for m in marks if m["gain"] is not None]
        label = "평가금액" if complete else "평가 가능분"
        gain = sum(gains) if gains else None
        live = sum(m["price"] is not None for m in marks)
        changes = [m["change"] for m in marks if m["change"] is not None]
        out.append(f'<article class="balance-tile"><small>{e(currency)} · {label}</small>'
                   f'<strong>{fmt(total) if any(m["value"] is not None for m in marks) else "—"}</strong>'
                   f'<div>평가손익 <b>{signed(gain)}</b></div>'
                   f'<div class="mark-change">원장 대비 변동 {signed(sum(changes) if changes else None)} · 계산 {len(changes)}행</div><small>손익 산출 {len(gains)}/{len(marks)}행'
                   f' · 시세 반영 {live}/{len(marks)}행</small></article>')
    if not buckets:
        out.append('<p>수량과 평가통화가 있는 계좌 자료를 기다리고 있습니다.</p>')
    return "".join(out) + "</div>"


def allocation(accounts):
    bars = []
    for a in accounts:
        by_ccy = {}
        for m in a["marks"]:
            if m["weight_pct"] is not None:
                group = by_ccy.setdefault(m["currency"], [])
                group.append(m)
        for ccy, members in sorted(by_ccy.items()):
            top = max(members, key=lambda m: Decimal(m["weight_pct"]))
            w = Decimal(top["weight_pct"])
            bars.append(f'<div class="allocation-line"><small>{e(store.PROVIDERS[a["provider"]])} · '
                        f'{e(a["account"])} · {e(ccy)}</small><div><b>{e(top["symbol"])}</b>'
                        f'<span>{w:.1f}%</span></div><progress value="{w}" max="100" '
                        f'aria-label="최대 보유 비중">{w}%</progress></div>')
    return ('<div class="allocations">' + "".join(bars[:4]) + '</div>') if bars else '<small>비중 산출 대기</small>'


def variables(package):
    cache = intel.private_json(package, intel.CACHE, {})
    captures = intel.private_json(package, intel.CAPTURE_FILE, {})
    out = ['<div class="market-strip">']
    for key, label in (("financial_conditions/DGS10", "미국 10년 금리"), ("financial_conditions/DEXKOUS", "달러·원"),
                       ("financial_conditions/BAMLH0A0HYM2", "하이일드 스프레드"), ("market_flow/VIXCLS", "VIX")):
        hit = cache.get(key, {})
        rows = hit.get("items", [])
        latest = max(rows, key=lambda row: row["as_of"]) if rows else {}
        capture = captures.get(key.split("/")[-1], {})
        manual = max(capture.get("items", []), key=lambda row: row["as_of"], default={})
        status = hit.get("status", "미수집")
        checked = hit.get("collected")
        if manual and (manual["as_of"], capture["collected"]) >= (latest.get("as_of", ""), hit.get("collected", "")):
            latest = manual
            checked = capture["collected"]
            status = "원문 확인 · 자동 " + status
        points = latest.get("history", [])
        spark = ""
        if len(points) >= 2:
            vals = [Decimal(v) for _, v in points]
            lo, hi = min(vals), max(vals)
            bars = "".join(f'<i style="height:{int(15 + 85*(v-lo)/(hi-lo)) if hi>lo else 50}%"></i>' for v in vals)
            spark = f'<span class="mini-chart" title="{e(points[0][0])} ~ {e(points[-1][0])}">{bars}</span>'
        out.append(f'<article><small>{label}</small><strong>{e(latest.get("value", "—"))}</strong>{spark}'
                   f'<small>{e(latest.get("as_of", "관측 대기"))} · {e(status)}</small><small>선택 자료 수집·확인 {time(checked)}</small></article>')
    return "".join(out) + "</div>"


def panel(directory, package, book=None, accounts=None, *, manager_base=None, detail_base=None):
    from .history_panel import eligible
    if book is None:
        book = live_valuation.read(package)
    if accounts is None:
        accounts = portfolio_accounts(directory, package, quote_book=book)
    good = sum(r["status"] == "수집 완료" for r in book.sources.values())
    stock_feeds = (*market_prices.KOREA,*market_prices.AMERICA)
    recent = set()
    now = datetime.now(intel.KST)
    for feed in stock_feeds:
        state = book.sources.get(feed,{})
        if state.get("status") == "수집 완료" and state.get("success") and (now-datetime.fromisoformat(state["success"])).total_seconds() <= 300:
            recent.add(feed)
    if recent == set(stock_feeds):
        badge,tone = "국내·미국 주식 시세 수집 중","ok"
    elif recent:
        badge,tone = f"주식 원천 {len(recent)}/{len(stock_feeds)} 최근 수신","pending"
    else:
        badge,tone = ("주식 시세 갱신 대기 · 저장값 표시" if book.sources else "주식 시세 연결 대기"),"pending"
    manager = manager_base is not None
    title = "내 포트폴리오" if manager else "계좌 평가"
    out = ['<section id="live-values" data-watch class="live-values"><div class="value-head">'
           f'<h2>{title}</h2><span class="live-badge {tone}">{badge}</span></div>',
           networth_and_cards(accounts, book)]
    books = [a["as_of"] for a in accounts if a["source"] == "workbook"]
    ticks = [m["at"] for a in accounts for m in a["marks"] if m.get("at")]
    out.append('<div class="valuation-dates"><span>화면 자료 조회 <b>' + time(now.isoformat())
               + '</b></span><span>엑셀 수정 <b>' + time(max(books, default=None))
               + '</b></span><span>최근 연결 시세 <b>' + time(max(ticks, key=datetime.fromisoformat, default=None)) + '</b></span></div>')
    context = ('<div class="live-split"><div><h3>계좌별 최대 비중</h3>' + allocation(accounts)
               + '</div><div><h3>시장 변수</h3>' + variables(package) + '</div></div>')
    if not manager:
        out.append(context)
    out.append('<details id="live-positions"' + (' open' if manager else '') +
               '><summary>종목별 현재가·손익</summary><div class="comparison"><table><thead><tr>')
    core_columns = ("계좌", "종목", "시장 단가", "평가통화", "수량", "평가 단가", "평가금액", "평가손익", "수익률", "비중", "상태")
    if manager:
        core_columns = ("종목", "시장 단가", "평가금액", "평가손익", "수익률", "비중", "상태", "평가통화", "계좌", "수량", "평가 단가")
    columns = (*core_columns, "원천 · 가격 기준시각", "해당 시세 마지막 수신·확인", "환율 기준 / 수신", "수량 기준")
    out.extend(f'<th>{label}</th>' for label in columns)
    out.append("</tr></thead><tbody>")
    for a in accounts:
        for m in a["marks"]:
            name = "업비트 공개 표본" if m["feed"] == "upbit_sample" else market_prices.SOURCES.get(m["feed"])
            source = (f'<a rel="noreferrer" target="_blank" href="{e(market_prices.origin(m["feed"], m["page"]))}">'
                      f'{e(name)}</a> · ' if name else "")
            state = m["state"]
            if m["price"] is None and state != "통화 잔액":
                state += " · 원장 평가액" if m["value"] is not None else " · 평가 불가"
            if m["delay"] and m["delay"] != "0":
                state += " · 원천 지연 " + m["delay"] + "분"
            symbol = e(m["symbol"])
            if manager or detail_base:
                pid = intel.position_id(a["provider"], a["account"], m["symbol"], m["currency"])
                position_url = f"{e(manager_base or detail_base)}/portfolio?position={pid}"
                symbol = f'<a href="{position_url}#position">{symbol}</a>'
                if eligible(a["provider"], m):
                    symbol += (f' <a class="price-link" href="{position_url}#price-history" aria-label="{e(m["symbol"])} 가격 차트">차트</a>'
                               f' <a class="price-link" href="{e(manager_base or detail_base)}/quant?position={pid}">퀀트 연구</a>')
            cells = {"시장 단가": fmt(m.get("market_price")) + " <small>" + e(m.get("market_currency") or "") + "</small>",
                     "종목": symbol, "계좌": e(store.PROVIDERS[a["provider"]] + " · " + a["account"]),
                     "평가통화": e(m["currency"]), "수량": e(m["qty"]), "평가 단가": fmt(m["price"]),
                     "평가금액": fmt(m["value"]), "평가손익": fmt(m["gain"]), "상태": e(state),
                     "수익률": fmt(m["rate"]) + "%" if m["rate"] is not None else "—",
                     "비중": fmt(m["weight_pct"]) + "%" if m["weight_pct"] is not None else "—"}
            out.append("<tr>" + "".join(f"<td>{cells[column]}</td>" for column in core_columns)
                + f'<td>{source}{time(m["at"])}</td><td>{time(m.get("seen"))}</td>'
                + f'<td>{time(m["fx_at"]) + " / " + time(m.get("fx_seen")) if m["fx_at"] else "—"}</td>'
                + f'<td>{time(a["as_of"])}</td></tr>')
    if not any(a["marks"] for a in accounts):
        out.append(f'<tr><td colspan="{len(columns)}">표시할 보유 행이 없습니다. 계좌 원천과 기준시각을 확인하세요.</td></tr>')
    out.append('</tbody></table></div><small>시세 미연결 행은 원장 평가액을 사용합니다. '
               '외화 단가는 평가통화 환산 기준입니다. 원가는 원장의 같은 통화 평가액에서 손익을 빼거나 수량에 같은 통화 매입단가를 곱해 구합니다. 매도 비용은 제외합니다. 이전 수집기에서 기록한 수신 시각은 수집 시작 시각입니다.</small></details>')
    if manager:
        out.append(context)
    out.append(f'<details id="quote-health"><summary>시세 원천 최근 시도 성공 {good}/{len(market_prices.SOURCES)}</summary>'
               '<div class="comparison"><table><tr><th>원천</th><th>상태</th><th>시도</th><th>마지막 성공</th></tr>')
    for k, label in market_prices.SOURCES.items():
        s = book.sources.get(k, {})
        out.append(f'<tr><td>{e(label)}</td><td>{e(s.get("status", "수집 대기"))}</td>'
                   f'<td>{time(s.get("attempt"))}</td><td>{time(s.get("success"))}</td></tr>')
    return "".join(out) + '</table></div></details><small data-poll-status></small></section>'
