"""Local, allowlisted research archives; recovery always creates a new workspace."""
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from agents import intelligence as intel
from . import daily_review, local_sources, reports, research_book as book

FILES = (book.DB, reports.FILE)
FORMAT = 1


def protected(package, name):
    parent = package / ".local"
    local_sources.secure_directory(parent)
    folder = parent / name
    local_sources.secure_directory(folder)
    return folder


def digest(path):
    h = hashlib.sha256()
    with local_sources.open_private(path) as f:
        for block in iter(lambda: f.read(131072), b""):
            h.update(block)
    return h.hexdigest()


def put(path, data):
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def validate(folder):
    db = folder / book.DB
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as con:
        con.execute("PRAGMA trusted_schema=OFF")
        if con.execute("PRAGMA integrity_check").fetchall() != [("ok",)] or con.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("연구 DB 무결성 점검에 실패했습니다.")
        ids = {row[0] for row in con.execute("SELECT DISTINCT report FROM ideas")}
        con.execute("SELECT idea,assessment FROM outcomes LIMIT 0")
    with local_sources.open_private(folder / reports.FILE) as f:
        ledger = json.load(f)
    if not ids <= ledger.keys() or any(key != row["id"] or not set(row["inputs"]) <= ledger.keys()
                                      for key, row in ledger.items()):
        raise ValueError("연결된 보고서가 누락됐습니다.")


def snapshot(package):
    parent = protected(package, "research-archives")
    name = datetime.now(intel.KST).strftime("%Y%m%d-%H%M%S-%f")
    temp = Path(tempfile.mkdtemp(dir=parent))
    try:
        # Initialize an empty journal on first use; never back up the personal account database.
        with book.database(package, True):
            pass
        put(temp / book.DB, b"")
        with book.database(package) as src:
            dst = sqlite3.connect(temp / book.DB)
            try:
                src.backup(dst)
            finally:
                dst.close()
        put(temp / reports.FILE, json.dumps(reports.read(package), ensure_ascii=False).encode())
        validate(temp)
        manifest = {"version": FORMAT, "files": {n: digest(temp / n) for n in FILES}}
        put(temp / "manifest.json", json.dumps(manifest).encode())
        temp.rename(parent / name)
        return name
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def recover(package, name):
    if not re.fullmatch(r"\d{8}-\d{6}-\d{6}", name):
        raise ValueError("복구할 스냅샷 ID를 확인하세요.")
    source = protected(package, "research-archives") / name
    if not source.is_dir() or source.is_symlink():
        raise ValueError("지정한 연구 스냅샷을 찾을 수 없습니다.")
    with local_sources.open_private(source / "manifest.json") as f:
        manifest = json.load(f)
    if manifest.get("version") != FORMAT or set(manifest["files"]) != set(FILES):
        raise ValueError("지원하는 연구 스냅샷 형식을 확인하세요.")
    parent = protected(package, "research-recovered")
    temp = Path(tempfile.mkdtemp(dir=parent))
    try:
        recovered = temp / ".local"
        local_sources.secure_directory(recovered)
        for n in FILES:
            with local_sources.open_private(source / n) as stream:
                put(recovered / n, stream.read())
            if digest(recovered / n) != manifest["files"][n]:
                raise ValueError("스냅샷 체크섬이 일치하지 않습니다.")
        validate(recovered)
        target = parent / name
        if target.exists() or target.is_symlink():
            raise ValueError("같은 ID의 독립 복구본이 이미 존재합니다.")
        temp.rename(target)
        return target
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def market_note(package, day):
    """Write only the explicitly supplied public flows, never a portfolio or desk memo."""
    from datetime import date
    day = date.fromisoformat(day).isoformat()
    review = intel.private_json(package, daily_review.FILE, {}).get(day)
    if review is None:
        raise ValueError("해당 날짜의 저장된 일일 검토가 없습니다.")
    rows = daily_review.read_flows(io.StringIO(json.dumps(review.get("flows", []))),
                                   datetime.now(intel.KST).date())
    lines = [f"# {day} 공개 시장 수급", "", f"일일 검토 저장시각 {review['generated']}", ""]
    if not rows:
        lines.append("이 검토에 등록된 공개 수급 자료가 없습니다.")
    for row in rows:
        # Indented literal blocks keep imported text inert in Markdown viewers.
        fields = ("market", "period", "as_of", "metric", "theme", "net", "unit", "source")
        lines.extend(["    " + " · ".join(" ".join(row[k].split()) for k in fields), ""])
    parent = protected(package, "market-notes")
    with tempfile.NamedTemporaryFile(dir=parent, delete=False) as f:
        temp = Path(f.name)
    try:
        temp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(temp, parent / (day + ".md"))
    finally:
        temp.unlink(missing_ok=True)
