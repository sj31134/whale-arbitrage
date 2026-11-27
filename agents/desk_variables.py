"""Sector-specific inputs supplementing the shared public analyst feeds."""

from datetime import date, datetime
import json
from urllib.parse import urlsplit

from . import intelligence as intel

# Stable variable key, display label and destination analyst category.
FIELDS = {
    "whale": {
        "exchange_net": ("거래소 순유입", "market_flow"),
        "wallet_label": ("주소 라벨·출처", "market_flow"),
        "internal": ("내부 이체 검증", "market_flow"),
    },
    "crypto": {
        "depth": ("현물 호가 깊이", "market_flow"),
        "funding": ("펀딩 비율", "market_flow"),
        "open_interest": ("미결제약정", "market_flow"),
        "unlock": ("토큰 해제 일정", "fundamentals"),
    },
    "real_estate": {
        "sale": ("동일 면적 실거래", "fundamentals"),
        "land": ("대지지분", "fundamentals"),
        "senior_right": ("선순위 권리·인수금", "fundamentals"),
        "supply": ("공급 물량", "industry"),
        "occupancy": ("점유·임차 현황", "fundamentals"),
        "deposit": ("인수보증금", "fundamentals"),
        "cash_cost": ("취득비용·필요현금", "fundamentals"),
    },
    "equities": {
        "cashflow": ("잉여현금흐름", "fundamentals"),
        "dilution": ("주식 희석", "fundamentals"),
        "debt": ("순부채", "fundamentals"),
        "constituents": ("ETF 편입·비중", "fundamentals"),
        "shareholder_return": ("ROE·주주환원·자사주 소각", "fundamentals"),
    },
    "us_small_cap_high_beta": {
        "cap": ("시가총액", "fundamentals"),
        "beta": ("베타", "market_flow"),
        "turnover": ("거래대금", "market_flow"),
        "runway": ("현금 소진 기간", "fundamentals"),
        "event": ("예정 촉매", "fundamentals"),
        "issuance": ("증자·희석 공시", "fundamentals"),
    },
}


def save(package, desk, fields):
    key = fields.get("variable", "")
    if not package or key not in FIELDS.get(desk, {}):
        raise ValueError("이 담당에 등록할 수 있는 변수를 선택하세요.")
    limits = dict(subject=90, value=100, unit=40, basis=180, origin=600, as_of=10)
    record = {k: fields.get(k, "").strip() for k in limits}
    if any(not v or len(v) > limits[k] for k, v in record.items()):
        raise ValueError("대상·값·단위·측정 기준·기준일·공개 원문을 확인하세요.")
    src = urlsplit(record["origin"])
    if src.scheme != "https" or not src.hostname or src.username or src.password:
        raise ValueError("공개 HTTPS 원문 주소를 입력하세요.")
    if date.fromisoformat(record["as_of"]) > datetime.now(intel.KST).date():
        raise ValueError("관측일은 오늘까지 입력하세요.")
    record["key"] = key

    def merge(rows):
        # Retain separate dates/sources and replace corrections to one observation.
        identity = ("key", "subject", "as_of", "origin")
        return [r for r in rows if any(r[k] != record[k] for k in identity)] + [record]

    intel.update_json(package, f"variables_{desk}.json", [], merge)


def depth_funding_dates(records, subject_field):
    subjects = {}
    for row in records:
        if row.get("key") in ("depth", "funding"):
            dates = subjects.setdefault(row[subject_field], {"depth": set(), "funding": set()})
            dates[row["key"]].add(row["as_of"])
    return {subject: max(dates["depth"] & dates["funding"], default=None) for subject, dates in subjects.items()}


def small_cap_checks(rows, assets, categories, today):
    """Check dated manual observations; market membership alone cannot establish the classification."""
    latest = {asset: {} for asset in assets}
    for r in rows:
        if r.get("key"):
            seen = latest.setdefault(r["asset"], {})
            seen[r["key"]] = max(r["as_of"], seen.get(r["key"], ""))
    checks = {}
    for asset, dates in latest.items():
        gaps = []
        observed = []
        for key in ("cap", "beta"):
            label, cid = FIELDS["us_small_cap_high_beta"][key]
            if key not in dates:
                gaps.append(f"{label} 미등록")
            else:
                observed.append(f"{label} 기준일 {dates[key]}")
                if intel.outdated(dates[key], categories[cid]["stale_days"], today):
                    gaps.append(f"{label} 기준일 경과")
        assessment = ("분류 보류 · " + ", ".join(gaps) if gaps else
                      "시총·베타 자료 등록됨 · 수치, 측정 기간, 벤치마크와 분류 기준 대조 필요")
        checks[asset] = " · ".join([assessment, *observed])
    return checks


def read(package, desk):
    records = intel.private_json(package, f"variables_{desk}.json", [])
    rows = []
    if desk == "crypto":
        from . import public_variables
        for source in intel.private_json(package, public_variables.CACHE, {}).values():
            latest_public = {r["asset"]: r for r in source.get("rows", [])}
            for capture in source.get("captures", []):
                if capture["observed"] > latest_public.get(capture["asset"], {}).get("observed", ""):
                    latest_public[capture["asset"]] = capture
            for item in latest_public.values():
                name, _ = FIELDS[desk][item["key"]]
                status = source.get("status", "미수집")
                rows.append(dict(item, title=name, analysis=item["analysis"] + " · " + item["scope"] + " · 자동 " + status))
    latest = {}
    for r in sorted(records, key=lambda row: row["as_of"]):
        latest[(r["key"], r["subject"], r["origin"])] = r
    retained = list(latest.values())
    if desk == "crypto":
        common = depth_funding_dates(records, "subject")
        for r in records:
            if (r["key"] in ("depth", "funding") and r["as_of"] == common.get(r["subject"])
                    and latest[(r["key"], r["subject"], r["origin"])] is not r):
                retained.append(r)
    for r in retained:
        name, cid = FIELDS[desk][r["key"]]
        rows.append(
            dict(
                key=r["key"],
                cid=cid,
                title=name,
                asset=r["subject"],
                value=r["value"] + " " + r["unit"],
                as_of=r["as_of"],
                origin=r["origin"],
                analysis=r["basis"],
                scope="분야 등록 자료",
            )
        )
    if desk == "us_small_cap_high_beta":
        path = "agents/us_small_cap_high_beta/data/order_flow/order_flow_feed.json"
        try:
            data = json.loads((intel.ROOT / path).read_text())
            day = date.fromisoformat(data["as_of_date"]).isoformat()
            for key, name in (
                ("nasdaq_futures_change_pct", "나스닥 선물 등락률"),
                ("us_10y_yield_pct", "미 10년물 금리"),
            ):
                val = data["variables"].get(key)
                if isinstance(val, (int, float)):
                    rows.append(
                        dict(
                            cid="market_flow",
                            title=name,
                            value=f"{val} %",
                            as_of=day,
                            origin=path,
                            asset="",
                            analysis="저장소 연구 스냅샷 · 원문 재확인 필요",
                            scope="분야 연구 자료",
                        )
                    )
        except (OSError, ValueError, KeyError, TypeError):
            pass
    return rows
