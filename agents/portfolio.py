"""Route read-only, account-local position views to the five research domains."""
import json
from datetime import datetime
from decimal import Decimal, localcontext
from functools import lru_cache
import unicodedata

from private_accounts import local_sources, store


DOMAINS = ("whale", "crypto", "real_estate", "equities", "us_small_cap_high_beta")
# Stablecoins have issuer and peg risk, so they remain in crypto research.
CASH_NAMES = {"KRW", "USD", "EUR", "JPY", "CNY", "HKD", "GBP", "AUD", "CAD",
              "CHF", "SGD", "원화", "달러", "현금", "예수금"}


def load_roles(package):
    """Optional explicit assignments. The private file is subject to the workbook's access policy."""
    path = package / ".local/agent_roles.json"
    if not path.exists():
        return {}
    with local_sources.open_private(path) as stream:
        rows = json.load(stream)
    if not isinstance(rows, list):
        raise ValueError("개인 자산 담당표는 행 목록이어야 합니다.")
    roles = {}
    for row in rows:
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip()
                                           for k in ("provider", "account", "symbol", "role")):
            raise ValueError("개인 자산 담당표의 기관·별칭·종목·담당을 확인하세요.")
        key = (row["provider"], row["account"], row["symbol"])
        role = row["role"]
        if key[0] not in store.PROVIDERS or role not in (*DOMAINS[1:], "cash", "other") or key in roles:
            raise ValueError("개인 자산 담당표의 기관, 담당 또는 중복 행을 확인하세요.")
        roles[key] = role
    return roles


def normalize(value):
    return " ".join(unicodedata.normalize("NFKC", value).strip().casefold().split())


@lru_cache(maxsize=1)
def public_identities():
    """Match only unambiguous public identifiers. Never use a research book as a balance."""
    registry = store.ROOT / "branch/investor_agent/data/timeline/verified_sources.json"
    records = json.loads(registry.read_text())["registry"]
    names = {}
    for key, record in records.items():
        role = {"Equities": "equities", "Real Estate": "real_estate"}.get(record.get("asset_class"))
        if not role:
            continue
        aliases = (key, key.partition("-")[2], record["asset_name"])
        for alias in aliases:
            if alias:
                names.setdefault(normalize(alias), []).append((role, aliases))
    return {k: matches[0] for k, matches in names.items() if len(matches) == 1}


# Research watchlist in the project's investor mandate. Membership triggers verification.
TACTICAL_REVIEW = {"LUNR", "POET", "CIFR", "CLBT", "OKLO"}


def responsibilities(provider, symbol, role):
    if role is None:
        if symbol.upper() in CASH_NAMES:
            return {}
        if provider not in store.CRYPTO:
            if symbol.upper().removeprefix("US-") in TACTICAL_REVIEW:
                role = "us_small_cap_high_beta"
            else:
                known = public_identities().get(normalize(symbol))
                if not known:
                    return {"equities": "증권 계좌 상품 유형 확인"}
                role = known[0]
        else:
            role = "crypto"
    if role == "crypto":
        return {"crypto": "보유 분석", "whale": "온체인 흐름 교차 검토"}
    if role == "us_small_cap_high_beta":
        return {"equities": "보유 분석", role: "시총·베타·단기 수급 검증"}
    if role in ("cash", "other"):
        return {}
    return {role: "보유 분석"}


def portfolio_accounts(directory, package, *, include_pnl=False, quote_book=None):
    """Use one source per account. Returned weights keep their original account/currency denominator."""
    workbook = package / "accounts_stocks.xlsx" if package is not None else None
    books = {}
    if workbook is not None and workbook.exists():
        modified, books = local_sources.workbook_accounts(workbook, include_pnl=include_pnl or quote_book is not None)
    accounts = []
    with store.database(directory) as con:
        snapshots = {(p, a): (sid, when) for p, a, _, sid, when in store.profiles(con)
                     if sid is not None}
        for provider, account in sorted(books.keys() | snapshots.keys()):
            key = (provider, account)
            saved = snapshots.get(key)
            if key in books and (not saved or datetime.fromisoformat(modified) > datetime.fromisoformat(saved[1])):
                view = local_sources.workbook_view(books[key], modified)
            else:
                sid, when = saved
                rows = store.positions(con, sid)
                view = store.weighted_view(rows, when)
                view.update(source="snapshot", time_basis="balance_as_of")
            raw = books[key]["rows"] if view["source"] == "workbook" else rows
            if quote_book is not None:
                from private_accounts.live_valuation import mark_account
                pnl = books[key].get("pnl", {}) if view["source"] == "workbook" else {}
                identifiers = books[key].get("identifiers", {}) if view["source"] == "workbook" else {}
                marks = mark_account(quote_book, provider, raw, pnl, view["as_of"], account, identifiers)
                view["marks"] = marks
                view["holdings"] = [{k: m[k] for k in ("symbol", "currency", "weight_pct")} for m in marks]
                raw = [(m["symbol"], m["currency"], m["qty"], m["value"]) for m in marks]
            totals = {}
            for _, currency, _, value, *_ in raw:
                if currency not in totals:
                    totals[currency] = Decimal(0)
                if value is None or totals[currency] is None:
                    totals[currency] = None
                else:
                    with localcontext() as ctx:
                        ctx.prec = 100
                        totals[currency] += Decimal(value)
            if include_pnl:
                if quote_book is not None:
                    view["pnl"] = {(m["symbol"],m["currency"]):m["gain"] for m in view["marks"]}
                else:
                    view["pnl"] = books[key].get("pnl", {}) if view["source"] == "workbook" else {}
            accounts.append(dict(provider=provider, account=account, **view,
                                 totals={c: store.fixed(v) if v is not None else None for c, v in totals.items()}))
    return accounts


def portfolio_review(directory, package, domain):
    roles = load_roles(package) if package is not None else {}
    accounts = portfolio_accounts(directory, package)
    for account in accounts:
        provider, alias = account["provider"], account["account"]
        matches = []
        for holding in account["holdings"]:
            symbol = holding["symbol"]
            tasks = responsibilities(provider, symbol, roles.get((provider, alias, symbol)))
            if domain in tasks:
                matches.append(dict(holding, task=tasks[domain]))
        account["holdings"] = matches
        del account["totals"]
    return {"agent": domain, "mandate": "agents/INVESTMENT_MANDATE.md",
            "research": f"agents/{domain}/README.md", "accounts": accounts,
            "providers_without_data": [p for p in store.PROVIDERS
                                       if not any(a["provider"] == p for a in accounts)]}
