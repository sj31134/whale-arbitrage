"""Dated public screens and offline, exact-identity portfolio cross-checks."""
import re
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import urlsplit

from agents import intelligence as intel, market_anomalies as scan, market_prices, portfolio
from . import live_valuation, store

FILE = "market_screen.json"
CASES = "market_casebook.json"
MATCHES = "market_crosscheck.json"
STRUCTURE = "market_structure.json"
HOSTS = ("krx.co.kr", "samsungpop.com", "sec.gov", "dart.fss.or.kr", "reuters.com",
         "cboe.com", "nasdaq.com", "kraken.com", "xstocks.fi", "nvidia.com", "naver.com",
         "finra.org", "fred.stlouisfed.org", "spglobal.com", "nyse.com", "kofia.or.kr",
         "newspim.com")
TEXT = ("name", "issue", "flow", "trend", "insight", "revisit")
KINDS = ("종목", "섹터 지수", "섹터 ETF 표본", "토큰")
OVERNIGHT_SAMPLES = {
    "SOXX": ("섹터 ETF 표본", "https://stockanalysis.com/etf/soxx/history/"),
    "NVDA": ("종목", "https://stockanalysis.com/stocks/nvda/history/"),
}
OVERNIGHT_FILE = "overnight_screen.json"
US_EARLY_CLOSE = {"2026-11-27", "2026-12-24", "2027-11-26", "2028-11-24"}


def date_key(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("거래일 형식을 확인하세요.")
    return date.fromisoformat(value)


def url_ok(value):
    if not isinstance(value, str) or len(value) > 1200:
        return False
    u = urlsplit(value)
    return (u.scheme == "https" and not u.username and not u.password and not u.port
            and any(u.hostname == h or (u.hostname or "").endswith("."+h) for h in HOSTS))


def run_scan(package, days, *, collector=scan.collect, retry_of=None):
    now = datetime.now(timezone.utc)
    for m, value in days.items():
        local = now.astimezone(scan.ZONE[m])
        day = date_key(value)
        earliest_close = (15,30) if m == "KR" else (16,0)
        if m == "US" and value in US_EARLY_CLOSE:
            earliest_close = (13,0)
        if (day > local.date() or day.weekday() >= 5 or
            (day == local.date() and (local.hour,local.minute) < earliest_close)):
            raise ValueError("거래소별 완료 거래일을 확인하세요.")
    observed = collector(days)
    stamp = now.isoformat()
    def merge(old):
        if retry_of is not None and old.get("at") and old.get("at") != retry_of:
            return old
        states = dict(old.get("feeds", {}))
        for key, sample in observed.items():
            before = states.get(key, {})
            if before.get("attempt", "") > stamp:
                continue
            states[key] = dict(section=sample["section"], status=sample["status"], attempt=stamp,
                               success=stamp if sample["rows"] else before.get("success"),
                               rows=sample["rows"] or before.get("rows", []))
        if old.get("at", "") > stamp:
            return dict(old, feeds=states)
        return dict(days=days, at=stamp, feeds=states)
    intel.update_json(package, FILE, {}, merge)
    # Keep past cutoff observations even after the latest dashboard advances.
    filename = "market_session_" + days["KR"] + "_" + days["US"] + ".json"
    intel.update_json(package, filename, {}, merge)


def retry_pending(directory, package):
    state = intel.private_json(package,FILE,{})
    if not state or datetime.fromisoformat(state["at"]).astimezone(intel.KST).date() != datetime.now(intel.KST).date():
        return
    pending = {key for key,r in state["feeds"].items() if r["status"] != "확인"}
    if pending:
        run_scan(package,state["days"],collector=lambda days:scan.collect(days,selected=pending), retry_of=state["at"])
    crosscheck(directory,package)


def import_cases(package, source, checked, rows):
    checked = store.timestamp(checked)
    until = datetime.fromisoformat(checked)
    if source != "market-cases" or not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise ValueError("공개 종목·섹터 사례 목록을 확인하세요.")
    records = {}
    for r in rows:
        base = {"market","day","symbol","kind","evidence","source","refs",*TEXT}
        quote = {"bid","ask","venue","observed"}
        if not isinstance(r, dict) or set(r) not in (base|{"change_pct"}, base|quote):
            raise ValueError("공개 사례 필드를 확인하세요.")
        m, s, day = r["market"], r["symbol"], date_key(r["day"])
        if (m not in ("KR","US","XT") or not isinstance(s,str) or not re.fullmatch(r"[A-Za-z0-9.\-]{1,20}",s)
            or r["kind"] not in KINDS or r["evidence"] not in ("공시 확인","관련 보도","원인 미확인")
            or any(not isinstance(r[k],str) or not 0 < len(r[k].strip()) <= 600 for k in TEXT)
            or day > until.astimezone(scan.ZONE.get(m,timezone.utc)).date()
            or not (url_ok(r["source"]) or (m == "US" and "change_pct" in r
                    and OVERNIGHT_SAMPLES.get(s) == (r["kind"], r["source"])))
            or not isinstance(r["refs"],list) or len(r["refs"]) > 6 or not all(url_ok(u) for u in r["refs"])):
            raise ValueError("공개 사례의 거래일·출처·분류를 확인하세요.")
        if r["evidence"] == "공시 확인" and not r["refs"]:
            raise ValueError("공시 원문을 첨부하세요.")
        row = dict(r,checked=checked,basis="공개 마감자료 표본")
        if "bid" in r:
            observed = store.timestamp(r["observed"])
            if (observed > checked or datetime.fromisoformat(observed).astimezone(scan.ZONE.get(m,timezone.utc)).date() != day
                or not isinstance(r["venue"],str) or not 1 <= len(r["venue"]) <= 50):
                raise ValueError("호가 거래소와 관측시각을 확인하세요.")
            row.update(spread_bps=scan.spread_bps(r["bid"], r["ask"]),observed=observed,basis="원문 호가 스냅샷")
        else:
            row["change_pct"] = scan.number(r["change_pct"])
            if row["change_pct"] < -100:
                raise ValueError("등락률을 확인하세요.")
        key = "|".join([m,r["day"],r["kind"],s,r.get("venue","종가"),row.get("observed","")])
        records[key] = row
    def merge(old):
        return {**old, **{k:v for k,v in records.items() if v["checked"] >= old.get(k,{}).get("checked","")}}
    intel.update_json(package, CASES, {}, merge)
    return len(records)


def overnight_close(now):
    day = now.astimezone(intel.KST).date() - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return datetime.combine(day, time(13 if day.isoformat() in US_EARLY_CLOSE else 16), scan.ZONE["US"])


def overnight_watch(package, now):
    """Same-session US closes available by the review time. No portfolio input."""
    close = overnight_close(now)
    target = close.date().isoformat()
    feeds = intel.private_json(package, FILE, {}).get("feeds", {})
    cases = intel.private_json(package, CASES, {})
    observations = [(r, r["checked"]) for r in cases.values() if r.get("day") == target]
    latest = intel.private_json(package, OVERNIGHT_FILE, {})
    for symbol in OVERNIGHT_SAMPLES:
        for feed in (feeds.get(symbol, {}), latest.get(symbol, {})):
            observations.extend((r, feed.get("success")) for r in feed.get("rows", []))
    samples = {}
    for row, stamp in observations:
        symbol = row.get("symbol")
        if (symbol not in OVERNIGHT_SAMPLES or row.get("market") != "US" or row.get("day") != target
                or row.get("kind") != OVERNIGHT_SAMPLES[symbol][0] or "change_pct" not in row or not stamp):
            continue
        seen = datetime.fromisoformat(stamp)
        if close <= seen <= now and (symbol not in samples or seen > datetime.fromisoformat(samples[symbol]["checked"])):
            samples[symbol] = dict(change_pct=float(row["change_pct"]), source=row["source"], checked=stamp)
    state = "판단 보류 · 같은 미국 거래일의 종가 두 건 확인 필요"
    if len(samples) == len(OVERNIGHT_SAMPLES):
        state = ("경보 · 한국 반도체 시초가 갭 하락 위험"
                 if all(r["change_pct"] <= -5 for r in samples.values()) else "동반 급락 조건 미충족")
    return dict(day=target, state=state, samples=samples)


def refresh_overnight(package, *, collector=scan.collect):
    now = datetime.now(timezone.utc)
    report = overnight_watch(package, now)
    missing = OVERNIGHT_SAMPLES.keys() - report["samples"].keys()
    if not missing or now < overnight_close(now):
        return
    days = {"US": report["day"], "KR": now.astimezone(intel.KST).date().isoformat()}
    result = collector(days, selected=missing)
    seen = datetime.now(timezone.utc).isoformat()

    def merge(old):
        updated = dict(old)
        for symbol, item in result.items():
            before = old.get(symbol, {})
            if before.get("attempt", "") > seen:
                continue
            rows = item["rows"]
            updated[symbol] = dict(attempt=seen, status=item["status"], day=days["US"],
                                   rows=rows or before.get("rows", []),
                                   success=seen if rows else before.get("success"))
        return updated

    intel.update_json(package, OVERNIGHT_FILE, {}, merge)


def import_structure(package, source, checked, rows):
    checked = store.timestamp(checked)
    fields = {"market","venue","kind","as_of","published","title","source","implication","revisit"}
    if source != "market-structure" or not isinstance(rows,list) or not 1 <= len(rows) <= 50:
        raise ValueError("공개 시장구조 관측 목록을 확인하세요.")
    records = {}
    for r in rows:
        if (not isinstance(r,dict) or set(r) != fields or r["market"] not in ("US","KR","XT")
            or r["kind"] not in ("거래소 조치","프로그램 집계","리밸런싱 공지","거래장소 집계","파생시장 집계")
            or not all(isinstance(r[k],str) and 0 < len(r[k].strip()) <= 600 for k in fields-{"source"})
            or not url_ok(r["source"])):
            raise ValueError("시장구조 관측의 원문과 분류를 확인하세요.")
        event, published = (store.timestamp(r[k]) for k in ("as_of","published"))
        if not event <= published <= checked:
            raise ValueError("시장구조 관측·공표·조회 시각의 순서를 확인하세요.")
        key = "|".join((r["market"],r["venue"],r["kind"],event,r["source"]))
        records[key] = dict(r,as_of=event,published=published,checked=checked)
    intel.update_json(package,STRUCTURE,{},lambda old:{**old,**{k:r for k,r in records.items()
                     if r["checked"] >= old.get(k,{}).get("checked","")}})
    return len(records)


def snapshot(package):
    state = intel.private_json(package,FILE,{})
    days, at = state.get("days",{}), state.get("at")
    if not at:
        return {}
    target = {**days, "XT":datetime.fromisoformat(at).astimezone(timezone.utc).date().isoformat()}
    feeds, spreads, program = {}, [], []
    for key, f in state["feeds"].items():
        if f["section"] == "program":
            program.extend(r for r in f["rows"] if r["day"] == days["KR"])
        else:
            rows = [r for r in f["rows"] if r["day"] == target.get(r["market"])]
            if f["section"] == "spreads":
                spreads.extend(rows)
            else:
                feeds[key] = dict(f, rows=rows)
    cases = [r for r in intel.private_json(package,CASES,{}).values() if r["day"] == target.get(r["market"])]
    spreads.extend(r for r in cases if "spread_bps" in r)
    quote_groups = {}
    for r in spreads:
        key = r["market"],r["venue"],r["observed"]
        quote_groups.setdefault(key,{})[r["symbol"]] = r
    spreads = []
    for book in quote_groups.values():
        ordered = sorted(book.values(),key=lambda r:(-r["spread_bps"],r["symbol"]))
        spreads.extend(dict(r,rank=rank,sample=len(ordered)) for rank,r in enumerate(ordered,1))
    feeds["독립 확인"] = dict(section="moves",rows=[r for r in cases if "change_pct" in r])
    day_kst = datetime.fromisoformat(at).astimezone(intel.KST).date()
    structure = [r for r in intel.private_json(package,STRUCTURE,{}).values()
                 if datetime.fromisoformat(r["published"]).astimezone(intel.KST).date() == day_kst or
                 datetime.fromisoformat(r["as_of"]).astimezone(scan.ZONE.get(r["market"],timezone.utc)).date().isoformat() == target[r["market"]]]
    checked_at = max([at, *(r["checked"] for r in cases), *(r["checked"] for r in structure)])
    return dict(at=checked_at, scan_at=at, days=days, groups=scan.rankings(feeds), cases=cases, program=program,
                structure=sorted(structure,key=lambda r:r["published"],reverse=True),
                spreads=sorted(spreads,key=lambda r:(r["market"],r["venue"],r["observed"],-r["spread_bps"])),
                sources={k:{i:f.get(i) for i in ("status","success","attempt")} for k,f in state["feeds"].items()})


def crosscheck(directory, package):
    snap = snapshot(package)
    if not snap:
        raise ValueError("먼저 공개 시장을 점검하세요.")
    universe = {}
    for r in [*(r for g in snap["groups"] for r in g["leaders"]),*snap["spreads"],*snap["cases"]]:
        universe.setdefault((r["market"],r["symbol"].upper()),[]).append(r)
    book = live_valuation.read(package)
    accounts = portfolio.portfolio_accounts(directory,package)
    tags = intel.private_json(package,intel.NOTES,{}).get("tags",{})
    matches = []
    checked = 0
    for a in accounts:
        for h in a["holdings"]:
            symbol, ccy = h["symbol"], h["currency"]
            if symbol.upper() == ccy.upper():
                continue
            pid = intel.position_id(a["provider"],a["account"],symbol,ccy)
            keys = set()
            q = book.match(a["provider"],symbol,ccy)
            if q and q["venue"] in (*market_prices.AMERICA,"KRX"):
                keys.add(("KR" if q["venue"] == "KRX" else "US",q["symbol"].upper(),"직접"))
            for tag in tags.get(pid,[]):
                fields = tag.split(":")
                if len(fields)==3 and fields[0] in ("underlying","sector","token","stock") and fields[1] in ("KR","US","XT"):
                    keys.add((fields[1],fields[2].upper(),dict(underlying="기초주식",sector="섹터",token="상품",stock="직접")[fields[0]]))
            if keys:
                checked += 1
            for m, code, relation in sorted(keys):
                for r in universe.get((m,code),[]):
                    item = dict(position=pid, holding=symbol, relation=relation, market=m,
                                name=r["name"], day=r["day"], signal=r.get("insight","공개 이상치 · 원인 검토 대기"),
                                source=r["source"], revisit=r.get("revisit","공시와 다음 정규장 가격을 확인"))
                    if item not in matches:
                        matches.append(item)
    record = dict(at=datetime.now(timezone.utc).isoformat(),scan_at=snap["at"],days=snap["days"],
                  matched=matches, identified=checked, has_accounts=bool(accounts), has_public=bool(universe))
    intel.update_json(package,MATCHES,{},lambda old: record if record["scan_at"] >= old.get("scan_at","") else old)
