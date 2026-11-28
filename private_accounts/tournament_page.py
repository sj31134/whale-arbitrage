"""Authenticated Knockout Tournament Arena & Executive Champion Summary View."""

from html import escape

from . import chat_page, tournament

e = escape


def _card(title, badge, headline, body, detail_link=None):
    link = f'<p style="margin:.45rem 0 0"><a href="{e(detail_link)}">토너먼트 대진표·탈락 사유 확인 ↗</a></p>' if detail_link else ""
    return (
        '<article class="era-card">'
        f'<div class="spread"><strong>{e(title)}</strong><span class="badge-pass">{e(badge)}</span></div>'
        f'<div style="font-size:1.05rem;font-weight:750;margin:.35rem 0;color:#0e3a32">{e(headline)}</div>'
        f'<p style="margin:0;font-size:.88rem;color:#354a4f">{e(body)}</p>'
        f'{link}</article>'
    )


def champion_banner(package, base):
    """Compact 3-champion executive banner embedded at top of ★ 종합 상황판."""
    board = tournament.read(package)
    if not board:
        board = tournament.run_tournament(package)
    st = board["stocks"]
    sg = board["strategies"]
    pt = board["patterns"]
    sc = st["champion"]
    return (
        '<section id="tournament-champions" style="background:#f4fbf8;border:2px solid #0b5d46;border-radius:12px;padding:1rem;margin:1rem 0">'
        '<div class="spread">'
        '<div><h2 style="margin:0">🏆 누적 토너먼트 최종 우승 챔피언 (한눈에 보기)</h2>'
        f'<small>갱신 {e(board["updated"])} · 배틀 ID <code>{e(board["battle_id"])}</code> · '
        f'현재 레짐: <b>{e(board["regime"]["label"])}</b></small></div>'
        f'<a class="desk-link" href="{e(base)}/tournament"><b>전체 대진표·배틀 로그 열기 ↗</b></a>'
        '</div>'
        '<div class="era-grid" style="margin-top:.75rem">'
        + _card(
            f'① 최종 우승 종목 ({st["pool_count"]}개 배틀)',
            f'비중 {sc["recommended_pct"]:.1f}% · 현금 {sc["cash_reserve_pct"]:.1f}%',
            f'{sc["name"]} ({sc["symbol"]})',
            sc["summary"],
        )
        + _card(
            f'② 최종 우승 전략 ({sg["pool_count"]}개 배틀)',
            f'점수 {sg["champion"]["score"]:.0f}',
            sg["champion"]["name"],
            f'전환 조건: {sg["champion"]["handover_condition"]}',
        )
        + _card(
            f'③ 최종 승리 패턴 ({pt["pool_count"]}건 오답 통합)',
            f'점수 {pt["champion"]["score"]:.0f}',
            pt["champion"]["name"],
            pt["champion"]["rule"],
        )
        + '</div></section>'
    )


def _match_table(matches):
    rows = []
    for m in matches:
        win_a = m["winner"] in m["a"] or m["score_a"] >= m["score_b"]
        a_txt = f'<b>🏆 {e(m["a"])}</b>' if win_a else e(m["a"])
        b_txt = f'<b>🏆 {e(m["b"])}</b>' if not win_a else e(m["b"])
        rows.append(
            f'<tr><td><span class="badge-info">{e(m["round"])}</span></td>'
            f'<td>{a_txt} <small>({m["score_a"]:.1f})</small></td>'
            f'<td>vs</td>'
            f'<td>{b_txt} <small>({m["score_b"]:.1f})</small></td>'
            f'<td>{e(m["reason"])}</td></tr>'
        )
    return (
        '<div class="comparison"><table><thead><tr>'
        '<th>라운드</th><th>대진 A</th><th></th><th>대진 B</th><th>판정 근거</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


def render(package, base, csrf, query, css):
    q = query or {}
    board = tournament.read(package)
    if not board:
        board = tournament.run_tournament(package)
    logs = tournament.history(package)

    done_banner = ""
    if q.get("done") == "battled":
        done_banner = '<p class="badge-pass" style="padding:8px 12px;display:inline-block">전체 종목·전략·패턴 토너먼트 재배틀 및 로그 기록을 완료했습니다.</p>'

    st = board["stocks"]
    sg = board["strategies"]
    pt = board["patterns"]
    sc = st["champion"]

    elim_rows = "".join(
        f'<tr><td><code>{e(x["symbol"])}</code></td><td><b>{e(x["name"])}</b></td>'
        f'<td>{e(x["league"])}</td><td>{e(x["reason"])}</td></tr>'
        for x in st["eliminated_sample"]
    )
    log_rows = "".join(
        f'<tr><td>{e(r["updated"])}</td><td><code>{e(r["battle_id"])}</code></td>'
        f'<td>{e(r["regime"])}</td><td><b>{e(r["champion_stock"])}</b></td>'
        f'<td>{e(r["champion_strategy"])}</td><td>{e(r["champion_pattern"])}</td></tr>'
        for r in logs[:25]
    )

    body = [
        '<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta name="referrer" content="no-referrer"><title>최종 우승 토너먼트 · Whale Tracking</title><style>',
        css,
        '.spread{display:flex;justify-content:space-between;align-items:center;gap:.8rem;flex-wrap:wrap}'
        '.era-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;margin:12px 0}'
        '.era-card{background:white;border:1px solid #cbd7d5;border-radius:10px;padding:14px}'
        '.badge-pass{background:#e4f6ee;color:#0b5d46;padding:2px 8px;border-radius:999px;font-size:.8rem;font-weight:700}'
        '.badge-info{background:#e7f0fb;color:#17477a;padding:2px 8px;border-radius:999px;font-size:.8rem;font-weight:650}',
        '</style><header><div><strong>Whale Tracking</strong><small>로컬 투자 관리 · 누적 토너먼트 결승</small></div></header><main>',
        chat_page.navigation(base, "tournament"),
        '<div class="spread" style="margin-top:1rem"><div><h1 style="margin:0">🏆 누적 종목·전략·패턴 토너먼트 결승실</h1>'
        f'<small>수십 개 종목·백테스트·오답 패턴은 모두 로그에 남기고, 배틀에서 살아남은 <b>단 하나의 최종 챔피언만</b> 제시합니다 · 갱신 {e(board["updated"])}</small></div>'
        f'<form method="post" action="{e(base)}/desk/manager/tournament-run"><input type="hidden" name="csrf" value="{e(csrf)}">'
        '<button type="submit">토너먼트 재배틀 실행</button></form></div>',
        done_banner,
        champion_banner(package, base),
        '<section id="stock-bracket"><h2>1. 종목 토너먼트 대진표 (누적 ' + str(st["pool_count"]) + '종목 → 최종 1챔피언)</h2>'
        f'<p>역발상 완전 통과주 <b>{st["contrarian_pass_count"]}건</b> · 최종 우승 <b>{e(sc["name"])} ({e(sc["symbol"])})</b> · '
        f'차선 준우승: <b>{e(st["runner_up"])}</b> · 코어 트랙 우승: <b>{e(st["core_champion"])}</b> · '
        f'국내 대기(눌림/손익비): {e(st["kr_watchlist"])}</p>'
        + _match_table(st["matches"])
        + f'<details><summary>1라운드 탈락 후보 {st["eliminated_count"]}건 탈락 사유 보기 (로그 보존)</summary>'
        '<div class="comparison"><table><thead><tr><th>티커</th><th>종목명</th><th>트랙</th><th>1라운드 탈락 사유</th></tr></thead>'
        f'<tbody>{elim_rows}</tbody></table></div></details></section>',
        '<section id="strategy-bracket"><h2>2. 전략 토너먼트 대진표 (31년 백테스트 · /quant 워크포워드 '
        f'{sg["quant_stats"]["selected"]}/{sg["quant_stats"]["total"]} 통과 반영)</h2>'
        + _match_table(sg["matches"]) + '</section>',
        '<section id="pattern-bracket"><h2>3. 실행 패턴 토너먼트 대진표 (누적 오답노트 ' + str(pt["pool_count"]) + '건 통합)</h2>'
        + _match_table(pt["matches"]) + '</section>',
        f'<details><summary>과거 토너먼트 배틀 로그 이력 ({len(logs)}회 누적 보존)</summary>'
        '<div class="comparison"><table><thead><tr><th>시각</th><th>배틀 ID</th><th>국면</th><th>우승 종목</th><th>우승 전략</th><th>승리 패턴</th></tr></thead>'
        f'<tbody>{log_rows or "<tr><td colspan=6>초회 실행 기록이 저장되었습니다.</td></tr>"}</tbody></table></div></details>',
        '</main></html>',
    ]
    return "".join(body).encode()
