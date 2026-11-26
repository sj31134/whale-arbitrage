"""Local work intake. Only fixed public instructions and opaque identifiers leave the ledger."""

import csv
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import uuid
from contextlib import closing, contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from . import local_sources, reports, store

TOOLS = ("Codex", "Claude", "Cowork")
COMMON = (
    "private_accounts/__main__.py",
    "private_accounts/view.py",
    "private_accounts/reports.py",
    "private_accounts/live_panel.py",
    "private_accounts/history_panel.py",
    "agents/INVESTMENT_MANDATE.md",
)
AUDIT = (
    "private_accounts/live_valuation.py",
    "private_accounts/price_history.py",
    "agents/market_prices.py",
    "agents/portfolio.py",
    "private_accounts/live_panel.py",
)
QUANT = ("private_accounts/quant.py", "private_accounts/quant_page.py")
# File ownership for the two implementation lanes. Inventory ownership stays in FILE_MAP.
ROUTES = {
    "audit": (
        "계좌 최신성 감사",
        "equities",
        ["manager"],
        (*AUDIT, "tests/test_live_valuation.py", "tests/test_price_history.py"),
        "원장·스냅샷, 시세·환율 원천과 관측시각",
        "live_valuation.mark_account → live_panel",
        "원장·시세·환율·화면 대조",
    ),
    "sma": (
        "종목별 이동평균 백테스트",
        "equities",
        ["manager"],
        (
            *QUANT,
            "private_accounts/view.py",
            "private_accounts/chat_page.py",
            "tests/test_quant.py",
        ),
        "public_quotes.sqlite3의 price_bar·원천별 거래일과 Mac 보유 행",
        "인증 /quant → quant_page.experiment → quant.evaluate",
        "SMA 116개·비용·미사용 구간·표본 부족 대조",
    ),
    "brief": (
        "오늘 수급·공시를 반영한 매니저 브리핑",
        "manager",
        ["equities"],
        (),
        "market_flow·fundamentals 공개 관측, 완료 거래일과 분야 보고서",
        "research-refresh → market-scan → market-crosscheck → publish-report manager",
        "시장별 마감일·수급·공시 원문 및 참여 분야 게시 ID 대조",
    ),
    "review": (
        "병렬 작업 결과 종합",
        "manager",
        [],
        (),
        "참여 분야가 이미 게시한 보고서와 담당별 인계 결과",
        "기존 결과·재검증 근거 대조 → publish-report manager",
        "검수 기준시각 이전에 게시된 참여 분야 ID와 거래일 대조",
    ),
}
DESK_WORDS = {
    "whale": ("고래",),
    "crypto": ("코인", "암호화폐"),
    "equities": ("주식", "etf"),
    "real_estate": ("부동산", "경매"),
    "us_small_cap_high_beta": ("고베타", "소형주"),
}


def mentioned_desks(request):
    s = request.lower()
    return [
        d for d, words in DESK_WORDS.items() if d in s or any(w in s for w in words)
    ]


def route(request):
    s = request.lower()
    if re.search("주문|매수해|매도해|봇 시작|거래 권한", s):
        raise ValueError("직접 거래는 보류 상태입니다.")
    if "병렬 작업 결과 종합" in s:
        return "review"
    hits = [
        k
        for k, words in (
            ("sma", ("sma", "이동평균", "백테스트")),
            ("audit", ("최신성", "계좌 감사")),
            ("brief", ("브리핑", "종합 보고")),
        )
        if any(w in s for w in words)
    ]
    if not hits and any(w in s for w in DESK_WORDS["us_small_cap_high_beta"]):
        hits = ["us_small_cap_high_beta"]
    if not hits:
        hits = mentioned_desks(request)
        if len(hits) > 1 and "비교" in s:
            hits = ["brief"]
    if len(hits) != 1:
        raise ValueError(
            "주담당과 목표를 특정할 수 없습니다. 요청을 한 업무 단위로 나누세요."
        )
    return hits[0]


def template(kind):
    if kind in ROUTES:
        return ROUTES[kind]
    return (
        f"{kind} 분야 가설 검토",
        kind,
        ["manager"],
        (),
        f"agents/{kind}/README.md 및 담당 공개 원천",
        f"portfolio-review {kind} --signals (Mac 내부) → publish-report {kind}",
        "근거·하방·재검토 조건 대조",
    )


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def primary_root(root):
    raw = subprocess.check_output(
        ["git", "worktree", "list", "--porcelain", "-z"], cwd=root
    )
    first = os.fsdecode(raw.split(b"\0")[0]).removeprefix("worktree ")
    return Path(first).resolve()


@contextmanager
def ledger(primary):
    directory = primary / "private_accounts/.local"
    local_sources.secure_directory(directory)
    path = directory / "work.sqlite3"
    os.close(os.open(path, os.O_CREAT | os.O_NOFOLLOW | os.O_RDONLY, 0o600))
    with (
        local_sources.open_private(path),
        closing(sqlite3.connect(path, timeout=10)) as db,
        db,
    ):
        db.row_factory = sqlite3.Row
        db.execute("BEGIN IMMEDIATE")
        db.execute("""CREATE TABLE IF NOT EXISTS work(id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE,
                   spec TEXT, state TEXT, tool TEXT, session TEXT, opened TEXT, report TEXT UNIQUE)""")
        db.execute(
            """CREATE TABLE IF NOT EXISTS events(id TEXT, at TEXT, state TEXT, tool TEXT, session TEXT)"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, evidence TEXT)"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS notes(event_no INTEGER PRIMARY KEY, note TEXT)"""
        )
        yield db


def inventory(root):
    with (root / "agents/FILE_MAP.csv").open(newline="") as f:
        return {r["path"]: r["owner"] for r in csv.DictReader(f)}


def session_id(text):
    if not re.fullmatch("[a-f0-9]{32}", text):
        raise ValueError("work session에서 발급한 세션 ID를 사용하세요.")
    return text


def get(db, key):
    row = db.execute("SELECT * FROM work WHERE id=?", (key,)).fetchone()
    if row is None:
        raise ValueError("등록된 작업 ID가 없습니다.")
    return row


def blockers(db, spec, key):
    result = []
    for r in db.execute(
        "SELECT id,spec FROM work WHERE state='running' AND id<>?", (key,)
    ):
        if set(json.loads(r["spec"])["writes"]) & set(spec["writes"]):
            result.append(r["id"])
    return result


def baseline(root, primary, spec):
    names = set(COMMON) | set(spec["writes"]) | set(AUDIT)
    if spec["kind"] == "sma":
        names.update(QUANT)
    if root != primary:
        # Include other dirty runtime modules used indirectly by the dashboard.
        for args in (
            ["diff", "HEAD", "--name-only"],
            ["ls-files", "--others", "--exclude-standard"],
        ):
            paths = subprocess.check_output(
                ["git", *args, "--", "private_accounts", "agents"], cwd=primary
            )
            names.update(
                p
                for p in paths.decode().splitlines()
                if p.endswith((".py", ".js", ".css"))
            )
    for name in sorted(names):
        a, b = root / name, primary / name
        if (
            not b.is_file()
            or not a.is_file()
            or (a != b and a.read_bytes() != b.read_bytes())
        ):
            raise ValueError(
                "Mac 기준 구현 누락 또는 불일치 · 기본 작업 트리에서 확인하세요."
            )


def event(db, key, state, tool=None, session=None, note=None):
    db.execute(
        "UPDATE work SET state=?,tool=?,session=? WHERE id=?",
        (state, tool, session, key),
    )
    log = db.execute(
        "INSERT INTO events VALUES(?,?,?,?,?)", (key, now(), state, tool, session)
    )
    if note:
        db.execute("INSERT INTO notes VALUES(?,?)", (log.lastrowid, note))


def packet(db, row, primary):
    s = json.loads(row["spec"])
    goal, lead, _, _, sources, engine, checks = template(s["kind"])
    peers = s["peers"]
    owners = inventory(primary)
    last_note = db.execute(
        "SELECT note FROM events JOIN notes ON event_no=events.rowid "
        "WHERE id=? ORDER BY events.rowid DESC LIMIT 1",
        (row["id"],),
    ).fetchone()
    return dict(
        id=row["id"],
        목표=goal,
        주담당=lead,
        협업담당=peers,
        시장=list(s["days"]),
        기준시각=s["as_of"],
        마지막완료거래일=s["days"],
        읽기=[sources, "AGENTS.md", f"agents/{lead}/README.md"],
        엔진=engine,
        실행결과={
            "audit": "account_marks.sqlite3 · 계좌 평가 화면",
            "sma": "인증된 /quant · .local/quant-<digest>.json",
            "brief": ".local/desk_reports.json · 매니저 화면",
        }.get(s["kind"], ".local/desk_reports.json"),
        파일담당={p: owners.get(p) for p in s["writes"]},
        쓰기=s["writes"],
        선행작업=s["after"],
        충돌작업=blockers(db, s, row["id"]),
        경계="공개 수집기에 보유 목록 전달 금지. 계좌 대조는 Mac 내부. 주문 보류.",
        산출물=(
            "구현·회귀시험 → work.sqlite3 검증 기록"
            if s["development"]
            else f"publish-report {lead} → private_accounts/.local/desk_reports.json"
        ),
        근거표지=list(check_labels(s["kind"])),
        검증=checks,
        보고대상="투자 매니저 → 사용자",
        상태=row["state"],
        선점명령=f"python3 -m private_accounts work claim {row['id']} --tool <Codex|Claude|Cowork> --session <로컬 세션 ID>",
        로컬수락도구=row["tool"] if row["state"] == "running" else None,
        인계대상=row["tool"] if row["state"] == "handoff" else None,
        최근인계사유=last_note[0] if last_note else None,
        수락="Mac에서 work claim 성공 후 시작. 외부 상태 미확인",
    )


def register(db, args, root, primary):
    kind = route(args.request)
    if (args.development or args.write) and kind not in ("audit", "sma"):
        raise ValueError("코드 변경 담당은 계좌 감사 또는 SMA 구현에서 선택하세요.")
    if args.write and not args.development:
        raise ValueError("추가 쓰기 파일은 --development 작업에서 지정하세요.")
    writes = (
        sorted(set(template(kind)[3]) | set(args.write)) if args.development else []
    )
    owners = inventory(primary)
    allowed = {"audit": {"shared", "equities"}, "sma": {"shared", "equities"}}.get(
        kind, set()
    )
    for path in writes:
        if (
            owners.get(path) not in allowed
            or not path.startswith(("private_accounts/", "agents/", "tests/"))
            or path in {"agents/FILE_MAP.csv", "agents/FILE_TREE.md"}
        ):
            raise ValueError(
                "파일 담당 또는 허용 쓰기 범위를 확인하세요. 신규 파일은 공통 분류표 인계 대기입니다."
            )
    for foreign, paths in (("audit", AUDIT), ("sma", QUANT)):
        if foreign != kind and set(writes) & set(paths):
            raise ValueError("다른 작업의 전담 파일입니다.")
    cutoff = store.timestamp(args.as_of)
    days = {}
    zones = {
        "KR": "Asia/Seoul",
        "US": "America/New_York",
        "JP": "Asia/Tokyo",
        "CN": "Asia/Shanghai",
        "XT": "UTC",
    }
    for item in args.day:
        market, sep, day = item.partition("=")
        if not sep or market not in zones or market in days:
            raise ValueError("--day KR=YYYY-MM-DD 형식으로 시장별 마감일을 입력하세요.")
        if market != "XT" and date.fromisoformat(day).weekday() >= 5:
            raise ValueError("주식 시장 주말을 완료 거래일로 지정할 수 없습니다.")
        if (
            date.fromisoformat(day)
            > datetime.fromisoformat(cutoff).astimezone(ZoneInfo(zones[market])).date()
        ):
            raise ValueError("기준시각 이후 거래일입니다.")
        days[market] = day
    if kind == "brief" and not {"KR", "US"} <= days.keys():
        raise ValueError("브리핑에 필요한 KR·US 완료 거래일을 각각 지정하세요.")
    if (
        kind == "sma"
        and not args.development
        and (len(days) != 1 or not set(days) <= {"KR", "US", "XT"})
    ):
        raise ValueError("한 종목의 KR·US·XT 중 해당 시장을 지정하세요.")
    if args.position and (
        kind != "sma"
        or args.development
        or not re.fullmatch("[a-f0-9]{64}", args.position)
    ):
        raise ValueError("SMA 분석의 로컬 종목 식별값을 확인하세요.")
    for dep in args.after:
        get(db, dep)
    inferred = mentioned_desks(args.request) if kind in ("brief", "review") else []
    peers = sorted(set(template(kind)[2]) | set(args.with_desk) | set(inferred))
    if kind == "review" and not peers:
        raise ValueError("기존 게시물을 검수할 참여 분야를 지정하세요.")
    if template(kind)[1] in peers:
        raise ValueError("주담당은 협업 목록에서 제외하세요.")
    spec = dict(
        position=args.position,
        peers=peers,
        development=args.development,
        kind=kind,
        as_of=cutoff,
        days=days,
        after=sorted(set(args.after)),
        writes=writes,
    )
    baseline(root, primary, spec)
    payload = json.dumps(spec, sort_keys=True)
    fingerprint = hashlib.sha256(payload.encode()).hexdigest()
    prior = db.execute(
        "SELECT id FROM work WHERE fingerprint=?", (fingerprint,)
    ).fetchone()
    if prior:
        return packet(db, get(db, prior["id"]), primary)
    key = "work-" + uuid.uuid4().hex
    db.execute(
        "INSERT INTO work VALUES(?,?,?,'queued',NULL,NULL,?,NULL)",
        (key, fingerprint, payload, now()),
    )
    event(db, key, "queued")
    return packet(db, get(db, key), primary)


def verify(primary, row, spec, ref):
    ledger_rows = reports.read(primary / "private_accounts")
    r = ledger_rows.get(ref, {})
    desk = template(spec["kind"])[1]
    if (
        r.get("desk") != desk
        or r.get("as_of") != spec["as_of"]
        or r.get("published", "") == ""
        or datetime.fromisoformat(r["published"])
        < datetime.fromisoformat(row["opened"])
        or r.get("status") == "판단 보류"
        or not r.get("sources")
    ):
        raise ValueError(
            "작업 접수 후 게시된 같은 담당·기준시각의 근거 있는 보고서가 필요합니다."
        )
    if desk == "manager":
        members = [ledger_rows.get(k, {}) for k in r["inputs"]]
        if (
            set(spec["peers"]) != {m.get("desk") for m in members}
            or any(not m.get("sources") for m in members)
            or any(
                m.get("desk") not in reports.ROOMS[1:] or m["as_of"] > r["as_of"]
                for m in members
            )
        ):
            raise ValueError("검증된 참여 분야 보고서 ID가 필요합니다.")
        if spec["kind"] == "review":
            if any(not m.get("published") or store.timestamp(m["published"]) > spec["as_of"] for m in members):
                raise ValueError("검수 기준시각까지 게시된 분야 보고서가 필요합니다.")
        elif any(m["as_of"] != spec["as_of"] for m in members):
            raise ValueError("브리핑과 같은 기준시각의 분야 보고서가 필요합니다.")
    # Contract labels tie a published result to this request and its market dates.
    labels = {x["label"] for x in r["sources"]}
    if spec["kind"] == "brief" and not {"수급", "공시"} <= {
        x["label"] for x in r["sources"] if x.get("url")
    }:
        raise ValueError("수급·공시의 공개 원문 주소가 필요합니다.")
    required = {f"{m} {d}" for m, d in spec["days"].items()}
    required.update(check_labels(spec["kind"]))
    if not required <= labels:
        raise ValueError("거래일 또는 작업별 검증 근거가 누락되었습니다.")


def verify_artifact(primary, spec, digest, directory):
    package = primary / "private_accounts"
    if spec["kind"] == "audit":
        from . import live_valuation

        with live_valuation.connection(package, account_history=True) as db:
            day = (
                datetime.fromisoformat(spec["as_of"])
                .astimezone(ZoneInfo("Asia/Seoul"))
                .date()
            )
            if (
                db is None
                or not db.execute(
                    "SELECT 1 FROM mark_day WHERE day=? AND julianday(observed)<=julianday(?) "
                    "AND ledger IS NOT NULL AND source_at IS NOT NULL LIMIT 1",
                    (day.isoformat(), spec["as_of"]),
                ).fetchone()
            ):
                raise ValueError("기준시각 이내의 당일 계좌 시점평가 인계 대기입니다.")
    elif spec["kind"] == "brief":
        from agents import intelligence

        days = {m: spec["days"][m] for m in ("KR", "US")}
        archive = "market_session_" + days["KR"] + "_" + days["US"] + ".json"
        if intelligence.private_json(package, archive, {}).get("days") != days:
            raise ValueError("해당 거래일의 로컬 시장 점검 기록 인계 대기입니다.")
    elif spec["kind"] == "sma":
        from agents import intelligence
        from agents.equities.daily_bars import US
        from . import quant

        if not re.fullmatch("[a-f0-9]{64}", digest or ""):
            raise ValueError("Mac에 저장된 실험 ID가 필요합니다.")
        record = intelligence.private_json(package, f"quant-{digest}.json", {})
        inputs = record.get("inputs", {})
        if (
            hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
            != digest
        ):
            raise ValueError("실험 원천을 확인할 수 없습니다.")
        if spec["position"]:
            from agents.portfolio import portfolio_accounts
            from . import live_valuation, price_history

            accounts = portfolio_accounts(
                directory, package, quote_book=live_valuation.read(package)
            )
            with live_valuation.connection(package) as db:
                keys = [
                    price_history.local_history_key(db, a["provider"], m)
                    for a in accounts
                    for m in a["marks"]
                    if intelligence.position_id(
                        a["provider"], a["account"], m["symbol"], m["currency"]
                    )
                    == spec["position"]
                ]
            if keys != [tuple(inputs["key"])]:
                raise ValueError("접수한 로컬 보유 행과 실험 원천 식별자가 다릅니다.")
        venue = inputs["key"][0]
        market = "US" if venue in US else {"KRX": "KR", "KRAKEN_X": "XT", "BINANCE_B": "XT"}.get(venue)
        if not inputs["rows"] or spec["days"] != {market: inputs["rows"][-1]["day"]}:
            raise ValueError("선택한 종목의 시장과 완료 일봉 마지막 날짜를 확인하세요.")
        if inputs.get("costs") != vars(quant.costs(venue)):
            raise ValueError("시장별 전략 비용 가정을 확인하세요.")
        if inputs.get("version") == quant.VERSION:
            _, result = quant.replay(inputs)
        elif inputs.get("version") in {"sma-cross-1", "sma-cross-1.1"}:
            # A completed legacy receipt required a clean full series.
            bars, issues = quant.prepare(inputs["rows"], inputs["sessions"], venue)
            result = quant.evaluate(bars, quant.costs(venue), issues)
            result["version"] = inputs["version"]
        else:
            raise ValueError("재현할 수 없는 퀀트 전략 버전입니다.")
        if len(result["holdout"]) != 116 or json.loads(
            json.dumps(result)
        ) != record.get("result"):
            raise ValueError("미사용 기간 116개 결과 재계산 검증 대기입니다.")


def check_labels(kind):
    return {
        "audit": ("원장", "시세", "환율", "화면 대조"),
        "sma": ("완료 일봉", "116개 SMA", "비용 차감", "미사용 기간"),
        "brief": ("수급", "공시"),
    }.get(kind, ())


def execute(args, root, directory=None):
    if getattr(args, "checkout", None):
        checkout = args.checkout.resolve()
        if primary_root(checkout) != primary_root(root):
            raise ValueError("같은 저장소 worktree를 지정하세요.")
        root = checkout
    if args.action == "session":
        return uuid.uuid4().hex
    primary = primary_root(root)
    with ledger(primary) as db:
        if args.action == "register":
            return register(db, args, root, primary)
        if args.action == "status" and not args.id:
            return [
                dict(
                    id=r["id"],
                    목표=template(json.loads(r["spec"])["kind"])[0],
                    상태=r["state"],
                    수락도구=r["tool"] if r["state"] == "running" else None,
                    외부="외부 상태 미확인",
                )
                for r in db.execute("SELECT * FROM work ORDER BY opened")
            ]
        row = get(db, args.id)
        spec = json.loads(row["spec"])
        if args.action == "status":
            return dict(
                packet(db, row, primary),
                로컬인계기록=[
                    dict(e)
                    for e in db.execute(
                        "SELECT at,state,tool,session,note FROM events LEFT JOIN notes ON event_no=events.rowid WHERE id=? ORDER BY events.rowid",
                        (args.id,),
                    )
                ],
                게시ID=row["report"],
                완료근거=[
                    x[0]
                    for x in db.execute(
                        "SELECT evidence FROM receipts WHERE id=?", (args.id,)
                    )
                ],
            )
        if args.action == "ticket":
            baseline(root, primary, spec)
            return packet(db, row, primary)
        session_id(args.session)
        if args.action == "claim":
            baseline(root, primary, spec)
            if row["state"] == "running" and (row["session"], row["tool"]) == (
                args.session,
                args.tool,
            ):
                return "동일 세션 재개"
            if row["state"] not in ("queued", "handoff", "held", "failed") or (
                row["state"] == "handoff" and row["tool"] and row["tool"] != args.tool
            ):
                raise ValueError("선점할 수 없는 상태 또는 인계 대상입니다.")
            if blockers(db, spec, args.id) or any(
                get(db, dep)["state"] != "done" for dep in spec["after"]
            ):
                raise ValueError("공용 파일 선점 또는 선행 작업 완료를 기다리세요.")
            event(db, args.id, "running", args.tool, args.session)
        else:
            if (
                args.action == "verify"
                and row["state"] == "done"
                and (row["session"], row["report"]) == (args.session, args.report)
            ):
                return "이미 완료 검증됨"
            if row["state"] != "running" or row["session"] != args.session:
                raise ValueError("현재 선점 세션에서만 상태를 변경할 수 있습니다.")
            if args.action == "verify":
                if spec["development"]:
                    if args.report or args.experiment:
                        raise ValueError("개발 완료는 담당 회귀시험으로 검증합니다.")
                    baseline(root, primary, spec)
                    suite = (
                        ["tests/test_quant.py"]
                        if spec["kind"] == "sma"
                        else [
                            "tests/test_live_valuation.py",
                            "tests/test_price_history.py",
                        ]
                    )
                    generation = db.execute(
                        "SELECT MAX(rowid) FROM events WHERE id=?", (args.id,)
                    ).fetchone()[0]
                    db.commit()
                    result = subprocess.run(
                        [sys.executable, "-m", "pytest", "-q", *suite],
                        cwd=root,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    db.execute("BEGIN IMMEDIATE")
                    current = db.execute(
                        "SELECT MAX(rowid) FROM events WHERE id=?", (args.id,)
                    ).fetchone()[0]
                    if current != generation:
                        raise ValueError(
                            "시험 중 선점 상태가 변경되어 결과를 폐기했습니다."
                        )
                    if result.returncode:
                        event(db, args.id, "failed", row["tool"], args.session)
                        db.commit()
                        raise ValueError("failed · 담당 회귀시험 실패")
                else:
                    verify(primary, row, spec, args.report)
                    verify_artifact(
                        primary, spec, args.experiment, directory or store.PRIVATE_DIR
                    )
                evidence = (
                    " + ".join(suite)
                    if spec["development"]
                    else (args.experiment or args.report)
                )
                db.execute("INSERT INTO receipts VALUES(?,?)", (args.id, evidence))
                db.execute(
                    "UPDATE work SET report=? WHERE id=?", (args.report, args.id)
                )
                event(db, args.id, "done", row["tool"], args.session)
            else:
                state = {"handoff": "handoff", "hold": "held", "fail": "failed"}[
                    args.action
                ]
                event(
                    db,
                    args.id,
                    state,
                    getattr(args, "to", None),
                    args.session,
                    args.reason,
                )
        return packet(db, get(db, args.id), primary)


def arguments(commands):
    cmd = commands.add_parser("work", help="로컬 투자 작업 접수·선점·인계")
    cmd.add_argument("--checkout", type=Path, help="기준 구현과 대조할 별도 worktree")
    actions = cmd.add_subparsers(dest="action", required=True)
    p = actions.add_parser("register")
    p.add_argument("request")
    p.add_argument("--position", help="Mac에서 선택한 보유 행의 로컬 position_id")
    p.add_argument(
        "--development",
        action="store_true",
        help="구현 인계. 완료 시 담당 회귀시험을 직접 실행",
    )
    p.add_argument("--as-of", required=True)
    p.add_argument(
        "--day",
        action="append",
        required=True,
        help="달력에서 확인한 시장별 완료 거래일 KR=YYYY-MM-DD",
    )
    p.add_argument(
        "--with-desk", action="append", default=[], choices=reports.ROOMS[1:]
    )
    p.add_argument("--after", action="append", default=[])
    p.add_argument("--write", action="append", default=[])
    actions.add_parser("session")
    for action in ("ticket", "status", "claim", "handoff", "fail", "hold", "verify"):
        p = actions.add_parser(action)
        if action == "status":
            p.add_argument("id", nargs="?")
        else:
            p.add_argument("id")
        if action not in ("ticket", "status"):
            p.add_argument("--session", required=True)
        if action == "claim":
            p.add_argument("--tool", required=True, choices=TOOLS)
        if action in ("hold", "fail", "handoff"):
            p.add_argument(
                "--reason",
                choices=(
                    "자료 대기",
                    "담당 인계",
                    "시험 실패",
                    "기준 구현 누락",
                    "세션 중단",
                ),
                default="담당 인계",
            )
        if action == "handoff":
            p.add_argument("--to", choices=TOOLS)
        if action == "verify":
            p.add_argument("--report")
            p.add_argument("--experiment", help="Mac 내부 SMA 결과 digest")
