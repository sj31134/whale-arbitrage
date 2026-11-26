"""Local manager queue, feed provenance and prospective investment review."""
from decimal import Decimal
import secrets
from datetime import datetime
import re
from html import escape

from agents import intelligence as intel
from . import chat_page, reports, research_book as book

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


def manager_panel(package, base):
    today = datetime.now(intel.KST).date().isoformat()
    ideas = book.entries(package)
    pending = [row for row in ideas if not row["result"]]
    due = sum(row["due"] <= today for row in pending)
    qualifying = sum(book.metrics(row["a"])["qualifies"] for row in pending)
    return (f'<section><h2>오늘의 투자 검토</h2><p><a href="{e(base)}/research">가설 연구장</a>'
            f' · 평가일 도래 {due}건 · 추적 중 {len(pending)}건 (3관문 집중 후보 {qualifying}건) · 평가 완료 {len(ideas)-len(pending)}건</p>'
            f'<div class="chips"><a class="chip" href="{e(base)}/research">1. 시나리오·3관문 점검</a>'
            f'<a class="chip" href="{e(base)}/strategies">2. 4대 위기 백테스트·레짐 규칙</a>'
            f'<a class="chip" href="{e(base)}/quant">3. 종목별 변동성·차트 검증</a>'
            f'<a class="chip" href="{e(base)}/portfolio#stress">보유분 하방 스트레스</a>'
            f'<a class="chip" href="{e(base)}/portfolio#performance">입출금 조정 계좌 성과</a></div>'
            + feed_health(package) + "</section>")


def field(key, label, kind="text", attrs=""):
    return f'<label>{e(label)}<input name="{key}" type="{kind}" required {attrs}></label>'


def price(key, label):
    return field(key, label, "number", 'min="0" step="any"')


def form(base, csrf, action, key):
    return (f'<form class="research-form" method="post" action="{e(base)}/desk/manager/{action}">'
            f'<input type="hidden" name="csrf" value="{e(csrf)}">'
            f'<input type="hidden" name="idea" value="{e(key)}">')


def obs_field():
    return field("observed", "두 가격의 공통 기준시각 (KST)", "datetime-local", 'step="1"')


def new_form(ledger, base, csrf):
    eligible = sorted((r for r in ledger.values() if r["sources"]), key=lambda r: r["as_of"], reverse=True)
    if not eligible:
        return "<p>원문 근거가 있는 분야 보고서를 게시하면 가설을 등록할 수 있습니다.</p>"
    choices = "".join(f'<option value="{e(r["id"])}">{e(stamp(r["as_of"]))} · {e(r["title"])}</option>'
                      for r in eligible)
    return (form(base, csrf, "idea", secrets.token_hex(16)) + '<label>근거 보고서<select name="report">'
            + choices + "</select></label>" + field("asset", "평가 대상") + field("currency", "평가통화", attrs='placeholder="KRW" maxlength="3"')
            + field("benchmark", "같은 통화 기준의 비교지수·대안") + obs_field()
            + price("entry", "대상 기준가격") + price("benchmark_entry", "비교지수 기준값")
            + field("price_source", "대상 기준가격 원문", "url") + field("benchmark_source", "비교지수 기준값 원문", "url")
            + price("bear", "약세 목표가격 · 20%") + price("base", "기준 내재가치 겸 목표가격 · 50%")
            + price("bull", "강세 목표가격 · 30%") + price("fees", "예상 왕복 수수료·세금 (bp)")
            + price("slip", "예상 왕복 스프레드·슬리피지 (bp)") + field("catalyst", "예상 촉매와 근거")
            + field("invalidate", "가설을 철회할 관측 조건") + field("due", "평가 예정일", "date")
            + '<button>가설과 최초 가정 저장</button></form>')


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


def render(package, base, csrf, css, done=None):
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
    out = [f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" '
           f'content="width=device-width,initial-scale=1"><title>가설 연구장</title><style>{css}</style></head><body>',
           chat_page.navigation(base, "research"), '<main class="desk-main"><h1>가설 연구장</h1>'
           '<p>현금 매수 가정의 가격수익률을 같은 통화·기간의 지수와 비교합니다. '
           '배당·이자·임대료를 제외하며, 분할·병합은 양 시점에 같은 조정 기준을 적용하세요.</p>',
           guide, kpis,
           f'<p>검증 완료 {len(closed)}건 · 비교지수 초과 {wins}건 · 전체 등록 {len(rows)}건</p>',
           '<details id="create"><summary>새 투자 가설 등록</summary>'
           '<p>기대수익률 12%는 입력한 평가기간 기준입니다. 약세 손실과 기준 이익이 있는 경우 '
           '확률가중 손익비 3배를 검사하며 안전마진 기준은 20%입니다. 등록한 가정은 결과와 함께 보존합니다.</p>',
           new_form(ledger, base, csrf), "</details>", comparison(rows)]
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
