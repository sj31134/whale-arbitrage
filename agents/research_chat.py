"""Prepare read-only, domain-limited research inputs for a private conversation."""

import re
from datetime import date, datetime

from . import intelligence as intel
from .personas import PERSONAS
from .portfolio import TACTICAL_REVIEW

MANAGER = "manager"
NAMES = {MANAGER: "투자 매니저", **intel.LABELS}
NAMES.update(real_estate="부동산·경매", equities="주식·ETF", us_small_cap_high_beta="미국 소형·고베타 주식")
# Each section is selected from the project skill, never from another chat.
SECTIONS = {"whale": "5", "crypto": "5", "equities": "2", "us_small_cap_high_beta": "5", "real_estate": "1"}
VARIABLES = {
    "whale": "체인·거래 시각, 거래소 순유입, 주소 라벨 출처, 내부 이체 여부",
    "crypto": "현물 가격·거래량, 호가 깊이, 펀딩·미결제약정, 발행·해제 일정",
    "real_estate": "동일 면적 실거래, 대지지분, 공급량, 선순위 권리, 보증금·필요 현금",
    "equities": "매출·현금흐름, 부채·희석, 실적 공시, ETF 편입 중복과 비용",
    "us_small_cap_high_beta": "시총 기준일, 베타 기간·벤치마크, 거래대금, 증자·현금 소진, 촉매 일정",
}


def profile(desk):
    if desk not in NAMES:
        raise ValueError("등록된 담당을 선택하세요.")
    root = intel.ROOT
    readme = (root / "agents" / desk / "README.md").read_text().split("\n\n")[1]
    purpose = readme.split(" [")[0].strip()
    persona = PERSONAS[desk]
    if desk == MANAGER:
        return dict(purpose=purpose, persona=persona, rules=purpose + "\n" + persona.instruction(),
                    variables="선택한 분야의 근거, 의견 차이, 자료 공백")
    mandate = (root / "agents/INVESTMENT_MANDATE.md").read_text()
    row = next(line for line in mandate.splitlines() if line.startswith("| [") and f"]({desk}/)" in line)
    principles = (root / ".agents/skills/investor-principles/SKILL.md").read_text()
    sections = dict(re.findall(r"^## (\d+)\. [^\n]*\n(.*?)(?=^## |\Z)", principles, re.M | re.S))
    rules = "\n".join([persona.instruction(), purpose, row, sections[SECTIONS[desk]].strip(), sections["8"].strip()])
    if desk == "real_estate":
        estate = (root / ".agents/skills/real-estate-subagent/SKILL.md").read_text()
        # Include the actual source-audit and rights/valuation requirements, excluding front matter.
        rules += "\n" + estate.partition("## 1.")[2]
    _, candidate, review = row.strip("|").split("|")[1:]
    return dict(
        purpose=purpose,
        persona=persona,
        rules=rules,
        variables=VARIABLES[desk],
        candidate=candidate.strip(),
        review=review.strip(),
    )


def source_allowed(row, desk):
    return desk in intel.SOURCE_ROLES.get(row.get("source_id"), intel.DOMAINS)


def shared_sources(reports):
    """Same public URL appearing in more than one selected report, with its actual references."""
    sources = {}
    for desk, report in reports.items():
        for fact in report["facts"]:
            origin = fact["source"]
            if origin.startswith("https://"):
                by_desk = sources.setdefault(origin, {})
                by_desk.setdefault(desk, []).append(fact["ref"])
    return {url: refs for url, refs in sources.items() if len(refs) > 1}


def research_input(
    board, desk, question="", followup="", public_flows=(), variables=(), snapshot_time=None
):
    checked = snapshot_time or datetime.now(intel.KST)
    brief = intel.brief_from_board(board, desk)
    terms = set(re.findall(r"[\w.-]{2,}", (question + " " + followup).casefold()))
    facts = {}
    inputs = {}
    holdings = []
    for cid, cat in brief["categories"].items():
        context = [r for r in cat["context"] if source_allowed(r, desk)]
        latest = max(context, key=lambda r: (not r["stale"], r["as_of"]), default=None)
        inputs[cid] = dict(
            title=cat["title"],
            question=cat["question"],
            market_example=latest,
            sources=[
                {"name": s["label"], "status": s["status"], "collected": s["collected"]}
                for s in cat["sources"]
                if source_allowed(s, desk)
            ],
        )

    def include(row, cid, scope, asset=""):
        if not source_allowed(row, desk):
            return
        origin, title = row["origin"], row["title"]
        key = (scope, asset, cid, origin, title, row["as_of"], row["value"])
        facts[key] = dict(
            scope=scope,
            asset=asset,
            category=inputs[cid]["title"],
            title=title,
            value=row["value"],
            as_of=row["as_of"],
            source=origin,
            stale=row["stale"],
            analysis=row["analysis"],
            cid=cid,
        )

    for index, p in enumerate(brief["positions"], 1):
        holdings.append(dict(symbol=p["symbol"], currency=p["currency"], as_of=p["as_of"], task=p["task"]))
        for cid, rows in p["evidence"].items():
            for row in rows:
                if cid == "exposure":
                    # Only a scoped concentration indicator. Raw account identifiers and cash amounts stay in ledger.
                    row = dict(
                        row,
                        analysis=f'보유행 {index} · 해당 계좌의 {p["currency"]} 평가액 내 비중',
                        origin=f"로컬 보유 자료 · 행 {index}",
                    )
                include(row, cid, "보유 직접 근거", p["symbol"])
    direct_keys = {(f["cid"], f["source"], f["title"], f["as_of"]) for f in facts.values()}
    for cid, cat in brief["categories"].items():
        for row in cat["context"]:
            include(row, cid, "공통 시장 자료")
        for row in board["categories"][cid]["observations"]:
            # Public candidates remain available even when this desk has no positions.
            if not row.get("subjects") or row.get("target") or desk not in row.get("domains", []):
                continue
            if desk == "us_small_cap_high_beta" and not any(
                x.upper().removeprefix("US-") in TACTICAL_REVIEW for x in row["subjects"]
            ):
                continue
            if (cid, row["origin"], row["title"], row["as_of"]) not in direct_keys:
                include(row, cid, "공개 후보 자료")
    # Daily imports with an explicit public market/theme can supplement the assigned price/flow category.
    for flow in public_flows:
        if desk == "equities":
            applies = ("주식" in flow["theme"] or "ETF" in flow["theme"]) and "미국" in flow["market"]
            if flow["market"] in {"한국 유가증권시장", "코스피", "코스닥"}:
                applies = flow["metric"] == "순매수"
        elif desk == "us_small_cap_high_beta":
            applies = "미국" in flow["market"] and "소형주" in flow["theme"]
        else:
            applies = False
        if applies:
            age = (checked.date() - date.fromisoformat(flow["as_of"])).days
            include(
                dict(
                    title=flow["theme"],
                    value=flow["net"] + " " + flow["unit"],
                    as_of=flow["as_of"],
                    origin=flow["source"],
                    stale=age > 7 or age < 0,
                    analysis=flow["market"] + " · " + flow["period"] + " · " + flow["metric"],
                ),
                "market_flow",
                "공통 시장 자료",
            )
    for row in variables:
        cid = row["cid"]
        old = intel.outdated(row["as_of"], board["categories"][cid]["stale_days"], checked.date())
        include(dict(row, stale=old), cid, row["scope"], row["asset"])

    def rank(f):
        label = " ".join([f["asset"], f["title"], f["category"], f["analysis"]]).casefold()
        matches = sum(t in label or bool(f["asset"] and f["asset"].casefold() in t) for t in terms)
        return (matches, not f["stale"], f["scope"] == "보유 직접 근거", f["cid"] != "exposure", f["as_of"])

    holdings.sort(key=lambda p: any(p["symbol"].casefold() in term for term in terms), reverse=True)
    ordered = sorted(facts.values(), key=rank, reverse=True)
    # Keep coverage across inputs even when a market feed publishes hundreds of tickers.
    selected = ordered[:6]
    for cid in inputs:
        first = next((r for r in ordered if r["cid"] == cid), None)
        if first and first not in selected:
            selected.append(first)
    for i, f in enumerate(selected, 1):
        f["ref"] = f"{desk}-{i}"
    return dict(
        desk=desk,
        at=checked.isoformat(timespec="seconds"),
        inputs=inputs,
        holdings=holdings,
        facts=selected,
        total_facts=len(ordered),
    )


def evidence_answer(ctx):
    facts = ctx["facts"]
    lines = []
    for f in facts[:4]:
        age = " · 기준일 경과" if f["stale"] else ""
        lines.append(f'[{f["ref"]}] {f["scope"]} · {f["title"]} {f["value"]} ({f["as_of"]}{age})')
    if not lines:
        lines.append("연결된 관측이 없습니다.")
    lines.append("추가 확인 변수 · " + VARIABLES[ctx["desk"]])
    return "\n".join(lines)
