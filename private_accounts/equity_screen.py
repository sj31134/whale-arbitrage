"""Replay the desk's existing SMA engine on completed public exchange series."""

import argparse
import csv
import gzip
import hashlib
import itertools
import io
import json
import os
import re
import sqlite3
import tempfile
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from contextlib import closing
from datetime import date
from pathlib import Path

from agents import intelligence
from agents.equities.daily_bars import US
from . import live_valuation, price_history, quant, store


def screen_rows(item):
    key, source, rows, sessions, actions = item
    fee = quant.costs(key[0])
    inputs = dict(key=key, source=source, rows=rows, sessions=sessions,
                  costs=vars(fee), version=quant.VERSION)
    raw = json.dumps(inputs, ensure_ascii=False, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    bars, run = quant.replay(inputs)
    pick = run["candidate"]
    score = run["holdout"].get(pick)
    state = "quality_hold"
    if run["holdout"]:
        state = "rule_pass" if run["selected"] else "rule_fail"
    affected = [d for d in actions if bars and bars[0]["day"] <= d <= rows[-1]["day"]]
    if affected:
        state = "action_hold"
    result = dict(state=state, period=pick, source=source, bars=len(bars),
                  held=run.get("hold_dates"), actions=affected, reasons=run["reasons"],
                  warnings=run["history_warnings"], score=score)
    if score:
        start, stop = len(bars) - quant.HOLD, len(bars)
        events = quant.signals([b["decimal"] for b in bars], pick)[0]
        stress = quant.simulate(bars, events, start, stop, fee, scale=2)
        benchmark = quant.simulate(bars, None, start, stop, fee, scale=2)
        result["double_cost_excess"] = stress["net"] - benchmark["net"]
        result["wf_excess"] = [f["metrics"]["net"] - f["benchmark"]["net"]
                               for f in run["folds"] if f["metrics"] and f["metrics"]["fills"]]
    # Keep the frozen inputs and the score for each final-window SMA for replay.
    return (*key, digest, gzip.compress(raw, compresslevel=1, mtime=0),
            json.dumps(result, ensure_ascii=False), json.dumps(run["holdout"]))


def complete_prices(row):
    try:
        return all(0 < float(row[k]) < 1e20 for k in ("opening", "closing"))
    except (ValueError, TypeError, OverflowError):
        return False


def collect_inputs(db, days, cutoff, actions, counts):
    venues = ("KRX", *US)
    calendars = {}
    for venue in venues:
        end = days["KR" if venue == "KRX" else "US"]
        calendars[venue] = sorted(d for d in price_history.known_sessions(db, venue) if d <= end)
    query = f"""SELECT venue,symbol,currency,source,day,opening,closing,revisions FROM price_bar
               WHERE venue IN ('KRX','AMEX','NYSE','NASDAQ')
               AND {price_history.VENUE_BARS}
               AND day <= CASE WHEN venue='KRX' THEN ? ELSE ? END
               AND julianday(seen)<=julianday(?)
               ORDER BY venue,symbol,currency,source,day"""
    cursor = db.execute(query, (days["KR"], days["US"], cutoff))
    for key, group in itertools.groupby(cursor, lambda r: (r[0], r[1], r[2])):
        venue, symbol, _ = key
        market = "KR" if venue == "KRX" else "US"
        end = days[market]
        counts[market]["universe"] += 1
        feeds = []
        for source, feed in itertools.groupby(group, lambda r: r[3]):
            rows = [dict(day=r[4], opening=r[5], closing=r[6], revisions=r[7]) for r in feed]
            if rows[-1]["day"] != end:
                continue
            if (len(rows) < quant.MIN_ROWS or not complete_prices(rows[-1])
                    or sum(map(complete_prices, rows)) < quant.MIN_ROWS):
                continue
            sessions = [d for d in calendars[venue] if rows[0]["day"] <= d <= end]
            train, _ = quant.prepare(rows[:-quant.HOLD], sessions, venue, recover=True)
            # Rank eligible sources using the training prefix alone, then stable source order.
            feeds.append((len(train), source, rows, sessions))
        if feeds:
            _, source, rows, sessions = min(feeds, key=lambda f: (-f[0], f[1]))
            counts[market]["screened"] += 1
            yield key, source, rows, sessions, sorted(actions.get((market, symbol), ()))


def split_events(path):
    events = defaultdict(set)
    if path:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            rows = db.execute("""SELECT DISTINCT s.market,s.symbol,b.day FROM price_bar b
                             JOIN series s ON s.id=b.series_id WHERE b.split_ratio>0
                             AND b.split_ratio!=1 AND s.market IN ('KR','US')""")
            for market, symbol, day in rows:
                events[market, symbol].add(day)
    return events


def index_result(package, path):
    """Point the authenticated page at the newest completely published run."""
    if (path.parent.resolve() != (package / ".local/equity_screens").resolve()
            or not re.fullmatch(r"[0-9]{8}T[0-9]{6}\.sqlite3", path.name)):
        return
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        meta = json.loads(db.execute("SELECT payload FROM metadata").fetchone()[0])
        markets = {m: dict(total=0, passed=0, failed=0, held=0) for m in meta["days"]}
        for venue, state, n in db.execute("""SELECT venue,json_extract(detail,'$.state'),count(*)
                                             FROM result GROUP BY 1,2"""):
            counts = markets["KR" if venue == "KRX" else "US"]
            counts["total"] += n
            counts[{"rule_pass": "passed", "rule_fail": "failed"}.get(state, "held")] += n
    record = dict(run=path.stem, cutoff=meta["cutoff"], days=meta["days"], markets=markets)
    intelligence.update_json(package, "equity_screen_index.json", {},
                             lambda old: old if old.get("cutoff", "") >= meta["cutoff"] else record)


def close_checks(folder, stamp):
    path = folder / (stamp + "-validation.sqlite3")
    if not path.is_file() or path.is_symlink():
        return {}
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        return {(sample, venue, symbol, ccy): result for sample, venue, symbol, ccy, result in
                db.execute("SELECT experiment,venue,symbol,currency,price_check FROM assessment")}


def public_csv(package):
    """Export market research alone. This path never reads an account or a position."""
    index = intelligence.private_json(package, "equity_screen_index.json", {}) if package else {}
    stamp = index.get("run", "")
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}", stamp):
        return None
    folder = package / ".local" / "equity_screens"
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    checks = close_checks(folder, stamp)
    classes = {}
    catalog = folder / (stamp + "-validation.sqlite3")
    if catalog.is_file() and not catalog.is_symlink():
        with closing(sqlite3.connect(catalog.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='listing_class'").fetchone():
                classes = {(v,s,c):k for v,s,c,k in db.execute("SELECT * FROM listing_class")}
    writer.writerow(["실험", "시장거래소:종목코드", "통화", "거래일", "종목분류", "연구규칙", "당일_정규장_종가대조",
                     "전진검증_우선표본", "학습선_일", "비용후수익률_%",
                     "단순보유수익률_%", "초과수익_%p", "최대낙폭_%", "청산횟수", "비용2배_초과수익_%p"])
    samples = [("단일 원천 기준선", "", "primary")]
    if index.get("recovery"):
        samples.append(("국내 거래장 미확정 참고 이력", "-naver", "recovery"))
    if index.get("supplement"):
        samples.append(("국내 결측일 보완 실험", "-gap", "gap"))
    for label, suffix, kind in samples:
        path = folder / (stamp + suffix + ".sqlite3")
        if not path.is_file() or path.is_symlink():
            return None
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            for venue, symbol, currency, payload in db.execute(
                    "SELECT venue,symbol,currency,detail FROM result ORDER BY venue,symbol,currency"):
                r = json.loads(payload)
                score = r["score"]
                metrics = [""] * 6
                if score:
                    values = (score["net"], score["net"]-score["excess"], score["excess"], score["mdd"])
                    metrics = [round(100*v, 4) for v in values] + [
                        score["exits"], round(100*r["double_cost_excess"], 4)]
                stock_class = classes.get((venue,symbol,currency), "기타·미분류")
                close_state = checks.get((kind,venue,symbol,currency), "unavailable")
                priority = (kind == "primary" and r["state"] == "rule_pass" and stock_class != "기타·미분류"
                            and close_state == "confirmed" and score and score["net"] > 0 and r["double_cost_excess"] > 0)
                writer.writerow([label, f"{venue}:{symbol}", currency, index["days"]["KR" if venue=="KRX" else "US"],
                                 stock_class, r["state"], close_state, "Y" if priority else "", r["period"], *metrics])
    return output.getvalue().encode("utf-8-sig")


def run(package, destination, days, cutoff, actions, workers):
    if destination.exists():
        raise FileExistsError("결과 파일이 이미 있습니다.")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    counts = {m: dict(universe=0, screened=0) for m in days}
    with tempfile.TemporaryDirectory(dir=destination.parent) as temp:
        tmp = Path(temp)
        with closing(sqlite3.connect(tmp / "bars.sqlite3")) as frozen:
            with live_valuation.connection(package) as live:
                if live is None:
                    raise ValueError("공개 일봉 DB가 없습니다.")
                live.backup(frozen)
            frozen.row_factory = sqlite3.Row
            with closing(sqlite3.connect(tmp / "result.sqlite3")) as out:
                out.executescript("""CREATE TABLE result(venue,symbol,currency,digest,inputs,detail,holdout,
                                  PRIMARY KEY(venue,symbol,currency));
                                  CREATE TABLE metadata(payload TEXT NOT NULL);""")
                stream = collect_inputs(frozen, days, cutoff, split_events(actions), counts)
                with ProcessPoolExecutor(max_workers=workers) as pool:
                    while True:
                        batch = list(itertools.islice(stream, 96))
                        if not batch:
                            break
                        out.executemany("INSERT INTO result VALUES (?,?,?,?,?,?,?)",
                                        pool.map(screen_rows, batch, chunksize=3))
                        out.commit()
                if not all(c["screened"] for c in counts.values()):
                    raise ValueError("양 시장의 최신 검증 가능 입력이 필요합니다.")
                out.execute("INSERT INTO metadata VALUES (?)", (json.dumps(dict(
                    days=days, cutoff=cutoff, version=quant.VERSION, counts=counts,
                    actions_source=actions.name if actions else None)),))
                out.commit()
                if out.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("연구 결과 DB 무결성 오류")
        (tmp / "result.sqlite3").chmod(0o600)
        os.link(tmp / "result.sqlite3", destination)
    index_result(package, destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kr-day", type=date.fromisoformat, required=True)
    parser.add_argument("--us-day", type=date.fromisoformat, required=True)
    parser.add_argument("--as-of", type=store.timestamp, required=True)
    parser.add_argument("--actions", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("workers must be positive")
    days = dict(KR=args.kr_day.isoformat(), US=args.us_day.isoformat())
    run(Path(__file__).resolve().parent, args.output, days, args.as_of, args.actions, args.workers)
    print("공개 시장 이동평균 결과 저장 완료")


if __name__ == "__main__":
    main()
