"""Prospective research decisions, separate from account balances and order execution."""

import json
import ipaddress
import os
import re
import sqlite3
import stat
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

from agents import intelligence as intel
from . import local_sources, reports, store

DB = "research.sqlite3"
SCHEMA = """
CREATE TABLE IF NOT EXISTS ideas (
    id TEXT PRIMARY KEY, created TEXT NOT NULL, due TEXT NOT NULL, report TEXT NOT NULL,
    assumptions TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outcomes (
    idea TEXT PRIMARY KEY REFERENCES ideas(id), recorded TEXT NOT NULL, assessment TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ideas_due ON ideas(due);
CREATE TABLE IF NOT EXISTS observations (
    idea TEXT PRIMARY KEY REFERENCES ideas(id), recorded TEXT NOT NULL, quote TEXT NOT NULL
);
"""
WEIGHTS = (Decimal("0.2"), Decimal("0.5"), Decimal("0.3"))
VERDICTS = ("가설 지지", "가설 기각", "판단 보류")


@contextmanager
def database(package, write=False):
    folder = package / ".local" if package else None
    if not folder or (not write and not folder.exists()):
        if write:
            raise ValueError("로컬 프로젝트를 확인하세요.")
        yield None
        return
    local_sources.secure_directory(folder)
    path = folder / DB
    if write and package == intel.ROOT / "private_accounts":
        store.exclude_from_mac_backup(folder)
    for name in (path.name, *(path.name + end for end in ("-wal", "-shm", "-journal"))):
        candidate = folder / name
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or
                info.st_nlink != 1 or stat.S_IMODE(info.st_mode) & 0o077):
            raise ValueError("연구 DB 파일 권한을 확인하세요.")
    if write:
        os.close(os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600))
    elif not path.exists():
        yield None
        return
    con = sqlite3.connect(path.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=10)
    try:
        con.execute("PRAGMA foreign_keys=ON")
        if write:
            con.executescript(SCHEMA)
        con.execute("BEGIN IMMEDIATE" if write else "BEGIN")
        with con:
            yield con
    finally:
        con.close()


def amount(fields, key, minimum=0, positive=False):
    raw = fields.get(key, "").strip()
    if not re.fullmatch(r"-?\d{1,15}(?:\.\d{1,12})?", raw):
        raise ValueError("수치 형식과 소수 자릿수를 확인하세요.")
    try:
        n = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("유효한 숫자를 입력하세요.") from exc
    if n < minimum or (positive and n == 0):
        raise ValueError("가격·비용의 범위를 확인하세요.")
    return store.fixed(n)


def note(fields, key, limit=300):
    value = fields.get(key, "").strip()
    if not 0 < len(value) <= limit or any(ord(c) < 32 and c != "\n" for c in value):
        raise ValueError("필수 문구와 길이를 확인하세요.")
    return value


def public_url(fields, key):
    value = note(fields, key, 1200)
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("근거의 공개 HTTPS 원문을 입력하세요.")
    host = parsed.hostname.rstrip(".").lower()
    try:
        private = not ipaddress.ip_address(host).is_global
    except ValueError:
        private = "." not in host or host.endswith((".localhost", ".local", ".internal"))
    if private:
        raise ValueError("인터넷에 공개된 가격 원문을 입력하세요.")
    return value


def metrics(a):
    entry = Decimal(a["entry"])
    drag = (Decimal(a["fees"]) + Decimal(a["slip"])) / 100
    bear, base, bull = [(Decimal(a[key]) / entry - 1) * 100 - drag
                        for key in ("bear", "base", "bull")]
    expected = sum(p * r for p, r in zip(WEIGHTS, (bear, base, bull)))
    payoff = (WEIGHTS[2] * bull + WEIGHTS[1] * base) / (-WEIGHTS[0] * bear) if bear < 0 <= base else None
    margin = (1 - entry / Decimal(a["base"])) * 100
    qualifies = expected >= 12 and payoff is not None and payoff >= 3 and margin >= 20
    return dict(expected=expected, bear=bear, base=base, bull=bull, margin=margin,
                payoff=payoff, qualifies=qualifies)


def record(package, fields):
    key = fields.get("idea", "")
    if not re.fullmatch("[0-9a-f]{32}", key):
        raise ValueError("양식을 새로 열어 주세요.")
    report = fields.get("report", "")
    ledger = reports.read(package)
    if report not in ledger or not ledger[report]["sources"]:
        raise ValueError("근거가 있는 게시 보고서를 선택하세요.")
    now = datetime.now(intel.KST)
    due = date.fromisoformat(fields.get("due", ""))
    a = {s: note(fields, s) for s in ("asset", "benchmark", "catalyst", "invalidate")}
    a["currency"] = note(fields, "currency", 12).upper()
    if not re.fullmatch("[A-Z]{3}", a["currency"]):
        raise ValueError("세 글자 평가통화 코드를 입력하세요.")
    for s in ("entry", "base", "benchmark_entry"):
        a[s] = amount(fields, s, positive=True)
    for s in ("bear", "bull", "fees", "slip"):
        a[s] = amount(fields, s)
    if not Decimal(a["bear"]) <= Decimal(a["base"]) <= Decimal(a["bull"]):
        raise ValueError("약세 ≤ 기준 ≤ 강세 목표값을 확인하세요.")
    if Decimal(a["fees"]) + Decimal(a["slip"]) >= 10000:
        raise ValueError("왕복 비용이 기준금액의 100% 이상입니다.")
    a["observed"] = store.timestamp(note(fields, "observed", 64))
    a["price_source"] = public_url(fields, "price_source")
    a["benchmark_source"] = public_url(fields, "benchmark_source")
    payload = json.dumps(a, sort_keys=True, ensure_ascii=False)
    with database(package, True) as con:
        old = con.execute("SELECT due,report,assumptions FROM ideas WHERE id=?", (key,)).fetchone()
        if old:
            if old != (due.isoformat(), report, payload):
                raise ValueError("같은 제출에 다른 가정이 있습니다.")
            return
        if due <= now.date():
            raise ValueError("등록일 이후의 평가 예정일을 선택하세요.")
        con.execute("INSERT INTO ideas VALUES (?,?,?,?,?)",
                    (key, now.isoformat(), due.isoformat(), report, payload))


def mark(package, fields, opening=False):
    key = fields.get("idea", "")
    a = {s: amount(fields, s) for s in ("exit", "benchmark_exit")}
    a["observed"] = store.timestamp(note(fields, "observed", 64))
    if opening:
        if Decimal(a["exit"]) <= 0 or Decimal(a["benchmark_exit"]) <= 0:
            raise ValueError("추적 시작값은 0보다 커야 합니다.")
    else:
        a["verdict"] = fields.get("verdict", "")
        if a["verdict"] not in VERDICTS:
            raise ValueError("가설 판정을 선택하세요.")
        a["reason"] = note(fields, "reason", 800)
    a.update(source=public_url(fields, "source"),
             benchmark_source=public_url(fields, "benchmark_source"))
    payload = json.dumps(a, sort_keys=True, ensure_ascii=False)
    with database(package, True) as con:
        start = con.execute("SELECT created FROM ideas WHERE id=?", (key,)).fetchone() if opening else (
            con.execute("SELECT recorded FROM observations WHERE idea=?", (key,)).fetchone())
        if not start or datetime.fromisoformat(a["observed"]) <= datetime.fromisoformat(start[0]):
            raise ValueError("직전 등록 이후 같은 시점에 관측한 두 평가값을 입력하세요.")
        table, column = ("observations", "quote") if opening else ("outcomes", "assessment")
        old = con.execute(f"SELECT {column} FROM {table} WHERE idea=?", (key,)).fetchone()
        if old:
            if old[0] != payload:
                raise ValueError("이미 다른 값으로 확정된 관측입니다.")
            return
        con.execute(f"INSERT INTO {table} VALUES (?,?,?)",
                    (key, datetime.now(intel.KST).isoformat(), payload))


def entries(package):
    with database(package) as con:
        if con is None:
            return []
        rows = con.execute("""SELECT id,created,due,report,assumptions,assessment,outcomes.recorded,quote
            FROM ideas LEFT JOIN outcomes ON outcomes.idea=id LEFT JOIN observations ON observations.idea=id
            ORDER BY assessment IS NOT NULL,due,created,id""").fetchall()
    return [dict(id=k, created=c, due=d, report=r, a=json.loads(a),
                 result=json.loads(result) if result else None, recorded=when,
                 start=json.loads(start) if start else None)
            for k, c, d, r, a, result, when, start in rows]


def performance(row):
    a, out = row["a"], row["result"]
    drag = (Decimal(a["fees"]) + Decimal(a["slip"])) / 100
    start = row["start"]
    net = (Decimal(out["exit"]) / Decimal(start["exit"]) - 1) * 100 - drag
    benchmark = (Decimal(out["benchmark_exit"]) / Decimal(start["benchmark_exit"]) - 1) * 100
    return net, benchmark, net - benchmark
