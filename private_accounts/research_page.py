"""Local manager queue, feed provenance and prospective investment review."""
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
    return (f'<section><h2>오늘의 투자 검토</h2><p><a href="{e(base)}/research">가설 연구장</a>'
            f' · 평가일 도래 {due}건 · 추적 중 {len(pending)}건 · 평가 완료 {len(ideas)-len(pending)}건</p>'
            f'<p><a href="{e(base)}/portfolio#stress">보유분 하방 스트레스</a> · '
            f'<a href="{e(base)}/portfolio#performance">입출금 조정 계좌 성과</a></p>'
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


def show(row, ledger, base, csrf):
    a, result = row["a"], row["result"]
    m = book.metrics(a)
    report = ledger.get(row["report"])
    out = [f'<article class="investment-report"><h3>{e(a["asset"])} · {e(a["currency"])}</h3>'
           f'<p>등록 {e(stamp(row["created"]))} · 평가 예정 {e(row["due"])} · 비교 대상 {e(a["benchmark"])}</p>']
    if report:
        out.append(f'<a href="{e(base)}/desk/{e(report["desk"])}?all=1#report-{e(report["id"])}">{e(report["title"])}</a>')
    else:
        out.append("<strong>참조 보고서 확인 필요</strong>")
    payoff = f'{m["payoff"]:.2f}배' if m["payoff"] is not None else "산정 보류"
    gate = "세 수치 기준 충족" if m["qualifies"] else "미충족 또는 산정 보류"
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
        out.append(f'<p><b>{e(result["verdict"])}</b> · 평가 {e(stamp(result["observed"]))} · '
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
        out.append(f'<h3>{e(benchmark)} · {e(currency)}</h3><p>{e(stamp(observed))} '
                   f'기준 {e(entry)} · {e(due)} 평가 예정</p><div class="comparison"><table><thead><tr>'
                   '<th>후보</th><th>비용 후 기대수익률</th><th>약세 수익률</th><th>안전마진</th></tr></thead><tbody>')
        for name, m in sorted(members, key=lambda item: item[1]["expected"], reverse=True):
            out.append(f'<tr><td>{e(name)}</td><td>{m["expected"]:+.2f}%</td>'
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
    closed = groups[-1][1]
    wins = sum(book.performance(r)[2] > 0 for r in closed)
    out = [f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" '
           f'content="width=device-width,initial-scale=1"><title>가설 연구장</title><style>{css}</style></head><body>',
           chat_page.navigation(base, "research"), '<main class="desk-main"><h1>가설 연구장</h1>'
           '<p>현금 매수 가정의 가격수익률을 같은 통화·기간의 지수와 비교합니다. '
           '배당·이자·임대료를 제외하며, 분할·병합은 양 시점에 같은 조정 기준을 적용하세요.</p>',
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
