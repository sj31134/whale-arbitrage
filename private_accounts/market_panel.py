"""Render the daily public market brief and the local-only matching ledger."""
import hashlib
from datetime import datetime
from html import escape
from urllib.parse import urlsplit

from agents import intelligence as intel
from . import market_review

VIEWS = {"all":"전체", "KR":"국내", "US":"미국", "XT":"토큰화 주식"}
MARKET = {"KR":"국내", "US":"미국", "XT":"토큰화 주식"}


def e(value):
    return escape(str(value), quote=True)


def when(stamp):
    return datetime.fromisoformat(stamp).astimezone(intel.KST).strftime("%m.%d %H:%M KST") if stamp else "기록 없음"


def link(url):
    return f'<a href="{e(url)}" target="_blank" rel="noreferrer noopener">{e(urlsplit(url).hostname)} ↗</a>'


def signed(value):
    return f"{value:+.2f}%"


def details(row):
    fields = [("판정",row.get("evidence","원인 미확인")),("이슈",row.get("issue")),("수급",row.get("flow")),
              ("추세",row.get("trend")),("연구 의견",row.get("insight")),("재검토",row.get("revisit"))]
    for key, label, unit in (("range_pct","장중 범위","%"),("five_day_pct","5거래일","%"),
                             ("z","직전 20일 대비","σ"),("volume_multiple","거래량 / 직전 20일 중앙값","배")):
        if key in row:
            fields.append((label,f"{row[key]:g}{unit}"))
    items = "".join(f"<dt>{e(k)}</dt><dd>{e(v)}</dd>" for k,v in fields if v)
    refs = dict.fromkeys([row["source"],*row.get("refs",[])])
    return '<dl class="signal-facts">'+items+'</dl><p class="signal-refs">'+" · ".join(link(u) for u in refs)+'</p>'


def movement(group):
    rows = group["leaders"]
    out = [f'<section class="signal-board"><div class="signal-head"><h3>{MARKET[group["market"]]} · {e(group["kind"])}</h3>'
           f'<small>{e(group["basis"])} · 표본 {group["coverage"]:,} · 기준 통과 {group["flagged"]:,}</small></div>']
    if not rows:
        return out[0] + '<p class="quiet-state">이 표본에서 선별 기준을 넘은 종목이 없습니다.</p></section>'
    scale = max(abs(r["change_pct"]) for r in rows) or 1
    for r in rows:
        size = min(50,abs(r["change_pct"])/scale*50)
        side = "up" if r["change_pct"] >= 0 else "down"
        out.append(f'<details class="signal-row"><summary><span class="signal-name">{e(r["name"])}'
                   f'<small>{e(r["symbol"])}</small></span><span class="signal-track {side}" aria-hidden="true">'
                   f'<i style="width:{size:.2f}%"></i></span><b class="signal-num {side}">{signed(r["change_pct"])}</b>'
                   f'<span class="disclose" aria-hidden="true">⌄</span></summary>{details(r)}</details>')
    return "".join(out)+"</section>"


def cross_panel(package, snap, base):
    record = intel.private_json(package,market_review.MATCHES,{})
    if not record or record.get("scan_at") != snap["at"]:
        return '<details class="signal-detail"><summary>포트폴리오 대조 <small>이번 점검 대기</small></summary></details>'
    rows = record["matched"]
    state = ("공개 표본 부족" if not record["has_public"] else "계좌 원천 미수집" if not record["has_accounts"]
             else "상품 식별 대기" if not record["identified"] else f'연결 근거 {len(rows)}건')
    out = [f'<details class="signal-detail"><summary>포트폴리오 대조 <small>{e(state)}</small></summary>']
    for r in rows:
        out.append(f'<p><a href="{e(base)}/portfolio?position={e(r["position"])}#position">{e(r["holding"])}</a>'
                   f' · {e(r["relation"])} · {e(r["name"])}<br>{e(r["signal"])}<br>재검토 · {e(r["revisit"])}</p>')
    if not rows:
        out.append('<p>공개 표본과 검증된 상품·기초자산·섹터 식별자의 교집합에서 표시할 연결이 없습니다.</p>')
    return "".join(out)+'</details>'


def render(package, base, selected="all"):
    selected = selected if selected in VIEWS else "all"
    snap = market_review.snapshot(package)
    out = ['<section id="market-desk" data-watch class="signal-desk" aria-label="시장 브리핑">']
    if not snap:
        return out[0]+'<div class="signal-hero"><h2>오늘의 시장 브리핑</h2><p>첫 공개 시장 점검을 기다리고 있습니다.</p></div></section>'
    belongs = lambda r: selected == "all" or r["market"] == selected
    cases = sorted((r for r in snap["cases"] if belongs(r) and "change_pct" in r),
                   key=lambda r:(r["evidence"] != "공시 확인",-abs(r["change_pct"]),r["symbol"]))
    day = datetime.fromisoformat(snap["at"]).astimezone(intel.KST)
    out.append(f'<div class="signal-hero"><div class="signal-intro"><small>{day:%Y.%m.%d} &nbsp;/&nbsp; {day:%H:%M} KST</small>'
               f'<h2>오늘의 시장 브리핑</h2><p>마지막 완료 거래일 &nbsp; 국내 {e(snap["days"]["KR"])} · 미국 {e(snap["days"]["US"])}</p></div>')
    if cases:
        r = cases[0]
        out.append(f'<div class="signal-lead"><small>{MARKET[r["market"]]} · {e(r["name"])} · 일간</small>'
                   f'<strong>{signed(r["change_pct"])}</strong><span>{e(r["evidence"])}</span></div>')
    out.append('</div><div class="signal-toolbar"><nav class="signal-nav" aria-label="시장 필터">')
    for k,v in VIEWS.items():
        current = ' aria-current="page"' if k == selected else ''
        out.append(f'<a href="{e(base)}/desk/manager?screen={k}#market-desk"{current}>{v}</a>')
    good = sum(v["status"] == "확인" for v in snap["sources"].values())
    state = "자동 확인" if good and good == len(snap["sources"]) else "일부 수집" if good else "자동 수집 실패"
    out.append(f'</nav><a class="signal-state" href="#signal-sources">{state} · 독립 확인 {len(snap["cases"])}건</a></div>'
               '<div class="signal-boards">')
    groups = [g for g in snap["groups"] if belongs(g)]
    extra, seen = [], set()
    for g in sorted(groups, key=lambda g:(not g["flagged"],g["basis"]!="공개 마감자료 표본",g["kind"]!="종목",g["market"])):
        if g["market"] in seen:
            extra.append(movement(g))
        else:
            out.append(movement(g))
        seen.add(g["market"])
    if not groups:
        out.append('<p class="quiet-state">해당 표본의 종가 변동 자료가 없습니다.</p>')
    out.append('</div>')
    if extra:
        out.append('<details class="signal-detail"><summary>다른 종목·섹터 표본 <small>'
                   + str(len(extra)) + '개 그룹</small></summary>' + "".join(extra) + '</details>')
    spreads = [r for r in snap["spreads"] if belongs(r)]
    out.append(f'<details class="signal-detail"><summary>매수·매도 호가 차이 <small>관측 {len(spreads)}건 · bp</small></summary>')
    for r in spreads:
        out.append(f'<p>{e(r["name"])} · <b>{r["spread_bps"]:g} bp</b> · {e(r["venue"])} · {when(r["observed"])}'
                   f' · {e(r["basis"])} · 동일 시각 표본 {r["rank"]}/{r["sample"]}위 · {link(r["source"])}</p>')
    if not spreads:
        out.append('<p>같은 거래소·시각의 유효 양방향 호가 미확보.</p>')
    out.append('</details>')
    if selected != "XT" or any(belongs(r) for r in snap["structure"]):
        notices = [r for r in snap["structure"] if belongs(r)]
        out.append(f'<details class="signal-detail"><summary>프로그램매매·시장구조 <small>공개 이슈 {len(notices)}건</small></summary>')
        for r in notices:
            out.append(f'<p><b>{e(r["venue"])} · {e(r["title"])}</b><br>{e(r["kind"])} · 관측 {when(r["as_of"])}'
                       f' · 발표 {when(r["published"])}<br>{e(r["implication"])}<br>재검토 · {e(r["revisit"])} · {link(r["source"])}</p>')
        for r in snap["program"] if selected in ("all","KR") else []:
            week = "미확보" if r["five_day_net"] is None else f'{r["five_day_net"]:+,.0f} {e(r["unit"])}'
            out.append(f'<p>{e(r["venue"])} · {e(r["category"])} · {e(r["day"])} · 일간 {r["net"]:+,.0f} {e(r["unit"])}'
                       f' · 최근 관측 5일 {week} · {link(r["source"])}</p>')
        if not snap["program"] and selected in ("all","KR"):
            out.append('<p>해당 거래일의 거래소별 차익·비차익 순매수 미확보.</p>')
        out.append('<p>공개 프로그램 집계로 개별 퀀트·HFT·AI 운용주체를 식별할 수 없습니다.</p></details>')
    out.append(cross_panel(package,snap,base))
    states = snap["sources"]
    out.append(f'<details id="signal-sources" class="signal-detail"><summary>자료 상태 <small>자동 {good}/{len(states)} · 독립 확인 {len(snap["cases"])}건</small></summary>')
    for k,v in states.items():
        out.append(f'<p>{e(k)} · {e(v["status"])} · 마지막 자동 성공 {when(v["success"])}</p>')
    html = "".join(out)+'</details></section>'
    revision = hashlib.sha256(html.encode()).hexdigest()[:16]
    return html.replace("data-watch ",f'data-watch data-revision="{revision}" ',1)
