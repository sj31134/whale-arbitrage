"""Compare three research rules on the existing public stock cohort."""

import json
import sqlite3
from collections import Counter
from pathlib import Path
from statistics import mean

from private_accounts import quant, strategy_registry


def risk_at(closes, t):
    below = all(closes[j] < mean(closes[j-59:j+1]) for j in (t-1, t))
    return below and closes[t] <= 0.9 * max(closes[t-59:t+1])


def local_watch(package, accounts):
    """Join to the verified public bar store locally. This function makes no network calls."""
    stocks = {"KR": set(), "US": set()}
    for account in accounts:
        for mark in account.get("marks", []):
            key = mark.get("instrument")
            if key and key[0] in ("KRX", "NYSE", "NASDAQ", "AMEX"):
                stocks["KR" if key[0] == "KRX" else "US"].add(tuple(key))
    if not any(stocks.values()):
        return dict(state="검증 일봉에 대조할 상장 주식 식별값 없음", rows=[])
    try:
        _, meta, groups = strategy_registry.read_panel(package, frozen=stocks)
    except (ValueError, OSError, sqlite3.Error):
        return dict(state="독립 검증한 공개 일봉을 읽을 수 없음", rows=[])
    records = []
    for market, members in groups.items():
        for member in members:
            reason = member.get("reason")
            bars = member.get("bars", [])
            if reason or len(bars) < 61:
                status = reason or "연속 종가 61개 미만"
            else:
                closes = [float(b["close"]) for b in bars[-61:]]
                status = "위험 재검토" if risk_at(closes, 60) else "가격 경보 조건 미충족"
            venue, symbol, _ = member["key"]
            records.append(dict(venue=venue, symbol=symbol, status=status, day=meta["days"][market]))
    return dict(state="검증 일봉 기준 · 미연결 상품 제외", rows=sorted(records, key=lambda r: (r["venue"], r["symbol"])))


def replay(bars, venue, rule, scale=1, window=126):
    start = len(bars) - window
    if start < 60 or window < 1:
        raise ValueError("60거래일 준비 자료와 평가 기간이 필요합니다.")
    closes = [float(b["close"]) for b in bars]
    fee = quant.costs(venue)
    shares, cash = 0.0, 1.0
    desired = True
    peak = 1.0
    drawdown = 0.0
    signals = []
    curve = []
    for t in range(start, len(bars)):
        opening = float(bars[t]["open"])
        if desired and not shares:
            shares, cash = cash / (opening * (1 + fee.side(False, scale))), 0.0
        elif not desired and shares:
            cash, shares = shares * opening * (1 - fee.side(True, scale)), 0.0
        nav = cash + shares * closes[t]
        peak = max(peak, nav)
        drawdown = min(drawdown, nav / peak - 1)
        curve.append(nav)
        if rule == "first":
            if desired and closes[t] < closes[t - 1]:
                desired = False
        elif rule == "trend":
            if desired:
                if risk_at(closes, t):
                    desired = False
                    signals.append(t)
            elif all(closes[j] > mean(closes[j-19:j+1]) for j in (t-1, t)):
                desired = True
        elif rule != "hold":
            raise ValueError("알 수 없는 규칙")
    matured = [t for t in signals if t + 20 < len(closes)]
    hits = sum(min(closes[t+1:t+21]) <= 0.9 * closes[t] for t in matured)
    return dict(net=curve[-1]-1, drawdown=drawdown, signals=len(signals), matured=len(matured), hits=hits)


def study(package):
    with strategy_registry.database(package) as db:
        cohort = db.execute("SELECT members FROM cohort WHERE rule='public-stock-sample-v1'").fetchone()
    if not cohort:
        raise ValueError("공개 고정 표본을 먼저 등록하세요.")
    panel, meta, markets = strategy_registry.read_panel(package, frozen=json.loads(cohort[0]))
    result = {}
    for market, rows in markets.items():
        eligible, exclusions = [], Counter()
        for row in rows:
            reason = row.get("reason")
            bars = row.get("bars", [])
            if not reason and (len(bars) < 186 or any(not b.get("open") for b in bars[-126:])):
                reason = "연속 시가·종가 부족"
            if reason:
                exclusions[reason] += 1
            else:
                eligible.append(row)
        stats = {}
        for scale in (1, 2):
            runs = {rule: [replay(r["bars"], r["key"][0], rule, scale) for r in eligible]
                    for rule in ("hold", "first", "trend")}
            if not eligible:
                continue
            for rule, records in runs.items():
                stats[f"{rule}_{scale}"] = dict(
                    mean_net=round(100 * mean(r["net"] for r in records), 3),
                    mean_drawdown=round(100 * mean(r["drawdown"] for r in records), 3),
                    beat=sum(r["net"] > b["net"] for r, b in zip(records, runs["hold"])),
                    signals=sum(r["signals"] for r in records), matured=sum(r["matured"] for r in records),
                    hits=sum(r["hits"] for r in records),
                )
        result[market] = dict(sample=len(rows), n=len(eligible), exclusions=dict(exclusions),
                              first=eligible[0]["bars"][-126]["day"] if eligible else None,
                              last=meta["days"][market], rules=stats)
    return dict(panel=panel, markets=result)


if __name__ == "__main__":
    package = Path(__file__).resolve().parents[2] / "private_accounts"
    print(json.dumps(study(package), ensure_ascii=False, indent=2))
