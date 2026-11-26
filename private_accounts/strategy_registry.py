"""Public-only research catalogue, as-of disclosures and immutable price experiments."""

import gzip
import hashlib
import json
import os
import stat
import re
import sqlite3
import zlib
from collections import Counter
from contextlib import closing, contextmanager
from datetime import date, datetime, timezone
from statistics import median
from urllib.parse import urlsplit

from agents import intelligence
from . import local_sources, quant
from .strategy_catalog import CATALOG, EVENTS

SAMPLE = 32
WINDOW = 63
PRICE_IDS = tuple(k for k, entry in CATALOG.items() if entry["kind"] == "price")
EVENT_HOSTS = {
    "berkshire": {"www.sec.gov"},
    "elevation": {"www.nctreasurer.gov"},
    "household": {"disclosures-clerk.house.gov"},
    "venture": {"www.businesswire.com", "www.sec.gov", "www.soundventures.com"},
}


def packed(x):
    return json.dumps(
        x, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def digest(x):
    return hashlib.sha256(packed(x).encode()).hexdigest()


def instant(text):
    stamp = datetime.fromisoformat(text)
    if stamp.tzinfo is None:
        raise ValueError("공개 시각에는 시간대가 필요합니다.")
    return stamp.astimezone(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def database(package):
    if package is None:
        raise ValueError("Mac 프로젝트 연결을 확인하세요.")
    folder = package / ".local"
    local_sources.secure_directory(folder)
    path = folder / "strategy_registry.sqlite3"
    fd = os.open(path, os.O_CREAT | os.O_NOFOLLOW | os.O_RDWR, 0o600)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
        ):
            raise ValueError("연구 DB 소유자와 파일 형식을 확인하세요.")
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)
    with closing(sqlite3.connect(path, timeout=15)) as db, db:
        db.row_factory = sqlite3.Row
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS specification(
              strategy TEXT, version TEXT, document TEXT NOT NULL, state TEXT NOT NULL,
              PRIMARY KEY(strategy,version));
            CREATE TABLE IF NOT EXISTS experiment(
              id TEXT PRIMARY KEY, strategy TEXT, version TEXT, panel TEXT, created TEXT, result TEXT);
            CREATE INDEX IF NOT EXISTS strategy_history ON experiment(strategy,version,created);
            CREATE TABLE IF NOT EXISTS cohort(
              rule TEXT PRIMARY KEY, panel TEXT NOT NULL, registered TEXT NOT NULL, members TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS refresh_status(
              id INTEGER PRIMARY KEY CHECK(id=1), attempted TEXT, status TEXT);
            CREATE TABLE IF NOT EXISTS disclosure(
              strategy TEXT, effective TEXT, available TEXT, url TEXT, items TEXT,
              PRIMARY KEY(strategy,effective,available,url));
        """
        )
        for key, doc in CATALOG.items():
            body = packed(doc)
            db.execute(
                "INSERT OR IGNORE INTO specification VALUES(?,?,?,'연구 중')",
                (key, doc["version"], body),
            )
            old = db.execute(
                "SELECT document FROM specification WHERE strategy=? AND version=?",
                (key, doc["version"]),
            ).fetchone()
            if old[0] != body:
                raise ValueError("변경된 전략 명세에는 새 버전이 필요합니다.")
        for key, day, when, url, items in EVENTS:
            db.execute(
                "INSERT OR IGNORE INTO disclosure VALUES(?,?,?,?,?)",
                (key, day, instant(when), url, packed(sorted(items))),
            )
        yield db


def state(db, key, value):
    if (
        key not in CATALOG
        or CATALOG[key]["kind"] == "existing"
        or value not in ("연구 중", "일시정지")
    ):
        raise ValueError("연구 전략과 상태를 확인하세요.")
    db.execute(
        "UPDATE specification SET state=? WHERE strategy=? AND version=?",
        (value, key, CATALOG[key]["version"]),
    )


def import_event(db, doc):
    if not isinstance(doc, dict) or set(doc) != {
        "strategy",
        "effective",
        "available",
        "url",
        "items",
    }:
        raise ValueError("공시 입력 형식을 확인하세요.")
    key, url = doc["strategy"], doc["url"]
    if not all(
        isinstance(doc[k], str) for k in ("strategy", "effective", "available", "url")
    ):
        raise ValueError("공시 기관·날짜·주소 형식을 확인하세요.")
    parsed = urlsplit(url)
    if (
        key not in EVENT_HOSTS
        or parsed.scheme != "https"
        or parsed.netloc not in EVENT_HOSTS[key]
        or (parsed.query and not (key == "elevation" and parsed.query == "attachment="))
        or parsed.fragment
    ):
        raise ValueError("지정된 공개 원문 도메인을 사용하세요.")
    if key == "berkshire" and not parsed.path.startswith(
        "/Archives/edgar/data/1067983/"
    ):
        raise ValueError("버크셔의 EDGAR 공시 원문을 사용하세요.")
    if key == "household" and not parsed.path.startswith("/public_disc/ptr-pdfs/"):
        raise ValueError("미 하원 PTR 원문을 사용하세요.")
    day = date.fromisoformat(doc["effective"])
    if key == "berkshire" and (day.month, day.day) not in {
        (3, 31),
        (6, 30),
        (9, 30),
        (12, 31),
    }:
        raise ValueError("13F 기준일에는 분기 말일을 사용하세요.")
    when = instant(doc["available"])
    if day > date.fromisoformat(when[:10]) or datetime.fromisoformat(
        when
    ) > datetime.now(timezone.utc):
        raise ValueError("관측일과 실제 공개시각을 확인하세요.")
    items = doc["items"]
    if (
        not isinstance(items, list)
        or len(items) > 200
        or not all(
            isinstance(i, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .&-]{0,59}", i)
            for i in items
        )
    ):
        raise ValueError("검토한 공개 발행인 또는 주식 코드만 입력하세요.")
    payload = packed(sorted(set(items)))
    keys = (key, day.isoformat(), when, url)
    # One authoritative sample per event time. A correction has a later public timestamp.
    old = db.execute(
        "SELECT url,items FROM disclosure WHERE strategy=? AND effective=? AND available=?",
        keys[:3],
    ).fetchone()
    if old and (old["url"], old["items"]) != (url, payload):
        raise ValueError(
            "같은 공시 시점이 충돌합니다. 정정의 실제 공개시각을 사용하세요."
        )
    db.execute("INSERT OR IGNORE INTO disclosure VALUES(?,?,?,?,?)", (*keys, payload))


def evidence(db, key, cutoff):
    rows = db.execute(
        """SELECT effective,available,url,items FROM disclosure WHERE strategy=? AND available<=?
                         ORDER BY effective,available""",
        (key, instant(cutoff)),
    )
    by_day = {r["effective"]: dict(r, items=json.loads(r["items"])) for r in rows}
    records = list(by_day.values())
    if key != "berkshire":
        return dict(records=records, items=records[-1]["items"] if records else [])
    matched = []
    if len(records) >= 2:
        first, second = records[-2:]
        a, b = (date.fromisoformat(r["effective"]) for r in (first, second))
        if (b.year - a.year) * 12 + b.month - a.month == 3:
            matched = sorted(set(first["items"]) & set(second["items"]))
    return dict(records=records, items=matched)


def target(key, closes):
    if key == "hold":
        return 1.0
    if key in ("trend-252", "trend-vote"):
        windows = (252,) if key == "trend-252" else (63, 126, 252)
        return sum(closes[-1] > closes[-1 - n] for n in windows) / len(windows)
    if key != "variance-cap":
        raise ValueError("가격 규칙을 확인하세요.")
    # A fixed 21-session approximation to the previous month's realized variance.
    recent = closes[-22:]
    var = 252 * sum((b / a - 1) ** 2 for a, b in zip(recent, recent[1:])) / 21
    return min(1.0, 0.15**2 / var) if var else 1.0


def simulate(bars, key, fee, scale):
    start = len(bars) - WINDOW
    closes = [b["close"] for b in bars]
    cash, shares, peak, dd, turnover = 1.0, 0.0, 1.0, 0.0, 0.0
    for i in range(start, len(bars)):
        bar = bars[i]
        if i == start or (key != "hold" and bar["day"][:7] != bars[i - 1]["day"][:7]):
            weight = target(key, closes[:i])
            stock = shares * bar["open"]
            wealth = cash + stock
            change = weight * wealth - stock
            cost = fee.side(change < 0, scale)
            trade = change / (1 + (1 if change >= 0 else -1) * weight * cost)
            cash -= trade + abs(trade) * cost
            shares += trade / bar["open"]
            turnover += abs(trade) / wealth
        wealth = cash + shares * bar["close"]
        peak = max(peak, wealth)
        dd = min(dd, wealth / peak - 1)
    return dict(net=wealth - 1, dd=dd, turnover=turnover)


def panel_name(package):
    index = intelligence.private_json(package, "equity_screen_index.json", {})
    stamp = index.get("run", "")
    return stamp if re.fullmatch(r"[0-9]{8}T[0-9]{6}", stamp) else None


def read_panel(package, requested=None, frozen=None):
    stamp = panel_name(package)
    folder = package / ".local/equity_screens"
    if not stamp:
        raise ValueError("완료된 공개 일봉 실험이 없습니다.")
    base, check = (folder / (stamp + s) for s in (".sqlite3", "-validation.sqlite3"))
    if any(not p.is_file() or p.is_symlink() for p in (base, check)):
        raise ValueError("해당 공개 일봉 또는 독립 종가 검증을 기다립니다.")
    with closing(sqlite3.connect(base.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.execute(
            "ATTACH DATABASE ? AS checks", (check.resolve().as_uri() + "?mode=ro",)
        )
        meta = json.loads(db.execute("SELECT payload FROM metadata").fetchone()[0])
        universe = db.execute(
            """SELECT r.venue,r.symbol,r.currency FROM result r
                              JOIN checks.listing_class l USING(venue,symbol,currency)
                              WHERE l.kind IN ('KIND 상장법인','보통주 명칭 확인')"""
        ).fetchall()
        groups = {}
        for market in ("KR", "US"):
            pool = [k for k in universe if (k[0] == "KRX") == (market == "KR")]
            if frozen is not None:
                chosen = [tuple(item) for item in frozen[market]]
            elif requested is None:
                chosen = sorted(
                    pool, key=lambda k: (digest(["public-stock-sample-v1", *k]), k)
                )[:SAMPLE]
            else:
                chosen = [requested] if requested in pool else []
            rows = []
            for k in chosen:
                if k not in pool:
                    rows.append(
                        dict(
                            key=k, reason="고정 표본의 현재 공개 일봉·상장 분류 미확인"
                        )
                    )
                    continue
                raw, expected, detail = db.execute(
                    "SELECT inputs,digest,detail FROM result WHERE venue=? AND symbol=? AND currency=?",
                    k,
                ).fetchone()
                status = db.execute(
                    """SELECT price_check FROM checks.assessment WHERE experiment='primary'
                                      AND venue=? AND symbol=? AND currency=?""",
                    k,
                ).fetchone()
                row = dict(key=k, digest=expected)
                data = gzip.decompress(raw)
                if hashlib.sha256(data).hexdigest() != expected:
                    raise ValueError("공개 시세 입력 식별값이 일치하지 않습니다.")
                info = json.loads(data)
                row["source"] = info["source"]
                sessions = info["sessions"]
                day = meta["days"][market]
                bars, _ = quant.prepare(info["rows"], sessions, k[0], recover=True)
                needed = 253 + WINDOW
                bars = bars[-needed:]
                if tuple(info["key"]) != k:
                    raise ValueError("공개 시세 입력 식별값이 일치하지 않습니다.")
                if not status or status[0] != "confirmed":
                    row["reason"] = "종가 불일치·미확인"
                elif not meta.get("actions_source") or json.loads(detail)["actions"]:
                    row["reason"] = "기업행동 보류"
                elif (
                    not bars
                    or [b["day"] for b in bars] != sessions[-len(bars) :]
                    or bars[-1]["day"] != day
                ):
                    row["reason"] = "연속 시가·종가 부족"
                else:
                    row["bars"] = bars
                rows.append(row)
            groups[market] = rows
    return stamp, meta, groups


def hold_reason(item, key):
    if "reason" in item:
        return item["reason"]
    needed = (22 if key == "variance-cap" else 253) + WINDOW
    bars = item["bars"]
    if len(bars) < needed or any(b["open"] is None for b in bars[-WINDOW:]):
        return "연속 시가·종가 부족"
    return ""


def calculate(package):
    now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    with database(package) as db:
        cohort = db.execute(
            "SELECT * FROM cohort WHERE rule='public-stock-sample-v1'"
        ).fetchone()
        frozen = json.loads(cohort["members"]) if cohort else None
        stamp, meta, groups = read_panel(package, frozen=frozen)
        if cohort is None:
            members = {
                market: [r["key"] for r in rows] for market, rows in groups.items()
            }
            if not any(members.values()):
                raise ValueError("공개 상장 표본과 일봉 입력을 확인하세요.")
            db.execute(
                "INSERT INTO cohort VALUES(?,?,?,?)",
                ("public-stock-sample-v1", stamp, now, packed(members)),
            )
        active = [k for k in PRICE_IDS if current_state(db, k) == "연구 중"]
        ids = {}
        created = 0
        for key in sorted(active):
            markets = {}
            for market, sample in groups.items():
                rows, holds = [], Counter()
                for item in sample:
                    rec = {k: v for k, v in item.items() if k != "bars"}
                    reason = hold_reason(item, key)
                    if reason:
                        rec["reason"] = reason
                    if "reason" in rec:
                        holds[rec["reason"]] += 1
                    else:
                        bars = item["bars"]
                        fee = quant.costs(item["key"][0])
                        sim = simulate(bars, key, fee, 1)
                        hold = simulate(bars, "hold", fee, 1)
                        stress = simulate(bars, key, fee, 2)
                        double_hold = simulate(bars, "hold", fee, 2)
                        rec.update(
                            net=sim["net"],
                            dd=sim["dd"],
                            hold=hold["net"],
                            hold_dd=hold["dd"],
                            excess=sim["net"] - hold["net"],
                            stress=stress["net"] - double_hold["net"],
                            turnover=sim["turnover"],
                            first=bars[-WINDOW]["day"],
                            last=bars[-1]["day"],
                        )
                    rows.append(rec)
                valid = [r for r in rows if "net" in r]
                summary = (
                    {
                        f: median(r[f] for r in valid)
                        for f in (
                            "net",
                            "hold",
                            "excess",
                            "stress",
                            "dd",
                            "hold_dd",
                            "turnover",
                        )
                    }
                    if valid
                    else {}
                )
                markets[market] = dict(
                    n=len(valid),
                    sampled=len(sample),
                    held=dict(holds),
                    first=sorted({r["first"] for r in valid}),
                    summary=summary,
                    rows=rows,
                )
            out = dict(
                panel=stamp,
                days=meta["days"],
                cutoff=meta["cutoff"],
                markets=markets,
                version=CATALOG[key]["version"],
                spec=digest(CATALOG[key]),
                engine="public-study-2",
                sample=SAMPLE,
                horizon=WINDOW,
                costs={
                    m: vars(quant.costs(v)) for m, v in (("KR", "KRX"), ("US", "NYSE"))
                },
            )
            rid = digest([key, out])
            created += db.execute(
                "INSERT OR IGNORE INTO experiment VALUES(?,?,?,?,?,?)",
                (rid, key, out["version"], stamp, now, packed(out)),
            ).rowcount
            ids[key] = rid
        status = "모든 가격 연구 일시정지"
        if ids:
            status = "새 실험 저장" if created else "기존 실험과 입력 동일"
        db.execute(
            "INSERT OR REPLACE INTO refresh_status VALUES(1,?,?)",
            (now, status),
        )
        return ids


def summary(db, key):
    return [
        dict(id=r["id"], created=r["created"], result=json.loads(r["result"]))
        for r in db.execute(
            "SELECT id,created,result FROM experiment WHERE strategy=? ORDER BY created DESC,rowid DESC LIMIT 5",
            (key,),
        )
    ]


def current_state(db, key):
    return db.execute(
        "SELECT state FROM specification WHERE strategy=? AND version=?",
        (key, CATALOG[key]["version"]),
    ).fetchone()[0]


def refresh(package):
    try:
        return calculate(package)
    except (
        ValueError,
        OSError,
        sqlite3.Error,
        KeyError,
        TypeError,
        EOFError,
        zlib.error,
    ) as exc:
        # Preserve successful runs and expose only fixed failure descriptions.
        status = (
            str(exc)
            if isinstance(exc, ValueError)
            and str(exc)
            in (
                "해당 공개 일봉 또는 독립 종가 검증을 기다립니다.",
                "완료된 공개 일봉 실험이 없습니다.",
                "공개 시세 입력 식별값이 일치하지 않습니다.",
            )
            else "연구 입력 또는 저장소 점검 필요"
        )
        with database(package) as db:
            db.execute(
                "INSERT OR REPLACE INTO refresh_status VALUES(1,?,?)",
                (datetime.now(timezone.utc).isoformat(), status),
            )
        return {}


def arguments(commands):
    command = commands.add_parser("strategies", help="공개 연구 전략·실험·공시 관리")
    actions = command.add_subparsers(dest="strategy_action", required=True)
    actions.add_parser("list", help="전략 버전과 상태")
    actions.add_parser("run", help="최근 검증된 공개 일봉 실험")
    sub = actions.add_parser("state", help="로컬 연구 일시정지·재개")
    sub.add_argument(
        "strategy", choices=[k for k, v in CATALOG.items() if v["kind"] != "existing"]
    )
    sub.add_argument("state", choices=["연구 중", "일시정지"])
    hist = actions.add_parser("history", help="전략의 실행 이력과 시장별 중앙값")
    hist.add_argument("strategy", choices=PRICE_IDS)
    events = actions.add_parser("evidence", help="당시 공개된 인물·기관 자료 확인")
    events.add_argument("strategy", choices=tuple(EVENT_HOSTS))
    events.add_argument("--as-of", required=True)
    actions.add_parser(
        "import-event", help="검증된 공개 공시 표본 JSON을 표준입력으로 기록"
    )
    one = actions.add_parser("result", help="저장된 공개 실험을 전체 ID로 재조회")
    one.add_argument("run_id")


def command(package, args, stream):
    op = args.strategy_action
    if op == "run":
        ids = refresh(package)
        if not ids:
            with database(package) as db:
                status = db.execute(
                    "SELECT status FROM refresh_status WHERE id=1"
                ).fetchone()[0]
            if status != "모든 가격 연구 일시정지":
                raise ValueError(status)
        return ids
    with database(package) as db:
        if op == "state":
            state(db, args.strategy, args.state)
            return args.state
        if op == "evidence":
            return evidence(db, args.strategy, args.as_of)
        if op == "import-event":
            raw = stream.read(20001)
            if len(raw) > 20000:
                raise ValueError("공시 표본 크기를 확인하세요.")
            import_event(db, json.loads(raw))
            return "공개 공시 표본 저장 완료"
        if op == "result":
            row = db.execute(
                "SELECT result FROM experiment WHERE id=?", (args.run_id,)
            ).fetchone()
            if not row:
                raise ValueError("실험 ID를 확인하세요.")
            return json.loads(row[0])
        if op == "history":
            rows = db.execute(
                "SELECT id,version,panel,created,result FROM experiment WHERE strategy=? ORDER BY created DESC",
                (args.strategy,),
            )
            return [
                dict(
                    id=r["id"],
                    version=r["version"],
                    panel=r["panel"],
                    created=r["created"],
                    markets={
                        m: {k: v for k, v in g.items() if k != "rows"}
                        for m, g in json.loads(r["result"])["markets"].items()
                    },
                )
                for r in rows
            ]
        return [
            dict(
                strategy=k,
                title=v["title"],
                version=v["version"],
                state=(
                    "기존 엔진 연결"
                    if v["kind"] == "existing"
                    else current_state(db, k)
                ),
            )
            for k, v in CATALOG.items()
        ]
