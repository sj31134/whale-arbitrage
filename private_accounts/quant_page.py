"""Authenticated SMA research on locally matched holdings."""

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from decimal import Decimal
from html import escape
from urllib.parse import urlencode

from agents import intelligence
from agents.equities.daily_bars import VENUES
from agents.portfolio import portfolio_accounts
from . import chat_page, live_valuation, price_history, quant, history_panel
from .equity_screen import close_checks


def pct(x):
    return f"{100 * x:+.2f}%"


def plot(title, dates, series, markers=()):
    colors = ("#1b528d", "#a75816")
    values = [v for _, line in series for v in line] + [p for _, _, p in markers]
    lo, hi = min(values), max(values)

    def x(i):
        return 10 + 750 * i / max(1, len(dates) - 1)

    def y(v):
        return 78 if hi == lo else 145 - 130 * (v - lo) / (hi - lo)

    shapes = []
    for color, (_, line) in zip(colors, series):
        points = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(line))
        shapes.append(
            f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{points}"/>'
        )
    for i, side, price in markers:
        label, color = ("진입", "#00855c") if side > 0 else ("청산", "#bb3040")
        shapes.append(
            f'<circle cx="{x(i):.1f}" cy="{y(price):.1f}" r="4" fill="{color}"><title>{dates[i]} {label} {price:g}</title></circle>'
        )
    legend = " · ".join(
        f'<b style="color:{c}">{escape(k)}</b>' for c, (k, _) in zip(colors, series)
    )
    return (
        f"<section><h3>{title}</h3>{legend}<small> · 범위 {lo:.3f} ~ {hi:.3f}</small>"
        f'<svg viewBox="0 0 770 155" role="img" aria-label="{title}">{"".join(shapes)}</svg>'
        f"<small>{dates[0]} ~ {dates[-1]}</small></section>"
    )


def history_for_research(db, key, sessions):
    """Use one feed. Assess continuity on its training prefix before comparing lengths."""
    feeds = db.execute(
        "SELECT source,count(*) AS n FROM price_bar WHERE (venue,symbol,currency)=(?,?,?) AND "
        + price_history.VENUE_BARS + " "
        "GROUP BY source ORDER BY n DESC,max(day) DESC,source",
        key,
    ).fetchall()
    best_rows, best_source, best_rank = [], None, (-1, -1)
    for feed in feeds:
        rows = db.execute(
            "SELECT * FROM price_bar WHERE (venue,symbol,currency,source)=(?,?,?,?) ORDER BY day",
            (*key, feed["source"]),
        ).fetchall()
        reserved = len(rows) >= quant.MIN_ROWS
        train = rows[: -quant.HOLD] if reserved else rows
        usable, _ = quant.prepare(train, sessions, key[0], recover=True)
        rank = (
            int(reserved and len(usable) >= quant.MIN_ROWS - quant.HOLD),
            len(usable),
        )
        if rank > best_rank:
            best_rows, best_source, best_rank = rows, feed["source"], rank
    return best_rows, best_source, len(feeds)


def experiment(package, key, source, rows, sessions):
    fee = quant.costs(key[0])
    inputs = dict(
        key=list(key),
        source=source,
        version=quant.VERSION,
        costs=vars(fee),
        sessions=sorted(
            d for d in sessions if rows and rows[0]["day"] <= d <= rows[-1]["day"]
        ),
        rows=[
            {k: r[k] for k in ("day", "opening", "closing", "revisions")} for r in rows
        ],
    )
    digest = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    name = f"quant-{digest}.json"
    saved = intelligence.private_json(package, name, None)
    bars, result = quant.replay(inputs, saved["result"] if saved else None)
    if saved is None:
        saved = dict(inputs=inputs, result=result)
        intelligence.update_json(package, name, {}, lambda _: saved)
    result = saved["result"].copy()
    for group in ("scores", "holdout"):
        result[group] = {int(n): s for n, s in result[group].items()}
    return bars, result, digest


def report(base, pid, n, bars, r, key, digest):
    pick = r["candidate"]
    period = n if n in quant.PERIODS else pick or 20
    scores = r["scores"]
    out = ["<section><h2>" + ("선정" if r["selected"] else "선정 보류") + "</h2>"]
    if r.get("history_warnings"):
        out.append(
            f"<p>학습 이력 중 {r['excluded']}봉 제외 · {escape(' · '.join(r['history_warnings']))}. 단절 뒤 연속 구간에서 워밍업을 다시 시작합니다.</p>"
        )
    if pick:
        out.append(
            f"<p>홀드아웃 전에 고른 선 <b>{pick}일</b> · 학습 구간 비용 후 수익률 기준</p>"
        )
    out.append(
        "<p>"
        + " · ".join(
            map(escape, r["reasons"] or ["워크포워드·홀드아웃·인접 기간 기준 통과"])
        )
        + "</p></section>"
    )
    if scores:
        out.append(
            f'<section><h2>학습 구간 성과</h2><p>{" ~ ".join(r["training"])} · 비용 후 수익률 · 파랑은 이익, 주황은 손실 · 셀을 눌러 비교</p><div class="heat">'
        )
        ceiling = max(abs(m["net"]) for m in scores.values()) or 1
        for k, m in scores.items():
            rgb = "92,160,210" if m["net"] >= 0 else "223,133,75"
            url = escape(base + "/quant?" + urlencode(dict(position=pid, period=k)))
            out.append(
                f'<a href="{url}" style="background:rgba({rgb},{0.1 + 0.55 * abs(m["net"]) / ceiling:.2f})" aria-current="{str(k == period).lower()}">{k}일<small>{pct(m["net"])}</small></a>'
            )
        out.append("</div></section>")
        final = bool(r["holdout"])
        if not final:
            bars = [b for b in bars if b["day"] <= r["training"][-1]]
        start = len(bars) - quant.HOLD if final else quant.WARM
        dates = [b["day"] for b in bars[start:]]
        fee = quant.costs(key[0])
        events, means = quant.signals([b["decimal"] for b in bars], period)

        def run(ev, scale):
            return quant.simulate(bars, ev, start, len(bars), fee, scale, detail=True)

        strategy, benchmark = run(events, 1), run(None, 1)
        out.append(
            f"<section><h2>{period}일선 · {'최종 미사용 구간' if final else '탐색 구간'}</h2><p>가격은 {escape(key[2])} 기준 · 진입은 초록점, 청산은 빨간점</p></section>"
        )
        out.append(
            plot(
                "가격과 모의 체결",
                dates,
                [
                    ("종가", [b["close"] for b in bars[start:]]),
                    (f"SMA {period}", means[start:]),
                ],
                strategy["markers"],
            )
        )
        for title, field in (
            ("누적성과 · 시작자산 1", "path"),
            ("낙폭 · 고점 대비 비율", "drawdowns"),
        ):
            out.append(
                plot(
                    title,
                    dates,
                    [("전략", strategy[field]), ("단순 보유", benchmark[field])],
                )
            )
        out.append(
            "<section><h3>거래비용 민감도</h3><table><tr><th>비용 배수</th><th>전략</th><th>보유</th><th>차이</th><th>전략 최대낙폭</th><th>체결 / 왕복</th><th>회전율¹</th></tr>"
        )
        for scale in (0.5, 1, 2):
            a, b = run(events, scale), run(None, scale)
            out.append(
                f"<tr><td>{scale:g}배</td><td>{pct(a['net'])}</td><td>{pct(b['net'])}</td><td>{100 * (a['net'] - b['net']):+.2f}%p</td><td>{pct(a['mdd'])}</td><td>{a['fills']} / {a['exits']}</td><td>{a['turnover']:.2f}배</td></tr>"
            )
        out.append(
            "</table><small>¹ 각 체결대금 ÷ 체결 직전 자산의 누적합</small></section>"
        )
        if final:
            near = [
                f"{k}일 {100 * r['holdout'][k]['excess']:+.2f}%p"
                for k in quant.PERIODS
                if abs(k - period) <= 2
            ]
            out.append(
                "<section><h3>인접 기간의 홀드아웃 초과수익</h3>"
                + " · ".join(near)
                + "</section>"
            )
        if r["folds"]:
            out.append(
                "<section><h3>워크포워드 · 과거 자료로 고른 선의 다음 42일 성과</h3><table><tr><th>평가 기간</th><th>선</th><th>전략</th><th>보유</th></tr>"
            )
            for f in r["folds"]:
                out.append(
                    f"<tr><td>{f['start']} ~ {f['end']}</td><td>{f['period'] or '보류'}</td><td>{pct(f['metrics']['net']) if f['metrics'] else '—'}</td><td>{pct(f['benchmark']['net'])}</td></tr>"
                )
            out.append("</table></section>")
    c = r["costs"]
    out.append(
        f"<section><h3>계산 조건</h3><p>편도 수수료 {c['commission']:g}bp · 반 스프레드 {c['half_spread']:g}bp · 슬리피지 {c['slippage']:g}bp · 매도 거래세 가정 {c['sell_tax']:g}bp. 모두 연구용 가정이며 상품별 면세·시점별 세율·개인 양도세는 미반영. 1bp = 0.01%.</p>"
        "<p>공통 워밍업 121봉, 학습 최소 126봉, 순차 평가 최소 2회, 마지막 63봉 봉인. 학습 왕복 2회 이상 중 비용 후 수익률 1위, 동률이면 짧은 선을 선택합니다. 각 구간은 현금에서 시작하며 직전 종가의 돌파부터 허용합니다. 종가가 선과 같으면 직전 방향을 유지합니다.</p>"
        "<p>신호 후 다음 유효 시가에 전액 체결하며 대기 중 반대 신호가 나오면 교체합니다. 마지막 보유분은 종가 평가하며 청산비를 부과하지 않습니다. 단순 보유도 동일한 비용과 종료 규칙을 씁니다. 토큰은 거래소별 자체 USD 또는 USDT 일봉의 UTC 시가를 사용합니다.</p>"
        "<p>학습 구간의 결측·가격 단절 뒤에는 워밍업부터 다시 시작합니다. 최종 평가 구간의 결측·단절은 선정을 보류합니다. 전체 거래소 달력과 기업행사 원장은 미확보입니다. 배당 재투자와 현금이자 제외, 원천 가격 기준입니다. 토큰은 체결이 관측된 일봉을 사용합니다. 과거 호가와 정지 원장이 없어 유효 시가에서 모의 체결을 가정합니다. 현재 보유 종목 표본에는 상장폐지·생존편향이 있습니다. 과거 정정 전 시세는 복원할 수 없습니다.</p>"
        f"<small>{quant.VERSION} · 입력 식별값 {digest[:16]}</small></section>"
    )
    return "".join(out)


def market_screen_panel(package, key, symbol, choices=None):
    index = intelligence.private_json(package, "equity_screen_index.json", {}) if package else {}
    stamp = index.get("run", "")
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}", stamp):
        return ""
    path = package / ".local" / "equity_screens" / (stamp + ".sqlite3")
    if not path.is_file() or path.is_symlink():
        return ""
    states = {"rule_pass": "연구 기준 통과", "rule_fail": "기준 미달",
              "quality_hold": "연속 일봉 부족·품질 보류", "action_hold": "기업행동 확인 대기"}
    checks = close_checks(path.parent, stamp)
    def verification(kind, venue, code):
        mark = checks.get((kind, venue, code, "KRW" if venue == "KRX" else "USD"))
        return {"confirmed":"독립 종가 일치", "conflict":"종가 불일치 · 판단 보류"}.get(mark,"독립 종가 확인 대기")
    out = ['<section id="market-sma"><h2>국내·미국 이동평균 검증</h2>',
           '<table><thead><tr><th>시장 · 완료일</th><th>1차 표본</th><th>품질·기업행동 보류</th>'
           '<th>기준 미달</th><th>기준 통과</th></tr></thead><tbody>']
    for market, label in (("KR", "한국"), ("US", "미국")):
        counts = index["markets"][market]
        out.append(f'<tr><th>{label} · {escape(index["days"][market])}</th>'
                   f'<td>{counts["total"]:,}</td><td>{counts["held"]:,}</td>'
                   f'<td>{counts["failed"]:,}</td><td>{counts["passed"]:,}</td></tr>')
    out.append('</tbody></table><small>주식·ETF 등 상장 상품 · 마지막 63거래일 평가 · 비용 차감 · 기업행동 원장 일부 확보</small>')
    out.append('<p><a href="quant/equity-screen.csv" download="public-equity-sma.csv">공개 종목 결과 CSV</a></p>')
    supplemental = index.get("supplement")
    recovered = index.get("recovery")
    recovery_path = path.with_name(stamp + "-naver.sqlite3")
    def recovered_stock(venue, code):
        if not recovered or venue != "KRX" or not recovery_path.is_file() or recovery_path.is_symlink():
            return None
        with closing(sqlite3.connect(recovery_path.resolve().as_uri() + "?mode=ro", uri=True)) as archive:
            hit = archive.execute("SELECT detail FROM result WHERE venue=? AND symbol=? AND currency='KRW'",
                                  (venue, code)).fetchone()
        return json.loads(hit[0]) if hit else None
    if recovered:
        out.append(f'<p>국내 거래장 미확정 참고 이력 {recovered["total"]:,}개 · 모의 규칙 통과 {recovered["passed"]:,}개. '
                   '정규장 전략 통과 수에서 제외합니다.</p>')
    for market, info in index.get("checks", {}).items():
        out.append(f'<p>{"한국" if market == "KR" else "미국"} 기준선 통과 중 독립 종가 일치 '
                   f'{info["confirmed"]:,}개 · 불일치 {info["conflict"]:,}개 · 대조 자료 없음 {info["unavailable"]:,}개</p>')
    if "positive_with_cost2_edge" in index.get("checks", {}).get("US", {}):
        out.append(f'<p>미국 보통주 전진검증 우선 표본 <strong>{index["checks"]["US"]["positive_with_cost2_edge"]}개</strong> · '
                   '독립 종가 일치, 기본 비용 후 절대수익 양수, 비용 2배에서 단순 보유 초과. CSV에서 Y로 표시합니다.</p>')
    if supplemental:
        out.append(f'<p>국내 결측일 교차검증 · {escape(index["gap_day"])} 일봉을 확인한 '
                   f'{supplemental["total"]:,}개로 별도 재실험 · 기준 통과 {supplemental["passed"]:,}개</p>')
    out.append('<form action="#market-sma"><label>공개 종목코드 <input name="screen_symbol" maxlength="32" '
               'placeholder="코드 또는 티커"></label> <button>검증 결과 조회</button></form>')
    symbol = symbol.strip().upper()
    select = "SELECT venue,symbol,detail FROM result WHERE "
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        if choices:
            out.append('<details id="portfolio-sma"><summary>내 보유 종목과 대조</summary><table><tr>'
                       '<th>종목</th><th>이번 검증</th><th>학습에서 고른 선</th></tr>')
            with live_valuation.connection(package) as prices:
                for pid, (account, mark) in choices.items():
                    instrument = price_history.local_history_key(prices, account["provider"], mark)
                    result = (db.execute(select + "(venue,symbol,currency)=(?,?,?)", instrument).fetchone()
                              if instrument and instrument[0] in ("KRX", "AMEX", "NASDAQ", "NYSE") else None)
                    record = json.loads(result[2]) if result else {}
                    label = (states[record["state"]] + " · " + verification("primary",result[0],result[1])
                             if result else "이번 표본 밖 · 식별 또는 이력 확인")
                    alternative = recovered_stock(instrument[0], instrument[1]) if result else None
                    if alternative:
                        label += " · 별도 참고 이력 있음"
                    period = str(record["period"]) + "일" if record.get("period") else "—"
                    out.append(f'<tr><td><a href="?position={escape(pid)}#market-sma">{escape(mark["symbol"])}</a>'
                               f'</td><td>{label}</td><td>{period}</td></tr>')
            out.append('</table></details>')
        if symbol:
            hits = db.execute(select + "symbol=? ORDER BY venue", (symbol,)).fetchall()
        elif key:
            hits = db.execute(select + "(venue,symbol,currency)=(?,?,?)", key).fetchall()
        else:
            hits = []
    for venue, code, payload in hits:
        record = json.loads(payload)
        score = record["score"]
        out.append(f'<h3>{escape(code)} · {escape(venue)}</h3><p>{states[record["state"]]} · {verification("primary",venue,code)}</p>')
        if score:
            out.append(f'<p>학습에서 고른 선 {record["period"]}일 · 비용 후 단순 보유 대비 '
                       f'{score["excess"] * 100:+.2f}%p · 최대낙폭 {score["mdd"] * 100:.2f}% · '
                       f'평가 구간 청산 {score["exits"]}회</p>')
        if record["reasons"]:
            out.append('<small>' + escape(" · ".join(record["reasons"])) + '</small>')
        alternative = recovered_stock(venue, code)
        if alternative:
            out.append(f'<p>거래장 미확정 참고 이력 · {states[alternative["state"]]} · {verification("recovery",venue,code)}')
            if alternative["score"]:
                out.append(f' · {alternative["period"]}일선 · 마지막 63일 단순 보유 대비 '
                           f'{alternative["score"]["excess"] * 100:+.2f}%p')
            out.append('</p>')
        gap_path = path.with_name(stamp + "-gap.sqlite3")
        if supplemental and venue == "KRX" and gap_path.is_file() and not gap_path.is_symlink():
            with closing(sqlite3.connect(gap_path.resolve().as_uri() + "?mode=ro", uri=True)) as alt:
                row = alt.execute("SELECT detail FROM result WHERE venue=? AND symbol=?", (venue, code)).fetchone()
            if row:
                gap = json.loads(row[0])
                out.append(f'<p>결측일 보완 실험 · {states[gap["state"]]} · {verification("gap",venue,code)}')
                if gap["score"]:
                    out.append(f' · {gap["period"]}일선 · 단순 보유 대비 {gap["score"]["excess"] * 100:+.2f}%p')
                out.append('</p>')
    if (key or symbol) and not hits:
        out.append('<p>해당 종목은 이번 시장 검증 표본에서 확인되지 않았습니다.</p>')
    return "".join(out) + "</section>"


def regular_close_conflict(package, key, last):
    index = intelligence.private_json(package, "equity_screen_index.json", {}) if package else {}
    stamp = index.get("run", "")
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}", stamp):
        return False
    path = package / ".local" / "equity_screens" / (stamp + "-validation.sqlite3")
    if not path.is_file() or path.is_symlink():
        return False
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='quote'").fetchone():
            return False
        quote = db.execute("SELECT closing FROM quote WHERE (venue,symbol,currency,day)=(?,?,?,?)",
                           (*key, last["day"])).fetchone()
    if quote is None or not last["closing"]:
        return False
    value = Decimal(last["closing"])
    tolerance = Decimal(0) if key[0] == "KRX" else Decimal(".005" if value >= 1 else ".00005")
    return abs(value - Decimal(quote[0])) > tolerance


def render(directory, package, base, query, css):
    accounts = portfolio_accounts(
        directory, package, quote_book=live_valuation.read(package)
    )
    choices = {
        intelligence.position_id(
            a["provider"], a["account"], m["symbol"], m["currency"]
        ): (a, m)
        for a in accounts
        for m in a["marks"]
        if history_panel.eligible(a["provider"], m)
    }
    out = [
        '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>퀀트 연구</title><style>',
        css,
        ".heat{display:grid;grid-template-columns:repeat(auto-fit,minmax(66px,1fr));gap:4px}.heat a{padding:6px;color:#132738;text-align:center}.heat small,svg{display:block}.heat [aria-current=true]{outline:2px solid #173750}svg{width:100%}section{overflow:auto}</style>",
        chat_page.navigation(base, "quant"),
        "<main><h1>퀀트 연구</h1>",
    ]
    pid = query.get("position", next(iter(choices), None))
    out.append('<form><label>보유 종목 <select name="position">')
    for k, (a, m) in choices.items():
        label = escape(f"{m['symbol']} · {a['account']} · {m['currency']}")
        out.append(
            f'<option value="{k}" {"selected" if k == pid else ""}>{label}</option>'
        )
    out.append("</select></label> <button>조회</button></form>")
    rows, source, key = [], None, None
    sessions = set()
    sources = 0
    if pid in choices:
        a, m = choices[pid]
        with live_valuation.connection(package) as db:
            if (
                db
                and db.execute(
                    "SELECT 1 FROM sqlite_master WHERE name='price_bar'"
                ).fetchone()
            ):
                key = price_history.local_history_key(db, a["provider"], m)
                if key and key[0] in VENUES:
                    sessions = price_history.known_sessions(db, key[0])
                    rows, source, sources = history_for_research(db, key, sessions)
    out.append(market_screen_panel(package, key, query.get("screen_symbol", ""), choices))
    if key:
        from .strategy_page import selected_panel
        out.append(selected_panel(package,key))
    if rows:
        bars, r, digest = experiment(package, key, source, rows, sessions)
        if regular_close_conflict(package, key, rows[-1]):
            r = dict(r, selected=False, reasons=[*r["reasons"], "당일 정규장 종가가 독립 시세와 불일치"])
        raw = query.get("period", "")
        n = int(raw) if raw.isascii() and raw.isdigit() and len(raw) <= 3 else None
        out.append(
            f"<p>{escape(key[0])} · {escape(key[2])} · 완료 일봉 {rows[0]['day']} ~ {rows[-1]['day']} · {len(rows)}봉 · 정정 {sum(row['revisions'] for row in rows)}회 · 분석 구간 시가 누락 {sum(not b['open'] for b in bars)}봉</p>"
            f"<p>원천 {sources}개 중 검증 가능 여부와 연속 학습 기간으로 고른 단일 이력 · {escape(source)}</p>"
        )
        out.append(report(base, pid, n, bars, r, key, digest))
    else:
        reason = (
            "보유 종목을 선택하세요."
            if pid not in choices
            else "시장·통화와 일치하는 완료 일봉 원천을 기다리고 있습니다."
        )
        out.append(
            f"<section><h2>선정 보류</h2><p>{reason} 전체 검증에는 최소 {quant.MIN_ROWS}봉이 필요합니다.</p></section>"
        )
    return ("".join(out) + "</main></html>").encode()
