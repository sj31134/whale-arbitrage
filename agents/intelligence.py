"""Collect public observations, then join them to private positions entirely on this Mac."""

import csv
import fcntl
import hashlib
import json
import os
import socket
import ssl
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from xml.etree.ElementTree import ParseError

from private_accounts import local_sources, store
from . import analyst_feeds as feeds
from .portfolio import (
    DOMAINS,
    load_roles,
    normalize as norm,
    portfolio_accounts,
    public_identities,
    responsibilities,
)


LABELS = dict(zip(DOMAINS, ("고래", "코인", "부동산", "주식", "미국 소형·고베타")))
ROOT = store.ROOT
KST = timezone(timedelta(hours=9))
CACHE = "analyst_observations.json"
CAPTURE_FILE = "public_source_captures.json"
NOTES = "investment_notes.json"
MARKET_CHECKS = "market_checkpoints.json"


SOURCE_ROLES = {
    "upbit": {"crypto", "whale"}, "whale": {"crypto", "whale"},
    "dart": {"equities"}, "edgar": {"equities", "us_small_cap_high_beta"},
    "dart_recent": {"equities"},
    "registry": {"equities", "us_small_cap_high_beta", "real_estate"},
    "seoul_apt_supply_annual_units": {"real_estate"},
}


def catalog():
    return sorted(
        (json.loads(p.read_text()) for p in (ROOT / "data/analysts").glob("*/analyst.json")),
        key=lambda c: c["order"],
    )


def private_json(package, name, default):
    if package is None:
        return default
    path = package / ".local" / name
    if path.is_symlink():
        raise ValueError("개인 설정 경로를 확인하세요.")
    if not path.exists():
        return default
    local_sources.secure_directory(path.parent)
    with local_sources.open_private(path) as stream:
        return json.load(stream)


def update_json(package, name, default, update):
    folder = package / ".local"
    local_sources.secure_directory(folder)
    if package == ROOT / "private_accounts":
        store.exclude_from_mac_backup(folder)
    lock = os.open(folder, os.O_RDONLY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        doc = update(private_json(package, name, default))
        with tempfile.NamedTemporaryFile(dir=folder, mode="w", encoding="utf-8", delete=False) as f:
            try:
                json.dump(doc, f, ensure_ascii=False, allow_nan=False)
                f.flush()
                os.fsync(f.fileno())
                os.replace(f.name, folder / name)
            finally:
                Path(f.name).unlink(missing_ok=True)
    finally:
        os.close(lock)


def collect(package, selected=None, offline=False, fetcher=feeds.fetch, *, domains=None):
    definitions = catalog()
    if selected and selected not in {c["id"] for c in definitions}:
        raise ValueError("알 수 없는 정보 범주입니다.")
    if domains is not None and (not domains or not set(domains) <= set(DOMAINS)):
        raise ValueError("담당 분야를 확인하세요.")
    now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    jobs = [
        (c["id"], s)
        for c in definitions
        if not selected or c["id"] == selected
        for s in c["sources"]
        if s["kind"] != "portfolio" and (not offline or "url" not in s)
        and (domains is None or set(domains).intersection(c["agents"], SOURCE_ROLES.get(s["id"], DOMAINS)))
    ]

    def run(job):
        cat, s = job
        key = cat + "/" + s["id"]
        try:
            items = feeds.read_public(s, fetcher(s), now) if "url" in s else feeds.local_feed(s, ROOT)
            if not items:
                raise feeds.SourceUnavailable("관측값 없음")
            unique = {(r["title"], r["as_of"], r["origin"]): r for r in items}
            return key, dict(
                attempt=now,
                collected=datetime.now(timezone.utc).isoformat(timespec="microseconds"),
                status="수집 완료",
                via="공개 API" if "url" in s else "로컬 연구 자료",
                items=list(unique.values()),
            )
        except feeds.SourceUnavailable as e:
            reason = str(e)
        except HTTPError as e:
            reason = f"HTTP {e.code}"
        except URLError as e:
            if isinstance(e.reason, socket.gaierror):
                reason = "원천 도메인 이름 조회 실패(DNS)"
            elif isinstance(e.reason, ssl.SSLError):
                reason = "원천 TLS 연결 실패"
            else:
                reason = "원천 네트워크 연결 실패"
        except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError, ArithmeticError, ParseError, csv.Error):
            reason = "연결 또는 원천 형식 확인"
        return key, dict(attempt=now, status=reason)

    # No private argument is passed to a feed. A failing source cannot discard the others.
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = dict(pool.map(run, jobs))

    def merge(cache):
        for key, row in results.items():
            old = cache.get(key, {})
            if row["attempt"] >= old.get("attempt", ""):
                cache[key] = {**old, **row}
        return cache

    if results:
        update_json(package, CACHE, {}, merge)
    return {k: v["status"] for k, v in results.items()}


def import_capture(package, source, checked_at, raw_rows):
    stamp = store.timestamp(checked_at)
    items = feeds.captured_observations(source, raw_rows, datetime.fromisoformat(stamp))

    def save(captures):
        old = captures.get(source, {})
        if old.get("collected", "") > stamp:
            raise ValueError("이미 더 최근에 확인한 공개 목록이 있습니다.")
        if old.get("collected") == stamp and old["items"] != items:
            raise ValueError("같은 확인시각의 원천 내용이 다릅니다.")
        if source in feeds.FRED_CAPTURES and old.get("items") and items[0]["as_of"] < old["items"][0]["as_of"]:
            raise ValueError("이전 기준일의 FRED 자료입니다.")
        if source in ("upbit", "upbit_sample", "FX_USDKRW"):
            previous = {r["title"]: r["as_of"] for r in old.get("items", [])}
            if any(r["as_of"] < previous.get(r["title"], "") for r in items):
                raise ValueError("기존 체결보다 오래된 원화마켓 시세가 섞여 있습니다.")
        captures[source] = dict(items=items, collected=stamp)
        return captures

    update_json(package, CAPTURE_FILE, {}, save)
    return len(items)


def position_id(provider, account, symbol, currency):
    return hashlib.sha256(
        json.dumps([provider, account, symbol, currency], ensure_ascii=False).encode()
    ).hexdigest()


def outdated(as_of, days, today):
    if len(as_of) == 10:
        observed_day = date.fromisoformat(as_of)
    else:
        observed_day = datetime.fromisoformat(as_of.replace("Z", "+00:00")).astimezone(KST).date()
    age = (today - observed_day).days
    return age < 0 or age > days


def latest_market_check(package):
    checks = private_json(package, MARKET_CHECKS, {})
    return checks[max(checks)] if checks else None


def record_market_check(package, cutoff, rows):
    """Save verified public benchmarks separately from balances, at their actual observation times."""
    now = datetime.now(KST)
    if cutoff.tzinfo is None or cutoff > now or not rows:
        raise ValueError("기준시각과 관측 자료를 확인하세요.")
    allowed = set(next(c["agents"] for c in catalog() if c["id"] == "market_flow"))
    for r in rows:
        observed = datetime.fromisoformat(r["as_of"])
        known = datetime.fromisoformat(r["known_at"])
        if (observed.tzinfo is None or known.tzinfo is None or not observed <= known <= cutoff
                or not r["domains"] or not set(r["domains"]) <= allowed or not r["origin"].startswith("https://")):
            raise ValueError("관측·이용 가능 시각과 공개 원문을 확인하세요.")
    stamp = cutoff.astimezone(KST).isoformat(timespec="seconds")
    record = dict(cutoff=stamp, verified_at=now.isoformat(timespec="seconds"), rows=rows)
    update_json(package, MARKET_CHECKS, {}, lambda history: {**history, stamp: record})


def board(directory, package, *, include_pnl=False, quote_book=None, live=False):
    if live and quote_book is None:
        from private_accounts import live_valuation
        quote_book = live_valuation.read(package)
    accounts = portfolio_accounts(directory, package, include_pnl=include_pnl, quote_book=quote_book)
    roles = load_roles(package) if package else {}
    cache = private_json(package, CACHE, {})
    captures = private_json(package, CAPTURE_FILE, {})
    notes = private_json(package, NOTES, {})
    tags = notes.get("tags", {})
    today = datetime.now(KST).date()
    categories = {}
    for cat in catalog():
        cid = cat["id"]
        rows, sources = [], []
        for s in cat["sources"]:
            hit = cache.get(cid + "/" + s["id"], {})
            observations = hit.get("items", [])
            stale = [outdated(r["as_of"], cat["stale_days"], today) for r in observations]
            sources.append(
                dict(
                    source_id=s["id"],
                    label=s["label"],
                    status=hit.get("status", "미수집"),
                    attempt=hit.get("attempt"),
                    collected=hit.get("collected"),
                    via=hit.get("via"),
                    count=len(observations),
                    stale=sum(stale),
                )
            )
            for r, old in zip(observations, stale):
                rows.append(
                    dict(r, stale=old, source_id=s["id"],
                         source=s["label"] + (" · " + hit["via"] if hit.get("via") else ""))
                )
        for source, (category, label) in feeds.CAPTURES.items():
            if category != cid or source not in captures:
                continue
            capture = captures[source]
            imported = [dict(r, source_id=source, source=label,
                             stale=outdated(r["as_of"], cat["stale_days"], today)) for r in capture["items"]]
            sources.append(dict(source_id=source, label=label, status="수집 완료",
                                count=len(imported), stale=sum(r["stale"] for r in imported),
                                attempt=capture["collected"], collected=capture["collected"], via="공식 화면 확인"))
            # One price per market, one filing per receipt across automatic and inspected sources.
            comparable = ({"dart", "dart_recent"} if source == "dart_recent" else
                          {"upbit", "upbit_sample"} if source in {"upbit", "upbit_sample"} else {source})
            merged = {}
            for r in [*rows, *imported]:
                if r["source_id"] in comparable:
                    key = r["title"] if source in {"upbit", "upbit_sample"} else r["origin"]
                    if (key not in merged or merged[key]["as_of"] < r["as_of"]
                            or (source in feeds.FRED_CAPTURES and merged[key]["as_of"] == r["as_of"]
                                and capture["collected"] >= cache.get(cid + "/" + source, {}).get("collected", ""))):
                        merged[key] = r
            rows = [r for r in rows if r["source_id"] not in comparable] + list(merged.values())
        categories[cid] = dict(cat, observations=rows, runs=sources)
    check = latest_market_check(package)
    if check:
        category = categories["market_flow"]
        saved = []
        for row in check["rows"]:
            saved.append(dict(row, subjects=[], source="공개 시점 점검",
                              stale=outdated(row["as_of"], category["stale_days"], today)))
        category["observations"].extend(saved)
        category["runs"].append(dict(source_id="market_checkpoint", label="공개 시장 기준시각 점검",
            status="수집 완료", attempt=check["verified_at"], collected=check["verified_at"], via="공개 원문 대조",
            count=len(saved), stale=sum(r["stale"] for r in saved)))
    for item in notes.get("evidence", []):
        c = categories[item["category"]]
        c["observations"].append(
            dict(item, source="로컬 등록", stale=outdated(item["as_of"], c["stale_days"], today))
        )

    positions = []
    for a in accounts:
        largest = {}
        valued_at = {}
        for mark in a.get("marks", []):
            if mark["price"] is not None:
                ccy = mark["currency"]
                stamps = [s for s in (valued_at.get(ccy), mark["at"], mark["fx_at"], a["as_of"]) if s]
                valued_at[ccy] = max(stamps, key=datetime.fromisoformat)
        for holding in a["holdings"]:
            w = holding["weight_pct"]
            if w is not None:
                currency = holding["currency"]
                largest[currency] = max(Decimal(w), largest.get(currency, Decimal(0)))
        for h in a["holdings"]:
            p, alias, symbol = a["provider"], a["account"], h["symbol"]
            pid = position_id(p, alias, symbol, h["currency"])
            explicit = roles.get((p, alias, symbol))
            tasks = responsibilities(p, symbol, explicit)
            subjects = {norm(x) for x in [symbol, *tags.get(pid, [])]}
            if p not in store.CRYPTO:
                known = public_identities().get(norm(symbol))
                if known and known[0] in tasks:
                    subjects.update(map(norm, known[1]))
            direct, context = {}, {}
            for cid, c in categories.items():
                associated = bool(set(tasks) & set(c["agents"]))
                hit, general = [], []
                for r in c["observations"]:
                    if r.get("target"):
                        if r["target"] == pid:
                            hit.append(r)
                        continue
                    if not associated:
                        continue
                    if r.get("domains") and not set(r["domains"]) & set(tasks):
                        continue
                    if subjects.intersection(norm(v) for v in r["subjects"]):
                        hit.append(r)
                    elif not r["subjects"]:
                        general.append(r)
                if hit:
                    direct[cid] = hit
                if general:
                    context[cid] = general
            w = h["weight_pct"]
            share_note = f"해당 계좌의 {h['currency']} 평가통화 내 비중"
            if w is not None and largest.get(h["currency"]) == Decimal(w):
                share_note += " · 계좌·통화 내 최대 비중"
            deadlines = [r for r in notes.get("cash_dates", []) if r["position"] == pid]
            if deadlines:
                due = min(deadlines, key=lambda r: r["day"])
                share_note += f" · 등록 현금 일정 {len(deadlines)}건, 첫 기한 {due['day']} ({due['amount']} {due['currency']})"
            exposure = feeds.observation(
                symbol, f"{w}%" if w is not None else "평가 누락", valued_at.get(h["currency"], a["as_of"]),
                "로컬 시세 재평가" if h["currency"] in valued_at else a["source"], share_note
            )
            exposure.update(
                target=pid,
                source="로컬 보유",
                stale=outdated(exposure["as_of"], categories["exposure"]["stale_days"], today),
            )
            direct.setdefault("exposure", []).append(exposure)
            positions.append(
                dict(
                    h,
                    id=pid,
                    provider=p,
                    account=alias,
                    as_of=a["as_of"],
                    valuation_as_of=exposure["as_of"],
                    tasks=tasks,
                    role=explicit,
                    tags=tags.get(pid, []),
                    direct=direct,
                    context=context,
                )
            )
    # Repeated labels are a review cue, not proof of identical instruments across markets.
    repeated = {}
    for p in positions:
        repeated.setdefault(norm(p["symbol"]), set()).add((p["provider"], p["account"]))
    for p in positions:
        count = len(repeated[norm(p["symbol"])])
        if count > 1:
            p["direct"]["exposure"][-1]["analysis"] += f" · 같은 종목 표기 {count}개 계좌, 중복 노출 확인"
    # Private exposure observations are already joined by position above.
    categories["exposure"]["observations"].extend(p["direct"]["exposure"][-1] for p in positions)
    exp = categories["exposure"]["runs"][0]
    exp.update(
        status="로컬 계산" if accounts else "계좌 자료 없음",
        count=len(positions),
        stale=sum(outdated(p["as_of"], categories["exposure"]["stale_days"], today) for p in positions),
    )
    return dict(
        accounts=accounts, positions=positions, categories=categories, cash_dates=notes.get("cash_dates", [])
    )


def manage(directory, package, fields):
    action = fields["action"]
    categories = {c["id"] for c in catalog()}
    pid = fields.get("position", "")
    if action == "refresh":
        selected = fields.get("category") or None
        collect(package, selected)
        return
    if action == "remove-date":
        key = fields["entry"]

        def remove(doc):
            doc["cash_dates"] = [r for r in doc.get("cash_dates", []) if r["id"] != key]
            return doc

        update_json(package, NOTES, {}, remove)
        return
    holdings = {
        position_id(a["provider"], a["account"], h["symbol"], h["currency"]): (a, h)
        for a in portfolio_accounts(directory, package)
        for h in a["holdings"]
    }
    if pid not in holdings:
        raise ValueError("현재 보유 종목을 다시 선택하세요.")
    a, h = holdings[pid]
    if action == "role":
        role = fields["role"]
        if role not in (*DOMAINS[1:], "auto", "cash", "other"):
            raise ValueError("담당 분야를 확인하세요.")
        key = dict(provider=a["provider"], account=a["account"], symbol=h["symbol"])

        def assign(rows):
            keep = [r for r in rows if any(r[k] != v for k, v in key.items())]
            if role != "auto":
                keep.append(dict(key, role=role))
            return keep

        update_json(package, "agent_roles.json", [], assign)
        return
    if action == "tags":
        values = list(dict.fromkeys(x.strip() for x in fields["tags"].split(",") if x.strip()))
        if len(values) > 12 or any(len(x) > 80 for x in values):
            raise ValueError("연결어의 개수 또는 길이를 확인하세요.")

        def save_tags(doc):
            doc.setdefault("tags", {})[pid] = values
            return doc

        update_json(package, NOTES, {}, save_tags)
        return
    if action == "evidence":
        cid, title, url = fields["category"], fields["title"].strip(), fields["source"].strip()
        if (
            cid not in categories
            or not title
            or len(title) > 200
            or len(url) > 800
            or urlsplit(url).scheme != "https"
            or not urlsplit(url).hostname
        ):
            raise ValueError("근거 제목과 HTTPS 원문 주소를 확인하세요.")
        day = date.fromisoformat(fields["day"])
        if day > datetime.now(KST).date():
            raise ValueError("자료 기준일을 확인하세요.")
        item = feeds.observation(title, fields["value"].strip(), day, url, fields["analysis"].strip())
        if not item["value"] or not item["analysis"]:
            raise ValueError("관측값과 해석을 입력하세요.")
        item.update(target=pid, category=cid)

        def add(doc):
            items = doc.setdefault("evidence", [])
            items[:] = [
                r
                for r in items
                if (r["target"], r["category"], r["origin"], r["as_of"], r["title"])
                != (pid, cid, url, day.isoformat(), title)
            ]
            items.append(item)
            return doc

        update_json(package, NOTES, {}, add)
        return
    if action == "cash-date":
        day = date.fromisoformat(fields["day"]).isoformat()
        amount = store.fixed(store.number(fields["amount"]))
        label = fields["title"].strip()
        if not label or len(label) > 120 or Decimal(amount) <= 0:
            raise ValueError("일정명과 양의 금액을 입력하세요.")
        key = position_id(a["provider"], a["account"], label + day, h["currency"])
        entry = dict(
            id=key,
            provider=a["provider"],
            account=a["account"],
            position=pid,
            title=label,
            day=day,
            amount=amount,
            currency=h["currency"],
        )

        def save(doc):
            doc["cash_dates"] = [r for r in doc.get("cash_dates", []) if r["id"] != key] + [entry]
            return doc

        update_json(package, NOTES, {}, save)
        return
    raise ValueError("지원하지 않는 관리 동작입니다.")


def agent_brief(directory, package, domain):
    """Consumable local research input. Keep other agents' private positions out."""
    return brief_from_board(board(directory, package, live=True), domain)


def brief_from_board(doc, domain):
    """Use the same observation snapshot for every participant in a manager question."""
    if domain not in DOMAINS:
        raise ValueError("담당 분야를 확인하세요.")
    positions = []
    for p in doc["positions"]:
        if domain not in p["tasks"]:
            continue
        direct = {
            cid: [r for r in rows if not r.get("domains") or domain in r["domains"]]
            for cid, rows in p["direct"].items()
            if domain in doc["categories"][cid]["agents"]
        }
        positions.append(
            {
                **{k: p[k] for k in ("provider", "account", "symbol", "currency", "weight_pct", "as_of")},
                "task": p["tasks"][domain],
                "evidence": {k: v for k, v in direct.items() if v},
            }
        )
    categories = {}
    for cid, c in doc["categories"].items():
        if domain in c["agents"]:
            categories[cid] = dict(
                title=c["title"],
                question=c["assessment"],
                sources=c["runs"],
                context=[
                    r
                    for r in c["observations"]
                    if not r["subjects"]
                    and not r.get("target")
                    and (not r.get("domains") or domain in r["domains"])
                ],
            )
    return dict(agent=domain, positions=positions, categories=categories)
