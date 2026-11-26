"""Authenticated research controls and locally evaluated instrument comparisons."""

from datetime import datetime, timezone
from html import escape
import sqlite3

from . import chat_page, quant, strategy_registry as registry
from .strategy_catalog import AQR, CATALOG, SOURCE_LABELS, WINTON


def pct(n, suffix="%"):
    return f"{100*n:+.2f}{suffix}"


def kst(stamp):
    from agents import intelligence

    return (
        datetime.fromisoformat(stamp)
        .astimezone(intelligence.KST)
        .strftime("%Y-%m-%d %H:%M")
    )


def form(base, csrf, action, fields, label):
    hidden = dict(csrf=csrf, **fields)
    inputs = "".join(
        f'<input type="hidden" name="{escape(k)}" value="{escape(v)}">'
        for k, v in hidden.items()
    )
    return f'<form method="post" action="{escape(base)}/desk/manager/{action}">{inputs}<button>{escape(label)}</button></form>'


def selected_panel(package, key):
    if not key or key[0] not in ("KRX", "AMEX", "NYSE", "NASDAQ"):
        return ""
    head = "<section><h2>선택 종목의 공개 전략 검토</h2>"
    try:
        _, meta, groups = registry.read_panel(package, tuple(key))
        selected = next((r for group in groups.values() for r in group), None)
        if not selected:
            return (
                head + "<p>검증된 공개 주식 표본에 해당 종목이 없습니다.</p></section>"
            )
        market = "KR" if key[0] == "KRX" else "US"
        lines = [
            head,
            f'<p>{escape(meta["days"][market])} 마감 · 최근 63거래일 · 같은 종목 단순 보유 대비</p><ul>',
        ]
        with registry.database(package) as db:
            for name in registry.PRICE_IDS:
                reason = registry.hold_reason(selected, name)
                if registry.current_state(db, name) == "일시정지":
                    value = "연구 일시정지"
                elif reason:
                    value = reason
                else:
                    bars = selected["bars"]
                    cost = quant.costs(key[0])
                    trial = registry.simulate(bars, name, cost, 1)
                    hold = registry.simulate(bars, "hold", cost, 1)
                    value = (
                        pct(trial["net"] - hold["net"], "%p")
                        + " · 최대낙폭 "
                        + pct(trial["dd"])
                    )
                lines.append(
                    f'<li>{escape(CATALOG[name]["title"])} · {escape(value)}</li>'
                )
            for name in ("berkshire", "household"):
                if (
                    registry.current_state(db, name) == "연구 중"
                    and key[1] in registry.evidence(db, name, meta["cutoff"])["items"]
                ):
                    lines.append(
                        f'<li>{escape(CATALOG[name]["title"])} · 가격 입력 기준시각까지 확인된 공개 표본과 일치</li>'
                    )
        return "".join(lines) + "</ul></section>"
    except (ValueError, OSError, sqlite3.Error):
        return head + "<p>공개 원천 또는 독립 종가 대조를 기다립니다.</p></section>"


def render(package, base, csrf, css):
    now = datetime.now(timezone.utc).isoformat()
    html = [
        '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta name="referrer" content="no-referrer"><title>전략 관리</title><style>',
        css,
        ".strategy-row{display:flex;align-items:center;justify-content:space-between;gap:1em;flex-wrap:wrap}"
        ".strategy-list details{padding:12px 0;border-bottom:1px solid #ccd5d9}.strategy-list summary{cursor:pointer}"
        ".strategy-scroll{overflow:auto}.strategy-scroll table{white-space:nowrap}.strategy-list p{max-width:82ch}</style><main>",
        chat_page.navigation(base, "strategies"),
        '<header class="strategy-row"><h1>전략 관리</h1>',
        form(base, csrf, "strategy-run", {}, "공개 일봉으로 재계산"),
        "</header>",
    ]
    with registry.database(package) as db:
        refresh = db.execute(
            "SELECT attempted,status FROM refresh_status WHERE id=1"
        ).fetchone()
        cohort = db.execute(
            "SELECT registered FROM cohort WHERE rule='public-stock-sample-v1'"
        ).fetchone()
        if cohort:
            html.append(
                f"<small>공개 표본 고정 {kst(cohort[0])} KST · 이후 누락 종목도 분모에 유지</small>"
            )
        if refresh:
            html.append(
                f'<p>최근 점검 {kst(refresh["attempted"])} KST · {escape(refresh["status"])}</p>'
            )
        html.append(
            "<section><h2>최근 63거래일 연구 결과</h2><p>시장당 32개 공개 종목 표본. 종목별 비용 차감 수익률과 최대낙폭의 중앙값입니다. 초과수익은 같은 종목을 같은 기간 보유했을 때와 비교했습니다.</p>"
        )
        html.append(
            '<div class="strategy-scroll"><table><thead><tr><th>시장 · 마감</th><th>규칙</th><th>계산 / 표본</th><th>순수익</th><th>초과수익</th><th>비용 2배 초과</th><th>최대낙폭</th></tr></thead><tbody>'
        )
        history = {k: registry.summary(db, k) for k in registry.PRICE_IDS}
        for market in ("KR", "US"):
            for key, runs in history.items():
                result = next(
                    (
                        r["result"]
                        for r in runs
                        if r["result"]["version"] == CATALOG[key]["version"]
                    ),
                    None,
                )
                if not result:
                    continue
                row = result["markets"][market]
                metrics = row["summary"]
                cells = [
                    market + " · " + result["days"][market],
                    CATALOG[key]["title"],
                    f'{row["n"]} / {row["sampled"]}',
                ]
                cells += [
                    (
                        pct(metrics[k], "%p" if k in ("excess", "stress") else "%")
                        if metrics
                        else "보류"
                    )
                    for k in ("net", "excess", "stress", "dd")
                ]
                html.append(
                    "<tr>"
                    + "".join("<td>" + escape(c) + "</td>" for c in cells)
                    + "</tr>"
                )
        html.append(
            "</tbody></table></div><small>현지통화 가격 기준 · 배당·현금이자·환전 제외 · 다음 시가 체결 가정 · 시장 간 합산 없음</small></section>"
        )
        html.append(
            "<details><summary>운용사가 공표한 펀드 표본 성과</summary>"
            "<p>2026년 10월 30일 미국 달러 총수익률. AQR AQMIX는 연초 이후 +14.52%, 10월 −3.69%, "
            "Winton Class I는 각각 +12.52%, −2.09%였다. 두 운용사의 3개월 미국 국고단기채 비교지수는 "
            "같은 기간 +3.01%, +0.35%였다. 위 주식 실험은 현금과 주식만 사용한다.</p>"
            f'<p><a href="{AQR}" rel="noreferrer">AQR 공표표</a> · <a href="{WINTON}" rel="noreferrer">Winton 공표표</a></p></details>'
        )
        for kind, label in (
            ("price", "가격 규칙"),
            ("event", "인물·기관 공시"),
            ("existing", "기존 분석 엔진"),
        ):
            html.append(f'<section class="strategy-list"><h2>{label}</h2>')
            for key, entry in CATALOG.items():
                if entry["kind"] != kind:
                    continue
                state = registry.current_state(db, key)
                title = entry["title"]
                html.append(
                    f'<details><summary><strong>{escape(title)}</strong> · {escape(entry["version"])} · '
                    + ("연결됨" if kind == "existing" else state)
                    + "</summary>"
                )
                html.extend(
                    "<p>" + escape(entry[k]) + "</p>"
                    for k in ("rule", "downside", "revisit")
                )
                links = [
                    f'<a href="{escape(u)}" rel="noreferrer noopener" target="_blank">{escape(SOURCE_LABELS[u])}</a>'
                    for u in entry["sources"]
                ]
                if links:
                    html.append("<p>" + " · ".join(links) + "</p>")
                if kind == "price":
                    for run in history[key]:
                        result = run["result"]
                        reasons = [
                            f"{m} {why} {n}개"
                            for m, g in result["markets"].items()
                            for why, n in g["held"].items()
                        ]
                        html.append(
                            f'<p><code>{run["id"][:12]}</code> · v{escape(result["version"])} · 입력 {kst(result["cutoff"])} KST · '
                            + escape(", ".join(reasons) or "전 표본 계산")
                            + "</p>"
                        )
                if kind == "event":
                    ev = registry.evidence(db, key, now)
                    html.append(
                        "<p>확인된 표본 · "
                        + escape(", ".join(ev["items"]) or "자료 대기")
                        + "</p>"
                    )
                    for r in ev["records"][-4:]:
                        html.append(
                            f'<small>기준일 {r["effective"]} · 사용 가능 {kst(r["available"])} KST · '
                            f'<a href="{escape(r["url"])}" target="_blank" rel="noreferrer noopener">공시·발표 원문</a></small><br>'
                        )
                if kind != "existing":
                    new = "일시정지" if state == "연구 중" else "연구 중"
                    html.append(
                        form(
                            base,
                            csrf,
                            "strategy-state",
                            dict(strategy=key, state=new),
                            "연구 일시정지" if state == "연구 중" else "연구 재개",
                        )
                    )
                elif key == "sma":
                    html.append(
                        f'<p><a href="{escape(base)}/quant">퀀트 연구 열기</a></p>'
                    )
                html.append("</details>")
            html.append("</section>")
    html.append("</main></html>")
    return "".join(html).encode()
