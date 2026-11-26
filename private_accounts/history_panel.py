"""Private dashboard views for real workbook positions and completed price sessions."""

from datetime import date
from html import escape
from urllib.parse import urlencode

from agents import intelligence
from agents.equities.daily_bars import BSTOCKS, VENUES
from . import live_panel, live_valuation, price_history, store

MODES = {"day": "일봉", "week": "주봉", "month": "월봉", "ma": "120일선", "year": "1년"}


def chart(rows, mode, missing=()):
    points = price_history.aggregate(rows, mode)
    ma = price_history.moving_average(rows, missing) if mode == "ma" else {}
    if mode in ("ma", "year"):
        end = date.fromisoformat(points[-1]["day"])
        points = [p for p in points if (end - date.fromisoformat(p["day"])).days <= 366]
    else:
        points = points[-{"day": 35, "week": 26, "month": 24}[mode] :]
    values = [p["closing"] for p in points] + [
        ma[p["day"]] for p in points if p["day"] in ma
    ]
    lo, hi = min(values), max(values)

    def xy(i, v):
        return f"{8 + 684 * i / max(1, len(points) - 1):.2f},{100 - 86 * float((v - lo) / (hi - lo)) if hi > lo else 57:.2f}"

    line = " ".join(xy(i, p["closing"]) for i, p in enumerate(points))
    avg = " ".join(xy(i, ma[p["day"]]) for i, p in enumerate(points) if p["day"] in ma)
    legend = '<span class="average-key">120거래일 단순이동평균</span>' if avg else ""
    svg = (
        '<svg viewBox="0 0 700 115" preserveAspectRatio="none" role="img" aria-label="완료 거래일 종가 추이">'
        '<path d="M0 15H700 M0 57H700 M0 100H700" stroke="#dde4ee" fill="none" stroke-dasharray="3 6"/>'
        f'<polyline points="{line}" fill="none" stroke="#3155b3" stroke-width="2.7" vector-effect="non-scaling-stroke"/>'
    )
    if len(points) == 1:
        svg += '<circle cx="8" cy="57" r="3" fill="#3155b3"/>'
    if avg:
        svg += f'<polyline points="{avg}" fill="none" stroke="#ad6417" stroke-width="2" vector-effect="non-scaling-stroke"/>'
    return (
        '<div class="history-key">종가 '
        + legend
        + f'<span class="chart-scale">표시 범위 {live_panel.fmt(lo)} – {live_panel.fmt(hi)}</span></div><div class="history-plot">'
        + svg
        + "</svg></div>"
        f'<div class="history-axis"><span>{points[0]["first"]}</span><span>{points[-1]["day"]}</span></div>'
    ), points


def eligible(provider, mark):
    key = mark.get("instrument")
    return bool(
        provider == "binance" and mark.get("symbol", "").strip().upper() in BSTOCKS
        or key and key[0] in VENUES
        or any(t.startswith("token:XT:") for t in mark.get("direct_ids", ()))
        or provider in store.BROKERS
        and mark["symbol"].upper() != mark["currency"]
    )


def position_history(
    package, accounts, base, pid=None, mode="day", *, manager=False, screen="all"
):
    mode = mode if mode in MODES else "day"
    rows_by_id = {}
    for a in accounts:
        for m in a["marks"]:
            if not eligible(a["provider"], m):
                continue
            row_id = intelligence.position_id(
                a["provider"], a["account"], m["symbol"], m["currency"]
            )
            rows_by_id[row_id] = (a, m)
    target = base + ("/desk/manager" if manager else "/portfolio")
    query = {"screen": screen} if manager else {}
    rows, source, state = [], None, None
    long_rows, long_source = [], None
    last_close = last_open = None
    sessions = set()
    with live_valuation.connection(package) as db:
        ready = (
            db is not None
            and db.execute(
                "SELECT 1 FROM sqlite_master WHERE name='price_bar'"
            ).fetchone()
        )
        if pid not in rows_by_id:
            pid = None
            for k, (account, m) in rows_by_id.items():
                identity = (
                    price_history.local_history_key(db, account["provider"], m)
                    if ready
                    else None
                )
                if (
                    identity
                    and ready
                    and db.execute(
                        "SELECT 1 FROM price_bar WHERE venue=? AND symbol=? AND currency=? LIMIT 1",
                        identity,
                    ).fetchone()
                ):
                    pid = k
                    break
            pid = pid or next(iter(rows_by_id), None)
        chosen = rows_by_id.get(pid)
        key = (
            price_history.local_history_key(db, chosen[0]["provider"], chosen[1])
            if chosen and ready
            else None
        )
        if ready and key:
            sessions = price_history.known_sessions(db, key[0])
            rows, source = price_history.series(db, key)
            long_rows, long_source = price_history.series(db, key, long=True)
            if mode in ("ma", "year", "month"):
                rows, source = long_rows, long_source
            if db.execute(
                "SELECT 1 FROM sqlite_master WHERE name='session_close'"
            ).fetchone():
                last_close = db.execute(
                    "SELECT * FROM session_close WHERE (venue,symbol,currency)=(?,?,?) AND "
                    + price_history.REGULAR_CLOSE + " ORDER BY day DESC LIMIT 1",
                    key,
                ).fetchone()
            if db.execute(
                "SELECT 1 FROM sqlite_master WHERE name='session_open'"
            ).fetchone():
                last_open = db.execute(
                    "SELECT * FROM session_open WHERE (venue,symbol,currency)=(?,?,?) AND "
                    "(venue!='KRX' OR source NOT LIKE 'https://m.stock.naver.com/api/stocks/marketValue/%') "
                    "ORDER BY day DESC,source_at DESC LIMIT 1",
                    key,
                ).fetchone()
            state = db.execute(
                "SELECT status,success FROM bar_job WHERE venue=? AND symbol=? AND currency=?",
                key,
            ).fetchone()
    out = [
        '<section class="price-history" id="price-history" data-watch><div class="history-top"><div>'
        "<h2>종목별 가격 이력</h2></div>"
    ]
    if not chosen:
        return (
            "".join(out)
            + "</div><p>분석할 주식 계좌 원장을 기다리고 있습니다.</p></section>"
        )
    name = escape(chosen[1]["symbol"])
    out.append(
        f'<form class="history-select" action="{escape(target)}#price-history" method="get">'
        f'<input type="hidden" name="frame" value="{mode}">'
    )
    if manager:
        out.append(f'<input type="hidden" name="screen" value="{escape(screen)}">')
    out.append('<label>보유 종목 <select name="position">')
    for k, (a, m) in rows_by_id.items():
        selected = " selected" if k == pid else ""
        label = f"{m['symbol']} · {store.PROVIDERS[a['provider']]} · {a['account']} · {m['currency']}"
        out.append(f'<option value="{k}"{selected}>{escape(label)}</option>')
    out.append(
        '</select></label><button type="submit">조회</button></form></div><div class="history-controls">'
        f'<strong>{name}</strong><nav aria-label="가격 집계 기간">'
    )
    for k, label in MODES.items():
        params = urlencode(dict(query, position=pid, frame=k))
        out.append(
            f'<a href="{escape(target + "?" + params)}#price-history" aria-current="{"page" if k == mode else "false"}">{label}</a>'
        )
    out.append(f'<a href="{escape(base)}/quant?position={pid}">퀀트 연구</a></nav></div>')
    if last_open and (not rows or last_open["day"] > rows[-1]["day"]):
        out.append(
            f'<p class="close-observation">{last_open["day"]} 시장 시가 <b>{live_panel.fmt(last_open["opening"])} {escape(key[2])}</b> · '
            f'<a href="{escape(last_open["source"])}" rel="noreferrer">원문</a> · {live_panel.time(last_open["source_at"])}</p>'
        )
    if last_close and (not rows or last_close["day"] > rows[-1]["day"]):
        out.append(
            f'<p class="close-observation">시장 마감 시세 <b>{live_panel.fmt(last_close["closing"])} {escape(key[2])}</b> · '
            f"{last_close['day']} · 완료 일봉 원문 대조 중</p>"
        )
    if rows:
        missing = {
            d for d in sessions if rows[0]["day"] <= d <= rows[-1]["day"]
        }.difference(r["day"] for r in rows)
        long_missing = sessions.difference(r["day"] for r in long_rows)
        stats = price_history.summaries(rows, missing)
        long_stats = price_history.summaries(long_rows, long_missing)
        plot, points = chart(rows, mode, missing)
        if missing:
            out.append(
                f"<small>같은 시장의 거래가 확인된 날 중 {len(missing)}일 결측 · 해당 이동평균 보류</small>"
            )
        out.append(
            f'<div class="last-candle"><b>{live_panel.fmt(rows[-1]["closing"])} {escape(key[2])}</b> 종가 · 시가 {live_panel.fmt(rows[-1]["opening"])}</div>'
            f"<small>{escape(key[2])} · 마지막 완료 일봉 {rows[-1]['day']} · 원천 종가 기준</small>"
        )
        out.append('<div class="history-stats">')
        for label, id_ in [
            ("전 거래일", "day"),
            ("1주", "week"),
            ("1개월", "month"),
            ("120일 평균", "ma"),
            ("1년", "year"),
        ]:
            older = id_ in ("year", "ma") and long_source != source
            val = long_stats[id_] if older else stats[id_]
            value = (
                "자료 부족"
                if val is None
                else live_panel.fmt(val)
                if id_ == "ma"
                else live_panel.signed(val) + "%"
            )
            out.append(
                f"<div><small>{label}</small><b>{value}</b>"
                + (
                    f'<small><a href="{escape(long_source)}" rel="noreferrer">{long_rows[-1]["day"]} 기준</a></small>'
                    if older
                    else ""
                )
                + "</div>"
            )
        out.append("</div>" + plot)
        out.append(
            f'<details><summary>{MODES[mode]} 시가·종가 표</summary><div class="comparison"><table>'
            "<tr><th>첫 관측 거래일</th><th>마지막 관측 거래일</th><th>시가</th><th>종가</th></tr>"
        )
        for p in reversed(points):
            out.append(
                f"<tr><td>{p['first']}</td><td>{p['day']}</td><td>{live_panel.fmt(p['opening'])}</td><td>{live_panel.fmt(p['closing'])}</td></tr>"
            )
        out.append(
            "</table></div></details>"
            f'<small><a rel="noreferrer" target="_blank" href="{escape(source)}">가격 원문</a> · {len(rows)}개 일봉 · '
            "현지 거래일 기준 · 배당·수수료·환율 제외 · 주봉과 월봉은 확보된 일봉 범위</small>"
        )
    else:
        reason = (
            "종목 식별 대기"
            if not key
            else (
                state["status"]
                if state and state["status"]
                else "공개 상장목록 수집 순서 대기"
            )
        )
        link = (
            f'<a href="{escape(base)}/portfolio?position={pid}#position">종목 식별자 확인</a>'
            if not key
            else ""
        )
        out.append(
            f'<div class="history-empty"><b>{escape(reason)}</b><p>거래소와 종목이 일치하는 완료 일봉을 확보하면 차트가 표시됩니다.</p>{link}</div>'
        )
    if state and state["status"] and state["status"] != "수집 완료":
        out.append(
            f"<small>자동 일봉 · {escape(state['status'])} · 마지막 성공 {live_panel.time(state['success'])}</small>"
        )
    with live_valuation.connection(package, account_history=True) as db:
        if db is not None:
            marks = list(
                db.execute(
                    "SELECT * FROM mark_day WHERE pid=? ORDER BY day DESC LIMIT 366",
                    (pid,),
                )
            )
            if marks:
                out.append(
                    '<details><summary>계좌 일별 평가 기록</summary><div class="comparison"><table><tr>'
                    "<th>기록일 KST</th><th>수량</th><th>평가액</th><th>평가손익</th><th>평가 근거</th><th>시세 시각</th></tr>"
                )
                for r in marks:
                    out.append(
                        f"<tr><td>{r['day']}</td><td>{live_panel.fmt(r['quantity'])}</td><td>{live_panel.fmt(r['valuation'])}</td>"
                        f"<td>{live_panel.fmt(r['gain'])}</td><td>{escape(r['state'])}</td><td>{live_panel.time(r['source_at'])}</td></tr>"
                    )
                out.append(
                    "</table></div><small>그날 마지막으로 실제 관측한 계좌 평가 · "
                    + escape(chosen[1]["currency"])
                    + "</small></details>"
                )
    return "".join(out) + "</section>"
