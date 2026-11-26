"""Close-confirmed, next-open SMA experiments on one immutable series."""

from bisect import bisect_right
from dataclasses import dataclass, asdict
from datetime import date
from decimal import Decimal
from math import isfinite
from statistics import median

VERSION = "sma-cross-1.3"
PERIODS = range(5, 121)
WARM, TRAIN, STEP, HOLD = 121, 126, 42, 63
MIN_ROWS = WARM + TRAIN + 2 * STEP + HOLD


@dataclass(frozen=True)
class Costs:
    commission: float
    half_spread: float
    slippage: float
    sell_tax: float

    def side(self, sell, scale):
        return (
            scale
            * (
                self.commission
                + self.half_spread
                + self.slippage
                + (self.sell_tax if sell else 0)
            )
            / 10000
        )


def costs(venue):
    # Research scenarios in basis points per fill, not statutory rates.
    if venue == "BINANCE_B":
        return Costs(10, 10, 5, 0)
    if venue == "KRAKEN_X":
        return Costs(40, 20, 10, 0)
    return Costs(5, 3, 2, 20 if venue == "KRX" else 0)


def signals(closes, period):
    """Exact decimal comparison, carry previous nonzero side across ties."""
    total = Decimal(0)
    previous = 0
    events = [0] * len(closes)
    means = [None] * len(closes)
    for i, close in enumerate(closes):
        total += close
        if i >= period:
            total -= closes[i - period]
        if i + 1 < period:
            continue
        means[i] = float(total / period)
        diff = close * period - total
        side = (diff > 0) - (diff < 0)
        if side and previous and side != previous:
            events[i] = side
        if side:
            previous = side
    return events, means


def simulate(bars, events, start, stop, fee, scale=1, detail=False):
    """Half-open interval. Benchmark requests one purchase at first open."""
    cash, shares, peak, worst, turnover = 1.0, 0.0, 1.0, 0.0, 0.0
    fills = exits = 0
    pending = 1 if events is None else events[start - 1]
    path, drawdowns, markers = [], [], []
    for i in range(start, stop):
        bar = bars[i]
        opening = bar["open"]
        if opening and pending:
            if (pending > 0) != bool(shares):
                wealth = cash + shares * opening
                if pending > 0:
                    shares = cash / (opening * (1 + fee.side(False, scale)))
                    traded = shares * opening
                    cash = 0.0
                else:
                    traded = shares * opening
                    cash = traded * (1 - fee.side(True, scale))
                    shares = 0.0
                    exits += 1
                turnover += traded / wealth
                fills += 1
                if detail:
                    markers.append((i - start, pending, opening))
            pending = 0
        wealth = cash + shares * bar["close"]
        peak = max(peak, wealth)
        dd = wealth / peak - 1
        worst = min(worst, dd)
        if detail:
            path.append(wealth)
            drawdowns.append(dd)
        if events is not None and events[i]:
            pending = events[i]
    result = dict(
        net=wealth - 1, mdd=worst, fills=fills, exits=exits, turnover=turnover
    )
    if detail:
        result.update(path=path, drawdowns=drawdowns, markers=markers)
    return result


def prepare(rows, sessions, venue, *, recover=False):
    """Optionally restart the warm-up after the last historical discontinuity."""
    bars, issues = [], []
    calendar = sorted(sessions)
    previous_day = None
    if not rows:
        return [], ["완료 일봉 원천 대기"]
    for r in rows:
        try:
            day = date.fromisoformat(r["day"])
        except (TypeError, ValueError):
            return [], ["거래일 형식 오류"]
        if previous_day and day <= previous_day:
            return [], ["거래일 중복 또는 역순"]
        previous_day = day
        try:
            close = Decimal(str(r["closing"]))
            if not close.is_finite() or not 0 < close < Decimal("1e20"):
                raise ValueError
        except (ArithmeticError, ValueError, TypeError):
            issues.append("유효한 종가 부족")
            if not recover:
                return [], issues
            bars.clear()
            continue
        try:
            opening = float(r["opening"])
            if not isfinite(opening) or not 0 < opening < 1e20:
                opening = None
        except (TypeError, ValueError, OverflowError):
            opening = None
        if bars:
            prior = bars[-1]
            idx = bisect_right(calendar, prior["day"])
            problems = []
            if idx < len(calendar) and calendar[idx] < r["day"]:
                problems.append("같은 시장에서 거래가 확인된 날짜 누락")
            if (day - date.fromisoformat(prior["day"])).days > (
                1 if venue in ("KRAKEN_X", "BINANCE_B") else 10
            ):
                problems.append("연속성 확인 필요 · 거래정지 또는 원천 누락")
            # A missing open cannot rule out a split. Screen the close-to-close
            # discontinuity in that case and never substitute a close for a fill.
            if not 0.68 < (opening or float(close)) / prior["close"] < 1.48:
                problems.append("분할·병합 또는 급변 의심 · 가격 단절")
            if problems:
                issues.extend(problems)
                if recover:
                    bars.clear()
        bars.append(dict(day=r["day"], open=opening, close=float(close), decimal=close))
    return bars, list(dict.fromkeys(issues))


def rank(scores):
    eligible = [n for n in PERIODS if scores[n]["exits"] >= 2]
    return max(eligible, key=lambda n: (scores[n]["net"], -n), default=None)


def evaluate(bars, fee, issues, *, invalid_holdout=False):
    size = len(bars) + (HOLD if invalid_holdout else 0)
    result = dict(
        version=VERSION,
        costs=asdict(fee),
        reasons=list(issues),
        folds=[],
        scores={},
        holdout={},
        candidate=None,
        selected=False,
    )
    if size < MIN_ROWS:
        result["reasons"].append(f"공통 구간에 {MIN_ROWS}개 일봉 필요 · {size}개 확보")
    if (issues and not invalid_holdout) or len(bars) <= WARM:
        return result
    closes = [b["decimal"] for b in bars]
    events = {n: signals(closes, n)[0] for n in PERIODS}
    cutoff = size - HOLD if size >= MIN_ROWS else size

    def compare(start, stop):
        benchmark = simulate(bars, None, start, stop, fee)
        scores = {n: simulate(bars, events[n], start, stop, fee) for n in PERIODS}
        for row in scores.values():
            row["excess"] = row["net"] - benchmark["net"]
        return scores

    scores = compare(WARM, cutoff)
    result.update(scores=scores, training=[bars[WARM]["day"], bars[cutoff - 1]["day"]])
    if size < MIN_ROWS:
        return result
    pick = rank(scores)
    result["candidate"] = pick
    first = WARM + TRAIN + (cutoff - WARM - TRAIN) % STEP
    for start in range(first, cutoff, STEP):
        best = rank(compare(WARM, start))
        base = simulate(bars, None, start, start + STEP, fee)
        out = simulate(bars, events[best], start, start + STEP, fee) if best else None
        result["folds"].append(
            dict(
                start=bars[start]["day"],
                end=bars[start + STEP - 1]["day"],
                period=best,
                metrics=out,
                benchmark=base,
            )
        )
    # Freeze the candidate before evaluating any final-interval returns.
    if invalid_holdout:
        result["reasons"].append("최종 미사용 구간의 일봉 품질을 확인해야 합니다.")
        return result
    result["holdout"] = compare(cutoff, size)
    result["hold_dates"] = [bars[cutoff]["day"], bars[-1]["day"]]
    reasons = result["reasons"]
    if not pick:
        reasons.append("학습 구간 왕복 2회 이상인 후보 없음")
        return result
    neighbors = [n for n in PERIODS if 0 < abs(n - pick) <= 2]
    folds = result["folds"]
    comparable = [f for f in folds if f["metrics"] and f["metrics"]["fills"]]
    if len(comparable) < 2 or len(comparable) != len(folds):
        reasons.append("워크포워드 평가 구간의 체결 표본 부족")
    elif median(f["metrics"]["net"] - f["benchmark"]["net"] for f in comparable) <= 0:
        reasons.append("워크포워드 초과수익 중앙값이 0 이하")
    if result["holdout"][pick]["exits"] < 2:
        reasons.append("최종 미사용 구간 왕복 거래 2회 미만")
    if result["holdout"][pick]["excess"] <= 0:
        reasons.append("최종 미사용 구간에서 단순 보유 초과 실패")
    if median(result["holdout"][n]["excess"] for n in neighbors) <= 0:
        reasons.append("인접 ±2일의 미사용 초과수익 중앙값이 0 이하")
    result["selected"] = not reasons
    return result


def replay(inputs, cached=None):
    """Rebuild a saved experiment from its own bars and recorded cost settings."""
    rows, sessions, venue = inputs["rows"], inputs["sessions"], inputs["key"][0]
    fee = Costs(**inputs["costs"])
    reserved = len(rows) >= MIN_ROWS
    train_rows = rows[:-HOLD] if reserved else rows
    training, warnings = prepare(train_rows, sessions, venue, recover=True)
    bars = training
    issues = []
    invalid_holdout = False
    if reserved and len(training) >= MIN_ROWS - HOLD:
        # Include the boundary bar to check the first held-out overnight gap.
        tail, issues = prepare(rows[-HOLD - 1 :], sessions, venue)
        invalid_holdout = bool(issues)
        if not issues:
            bars = training + tail[1:]
    if cached is not None:
        return bars, cached
    else:
        result = evaluate(bars, fee, issues, invalid_holdout=invalid_holdout)
        if reserved and len(training) < MIN_ROWS - HOLD:
            result["reasons"] = [
                f"마지막 {HOLD}봉 별도 보관 · 연속 학습 일봉 {len(training)}/{MIN_ROWS - HOLD}개"
            ]
        result["history_warnings"] = warnings
        result["excluded"] = len(train_rows) - len(training)
    return bars, result
