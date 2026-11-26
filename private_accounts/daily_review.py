"""Private, read-only investment review. Only a fixed completion message may leave this CLI."""

import json
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, localcontext
from urllib.parse import urlsplit

from agents import intelligence
from . import store


KST = intelligence.KST
FILE = "daily_investment_reviews.json"
FLOW_FIELDS = ("market", "period", "as_of", "metric", "unit", "theme", "net", "source")


def read_flows(stream, today):
    """Public, comparable flow figures supplied by the research run. Never fetch these links."""
    raw = stream.read(100001)
    if len(raw) > 100000:
        raise ValueError("공개 자료 크기를 확인하세요.")
    rows = json.loads(raw)
    if not isinstance(rows, list) or len(rows) > 100:
        raise ValueError("공개 수급 자료는 최대 100행 목록이어야 합니다.")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(FLOW_FIELDS):
            raise ValueError("공개 수급 필드를 확인하세요.")
        if any(not isinstance(v, str) or not v.strip() or len(v) > 600 for v in row.values()):
            raise ValueError("수급 값·단위·기간·원문을 확인하세요.")
        record = {k: row[k].strip() for k in FLOW_FIELDS}
        src = urlsplit(record["source"])
        if src.scheme != "https" or not src.hostname or src.username or src.password:
            raise ValueError("공개 HTTPS 원문 주소를 입력하세요.")
        if date.fromisoformat(record["as_of"]) > today:
            raise ValueError("수급 관측일을 확인하세요.")
        try:
            amount = Decimal(record["net"])
        except InvalidOperation:
            raise ValueError("수급 수치 형식을 확인하세요.") from None
        if not amount.is_finite() or abs(amount.adjusted()) > 30 or len(record["net"]) > 40:
            raise ValueError("순유입·순매수 값은 유한한 숫자여야 합니다.")
        record["net"] = store.fixed(amount)
        key = tuple(record[k] for k in ("market", "period", "as_of", "metric", "unit", "source", "theme"))
        if key in result and record != result[key]:
            raise ValueError("같은 관측의 수치가 충돌합니다.")
        result[key] = record
    return sorted(
        result.values(),
        key=lambda r: (
            -date.fromisoformat(r["as_of"]).toordinal(),
            r["market"],
            r["period"],
            r["metric"],
            r["unit"],
            r["source"],
            -Decimal(r["net"]),
            r["theme"],
        ),
    )


def build(board, now):
    accounts = {(a["provider"], a["account"]): a for a in board["accounts"]}
    marks = {(a["provider"],a["account"],m["symbol"],m["currency"]):m
             for a in board["accounts"] for m in a.get("marks",())}
    buckets = defaultdict(list)
    observations = []
    for p in board["positions"]:
        account = accounts[p["provider"], p["account"]]
        ccy = p["currency"]
        pnl = account["pnl"].get((p["symbol"], ccy))
        evidence = [
            dict(
                category=cid,
                title=r["title"],
                as_of=r["as_of"],
                origin=r["origin"],
                value=r["value"],
                analysis=r["analysis"],
            )
            for cid, obs in p["direct"].items()
            if cid not in ("exposure", "social")
            for r in obs
            if not r["stale"]
        ]
        evidence.sort(key=lambda r: r["as_of"], reverse=True)
        for item in evidence:
            observations.append(dict(item, position=p["id"], symbol=p["symbol"]))
        buckets[ccy].append(
            dict(
                id=p["id"],
                symbol=p["symbol"],
                provider=p["provider"],
                account=p["account"],
                source=account["source"],
                as_of=p["as_of"],
                agents=list(p["tasks"]),
                pnl=store.fixed(pnl) if pnl is not None else None,
                weight=p["weight_pct"],
                quote_at=marks.get((p["provider"],p["account"],p["symbol"],ccy),{}).get("at"),
                valuation_state=marks.get((p["provider"],p["account"],p["symbol"],ccy),{}).get("state"),
                evidence=evidence[:3],
            )
        )
    currencies = {}
    with localcontext() as ctx:
        ctx.prec = 100
        for ccy, rows in buckets.items():
            covered = [r for r in rows if r["pnl"] is not None]
            net = sum((Decimal(r["pnl"]) for r in covered), Decimal(0))
            losing = sorted((r for r in covered if Decimal(r["pnl"]) < 0), key=lambda r: Decimal(r["pnl"]))
            gross = sum((-Decimal(r["pnl"]) for r in losing), Decimal(0))
            for r in losing:
                r["loss_share_pct"] = str((-100 * Decimal(r["pnl"]) / gross).quantize(Decimal("0.1")))
            values = [a["totals"][ccy] for a in accounts.values() if ccy in a["totals"]]
            recovery = None
            if len(covered) == len(rows) and values and all(v is not None for v in values):
                capital = sum(map(Decimal, values))
                if capital > 0:
                    recovery = str((100 * max(-net, Decimal(0)) / capital).quantize(Decimal("0.01")))
            currencies[ccy] = dict(
                known=len(covered),
                total=len(rows),
                net=store.fixed(net) if covered else None,
                gross_loss=store.fixed(gross) if covered else None,
                recovery_pct=recovery,
                losses=losing,
                missing=[r for r in rows if r["pnl"] is None],
            )
    return dict(
        day=now.date().isoformat(),
        generated=now.isoformat(timespec="microseconds"),
        currencies=currencies,
        valuations=[dict(provider=a["provider"], account=a["account"], currency=currency,
                         as_of=a["as_of"], source=a["source"], value=value)
                    for a in board["accounts"] for currency, value in a["totals"].items()],
        account_dates=[
            {k: a[k] for k in ("provider", "account", "as_of", "source")} for a in accounts.values()
        ],
        missing_providers=[k for k in store.PROVIDERS if not any(p == k for p, _ in accounts)],
        cash_dates=sorted(board["cash_dates"], key=lambda c: c["day"]),
        observations=sorted(observations, key=lambda r: r["as_of"], reverse=True),
    )


def save(directory, package, flows=None):
    now = datetime.now(KST)
    report = build(intelligence.board(directory, package, include_pnl=True), now)
    from . import live_valuation, market_review
    book = live_valuation.read(package)
    from agents.equities.cash_review import local_watch
    marked = None
    if book.index:
        marked = intelligence.board(directory,package,include_pnl=True,quote_book=book)
        if any(m["price"] is not None for a in marked["accounts"] for m in a["marks"]):
            # Keep broker/book observations as the independent control for cash-flow reconciliation.
            report["currencies"] = build(marked,now)["currencies"]
            report["valuation_basis"] = "연결 시세 반영 · 미연결 행은 원장 평가"
    report["price_watch"] = local_watch(package, marked["accounts"] if marked else [])
    report["overnight_watch"] = market_review.overnight_watch(package, now)
    if not report["account_dates"]:
        raise ValueError("로컬 잔고 원천이 없어 일일 검토를 저장하지 않았습니다.")

    def record(history):
        day = report["day"]
        previous = history.get(day, {})
        if previous.get("generated", "") > report["generated"]:
            return history
        # Keep distinct source marks from same-day reruns for later cash-flow reconciliation.
        def point_key(row):
            return tuple(row[k] for k in ("provider", "account", "currency", "source", "as_of"))
        valuations = {point_key(row): row for row in previous.get("valuations", [])}
        valuations.update((point_key(row), row) for row in report["valuations"])
        report["valuations"] = list(valuations.values())
        # A cache-only rerun preserves this day's references. A new day starts without imports.
        if flows:
            keys = tuple(k for k in FLOW_FIELDS if k != "net")
            merged = {tuple(r[k] for k in keys): r for r in previous.get("flows", [])}
            merged.update((tuple(r[k] for k in keys), r) for r in flows)
            report["flows"] = list(merged.values())
        else:
            report["flows"] = previous.get("flows", []) if flows is None else []
        earlier = max((d for d in history if d < day and "observations" in history[d]), default=None)
        report["compared_to"] = earlier
        if earlier:
            old = history[earlier]["observations"]
            fields = ("position", "category", "as_of", "origin", "title", "value", "analysis")
            seen = {tuple(row.get(f) for f in fields) for row in old}
            report["new_observations"] = [
                row for row in report["observations"] if tuple(row.get(f) for f in fields) not in seen
            ]
        else:
            report["new_observations"] = []
        history[day] = report
        return history

    intelligence.update_json(package, FILE, {}, record)
