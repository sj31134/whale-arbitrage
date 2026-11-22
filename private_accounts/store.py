"""Local snapshots of balances, with explicit valuation currencies and observation times."""
import csv
import io
import os
import re
import sqlite3
import stat
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

PROVIDERS = {"kis": "한국투자증권", "mirae": "미래에셋증권", "meritz": "메리츠증권",
             "namuh": "나무증권", "binance": "바이낸스", "upbit": "업비트"}
CRYPTO = ("binance", "upbit")
BROKERS = tuple(p for p in PROVIDERS if p not in CRYPTO)
ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DIR = Path.home() / "Library/Application Support/whale_tracking/accounts"
COLUMNS = ("symbol", "quantity", "currency", "market_value")
SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    provider TEXT NOT NULL, alias TEXT NOT NULL, registered INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY(provider, alias)
);
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY, provider TEXT NOT NULL, alias TEXT NOT NULL, as_of TEXT NOT NULL,
    UNIQUE(provider, alias, as_of), FOREIGN KEY(provider, alias) REFERENCES profiles(provider, alias)
);
CREATE TABLE IF NOT EXISTS holdings (
    snapshot INTEGER NOT NULL REFERENCES snapshots(id), symbol TEXT NOT NULL, currency TEXT NOT NULL,
    quantity TEXT NOT NULL, market_value TEXT, PRIMARY KEY(snapshot, symbol, currency)
);
"""


def timestamp(value):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.utcoffset() is None or dt > datetime.now(timezone.utc):
            raise ValueError
        return dt.astimezone(timezone.utc).isoformat(timespec="microseconds")
    except (ValueError, OverflowError) as exc:
        raise ValueError("기준시각에 시간대가 포함된 과거 또는 현재 ISO 8601 시각을 입력하세요.") from exc


def number(value):
    try:
        if not isinstance(value, (str, Decimal)) or len(str(value)) > 100:
            raise ValueError
        n = Decimal(value)
        if not n.is_finite() or n < 0 or n.adjusted() > 40 or n.as_tuple().exponent < -40:
            raise ValueError
        return n
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("수량·금액은 유한한 0 이상의 십진수여야 합니다.") from exc


def fixed(n):
    text = format(n, "f")
    return (text.rstrip("0").rstrip(".") if "." in text else text) if n else "0"


def holding(symbol, quantity, currency, value):
    symbol, currency = symbol.strip(), currency.strip().upper()
    if not (1 <= len(symbol) <= 64 and symbol[0].isalnum()
            and all(ch.isalnum() or ch in "._-" for ch in symbol)
            and re.fullmatch("[A-Z0-9]{2,12}", currency)):
        raise ValueError("종목코드 또는 평가통화를 확인하세요.")
    qty = number(quantity)
    val = None if value in (None, "") else fixed(number(value))
    if qty == 0 and val not in (None, "0"):
        raise ValueError("수량이 0인 종목에 평가액이 있습니다.")
    return symbol, currency, fixed(qty), val


def read_csv(path):
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("CSV는 8 MiB 이하여야 합니다.")
    raw = path.read_bytes()
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = raw.decode("cp949")
    reader = csv.DictReader(io.StringIO(decoded, newline=""), strict=True)
    if sorted(reader.fieldnames or []) != sorted(COLUMNS):
        raise ValueError("CSV 열은 symbol,quantity,currency,market_value 네 개여야 합니다.")
    rows = []
    for line in reader:
        if None in line or None in line.values():
            raise ValueError(f"CSV {reader.line_num}행의 열 수를 확인하세요.")
        rows.append(holding(*(line[key].strip() for key in COLUMNS)))
    if not rows:
        raise ValueError("빈 CSV입니다. 전량 처분 후 잔고는 수량 0인 행으로 표시하세요.")
    return rows


def exclude_from_mac_backup(*paths):
    if sys.platform != "darwin":
        return
    paths = [str(p) for p in paths]
    env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    def excluded():
        status = subprocess.run(["/usr/bin/tmutil", "isexcluded", *paths], capture_output=True, env=env)
        lines = status.stdout.splitlines()
        return status.returncode == 0 and len(lines) == len(paths) and all(
            line.startswith(b"[Excluded]") for line in lines)
    if excluded():
        return
    result = subprocess.run(["/usr/bin/tmutil", "addexclusion", *paths], capture_output=True, env=env)
    if result.returncode or not excluded():
        raise ValueError("Time Machine의 개인 계좌 파일 제외 설정을 확인하세요.")


def private_path(directory, write):
    directory = Path(directory)
    if not directory.is_absolute() or directory.resolve() != directory or ROOT in (*directory.parents, directory):
        raise ValueError("개인 저장 경로는 저장소 밖의 실제 디렉터리여야 합니다.")
    db = directory / "balances.sqlite3"
    if write:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not directory.exists():
        return None
    info = directory.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError("개인 저장 폴더의 소유자 및 권한(0700)을 확인하세요.")
    if write:
        if directory == PRIVATE_DIR:
            exclude_from_mac_backup(directory)
        fd = os.open(db, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
    for path in (db, *(directory / (db.name + s) for s in ("-journal", "-wal", "-shm"))):
        if path.is_symlink():
            raise ValueError("개인 DB 경로에 심볼릭 링크가 있습니다.")
        if path.exists():
            info = path.stat()
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
                    or stat.S_IMODE(info.st_mode) & 0o077):
                raise ValueError("개인 DB 파일의 소유자 및 권한(0600)을 확인하세요.")
    return db if db.exists() else None


@contextmanager
def database(directory, write=False):
    path = private_path(directory, write)
    if path is None:
        yield None
        return
    con = sqlite3.connect(path.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=10)
    try:
        con.execute("PRAGMA foreign_keys=ON")
        if write:
            con.executescript(SCHEMA)
            con.execute("BEGIN IMMEDIATE")
        else:
            con.execute("BEGIN")
        with con:
            yield con
    finally:
        con.close()


def registered(con, provider, alias, enabled):
    con.execute("""INSERT INTO profiles VALUES (?, ?, ?) ON CONFLICT(provider, alias)
                   DO UPDATE SET registered=excluded.registered""", (provider, alias, int(enabled)))


def save(con, provider, alias, when, rows):
    rows = sorted(rows, key=lambda row: row[:2])
    if len({r[:2] for r in rows}) != len(rows):
        raise ValueError("동일 종목·통화가 중복되었습니다. 같은 계좌의 잔고를 한 행으로 합치세요.")
    rows = [r for r in rows if r[2] != "0"]
    con.execute("INSERT OR IGNORE INTO profiles(provider,alias) VALUES(?,?)", (provider, alias))
    key = (provider, alias, when)
    old = con.execute("SELECT id FROM snapshots WHERE provider=? AND alias=? AND as_of=?", key).fetchone()
    if old:
        if positions(con, old[0]) != rows:
            raise ValueError("같은 계좌·시각에 다른 잔고가 이미 있습니다.")
        return
    snapshot = con.execute("INSERT INTO snapshots(provider,alias,as_of) VALUES(?,?,?)", key).lastrowid
    con.executemany("INSERT INTO holdings VALUES(?,?,?,?,?)", ((snapshot, *r) for r in rows))


def positions(con, snapshot):
    return con.execute("""SELECT symbol,currency,quantity,market_value FROM holdings
                          WHERE snapshot=? ORDER BY symbol,currency""", (snapshot,)).fetchall()


def profiles(con):
    result = []
    for provider in PROVIDERS:
        found = [] if con is None else con.execute("""
            SELECT p.alias, p.registered, s.id, s.as_of FROM profiles p LEFT JOIN snapshots s ON s.id=(
                SELECT id FROM snapshots WHERE provider=p.provider AND alias=p.alias ORDER BY as_of DESC LIMIT 1)
            WHERE p.provider=? ORDER BY p.alias""", (provider,)).fetchall()
        result.extend((provider, *r) for r in (found or [("main", 0, None, None)]))
    return result


def agent_view(con, provider, alias):
    snapshot = next(((sid, when) for p, a, _, sid, when in profiles(con)
                     if p == provider and a == alias and sid is not None), None)
    if snapshot is None:
        raise ValueError("이 계좌의 저장된 잔고가 없습니다.")
    return weighted_view(positions(con, snapshot[0]), snapshot[1])


def weighted_view(rows, when):
    totals, missing = {}, set()
    with localcontext() as ctx:
        ctx.prec = 100
        for _, currency, _, value in rows:
            if value is None:
                missing.add(currency)
            else:
                totals[currency] = totals.get(currency, Decimal(0)) + Decimal(value)
        weights = []
        for symbol, currency, _, value in rows:
            weight = None
            if currency not in missing and totals.get(currency):
                weight = fixed((100 * Decimal(value) / totals[currency]).quantize(Decimal(".0001")))
            weights.append(dict(symbol=symbol, currency=currency, weight_pct=weight))
    return dict(as_of=when, holdings=weights)
