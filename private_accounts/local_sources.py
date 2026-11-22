"""Offline sources for the private UI. No HTTP clients or environment exports."""
import hashlib
import os
import re
import stat
import zipfile
from datetime import datetime, timezone

from . import store

WORKBOOK = store.ROOT / "private_accounts/accounts_stocks.xlsx"
KEYS_FILE = WORKBOOK.parent / ".local/credentials.env"
FIELDS = ("증권사", "계좌", "종목", "평가손익", "수익률", "보유주식수", "평가금액", "매입단가", "현재가")
PROVIDER_NAMES = {**{label: key for key, label in store.PROVIDERS.items()},
                  **{key: key for key in store.PROVIDERS}, "NH투자증권": "namuh"}
ACCOUNT_NAMES = {"일반": "general", "위탁": "brokerage", "국내": "domestic", "해외": "overseas",
                 "연금저축": "pension", "isa": "isa", "irp": "irp", "현물": "spot"}


class WorkbookInputError(ValueError):
    """Displayable workbook diagnostics. Messages must not include any cell values."""


def open_private(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    stream = os.fdopen(fd, "rb")
    info = os.fstat(fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) & 0o077):
        stream.close()
        raise ValueError("개인 입력 파일의 소유자와 권한(0600)을 확인하세요.")
    return stream


def account_alias(label):
    known = ACCOUNT_NAMES.get(label.casefold())
    if known:
        return known
    # Unknown labels may contain names or account numbers. Keep them out of CLI arguments and diagnostics.
    return "acct-" + hashlib.sha256(label.encode()).hexdigest()[:12]


def amount(cell, signed=False):
    from decimal import Decimal
    if cell.value is None:
        return None
    if type(cell.value) not in (int, float):
        raise ValueError("숫자·수식 캐시를 확인하세요.")
    n = Decimal(str(cell.value))
    store.number(abs(n) if signed else n)
    return store.fixed(n)


def valuation_currency(fmt):
    # Locale-only markers such as [$-409] do not specify a currency.
    fmt = re.sub(r"\[\$-[\da-fA-F]+\]", "", fmt).upper()
    currencies = []
    if "USDT" in fmt:
        currencies.append("USDT")
    fmt = fmt.replace("USDT", "")
    if any(mark in fmt for mark in ("₩", "￦", "KRW", '"원"')):
        currencies.append("KRW")
    if "US$" in fmt or "USD" in fmt:
        currencies.append("USD")
    if len(currencies) != 1:
        raise ValueError("평가금액의 통화 표기가 불명확합니다. KRW, USD 또는 USDT를 표시하세요.")
    return currencies[0]


def workbook_accounts(path):
    """Read the current source in memory, preserving account labels and displayed measures."""
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise WorkbookInputError("개인 엑셀을 읽으려면 로컬 Python 환경에 openpyxl이 필요합니다.") from None
    accounts = {}
    with open_private(path) as stream:
        when = datetime.fromtimestamp(os.fstat(stream.fileno()).st_mtime, timezone.utc).isoformat(timespec="seconds")
        with zipfile.ZipFile(stream) as archive:
            if sum(entry.file_size for entry in archive.infolist()) > 32 * 1024 * 1024:
                raise WorkbookInputError("개인 엑셀 크기 제한을 초과했습니다.")
        stream.seek(0)
        # Read formula text to reject unevaluated formulas rather than treating them as empty holdings.
        try:
            wb = load_workbook(stream, read_only=True, data_only=False, keep_links=False)
        except Exception:
            raise WorkbookInputError("엑셀 통합문서 형식을 읽을 수 없습니다.") from None
        try:
            for tab, sheet in enumerate(wb.worksheets, 1):
                rows = iter(sheet.iter_rows())
                header = next(rows, ())
                if not header:
                    continue
                headings = [str(c.value or "").strip() for c in header]
                if any(headings.count(f) != 1 for f in FIELDS):
                    raise WorkbookInputError(f"시트 {tab}의 계좌현황 열을 확인하세요.")
                idx = [headings.index(f) for f in FIELDS]
                for n, row in enumerate(rows, 2):
                    try:
                        p, a, sym, gain, rate, qty, val, cost, price = [row[i] for i in idx]
                        # Ignore auxiliary columns. A row containing only valuation formulas
                        # is a workbook total and must not be counted as a position.
                        if (all(c.value is None for c in (p, a, sym, qty, cost, price))
                                and all(c.value is None or c.data_type == "f" for c in (gain, rate, val))):
                            continue
                        if not all(c.data_type != "f" and isinstance(c.value, str) and c.value.strip()
                                   for c in (p, a, sym)):
                            raise ValueError
                        provider = PROVIDER_NAMES[p.value.strip().casefold()]
                        label, symbol = a.value.strip(), sym.value.strip()
                        currency = valuation_currency(val.number_format)
                        account = accounts.setdefault((provider, account_alias(label)), {"label": label, "rows": []})
                        if account["label"] != label or qty.value is None or val.value is None:
                            raise ValueError
                        row_values = (symbol, currency, amount(qty), amount(val), amount(gain, True),
                                      amount(rate, True), amount(cost), amount(price))
                        if rate.value is not None and "%" not in rate.number_format:
                            raise ValueError
                        if row_values[2] == "0" and row_values[3] != "0":
                            raise ValueError
                        account["rows"].append(row_values)
                    except (ValueError, KeyError, IndexError) as exc:
                        raise WorkbookInputError(f"시트 {tab}, {n}행의 기관·수량·금액·통화·퍼센트 서식을 확인하세요.") from exc
        finally:
            wb.close()
    if not accounts:
        raise WorkbookInputError("계좌현황 행이 없습니다.")
    return when, accounts


def credential_groups(path):
    """Parse literal KEY=VALUE records locally. Never evaluate shell or expand references."""
    with open_private(path) as stream:
        raw = stream.read(256 * 1024 + 1)
    if len(raw) > 256 * 1024:
        raise ValueError("키 설정 파일이 너무 큽니다.")
    groups = {}
    for n, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, sep, value = line.removeprefix("export ").partition("=")
        if not sep:
            raise ValueError(f"키 설정 파일 {n}행의 구분자를 확인하세요.")
        name = re.sub(r"[\s_]+", "_", name.strip()).casefold()
        match = re.fullmatch(r"(.+?)(?:_account)?_(?:app_|api_|access_)?(key|secret)(?:_key)?", name)
        if not match:
            continue
        prefix, field = match.groups()
        value = value.strip()
        if len(value) > 1 and value[0] in ("'", '"') and value[-1] == value[0]:
            value = value[1:-1]
        group = groups.setdefault(prefix, {})
        if field in group:
            raise ValueError(f"키 설정 파일 {n}행에 중복 필드가 있습니다.")
        if not value or value.startswith(("$", "`")):
            raise ValueError(f"키 설정 파일 {n}행의 값이 비어 있거나 참조식입니다.")
        group[field] = value
    return groups


def exchange_keys(path, provider):
    if provider not in store.CRYPTO:
        raise ValueError("자산조회 전용으로 구성된 거래소만 등록할 수 있습니다.")
    pair = credential_groups(path).get(provider, {})
    if set(pair) != {"key", "secret"}:
        raise ValueError("해당 거래소의 조회 키 쌍을 확인하세요.")
    if any(not re.fullmatch(r"[!-~]{1,1022}", v) for v in pair.values()):
        raise ValueError("키 형식을 확인하세요.")
    return {"access": pair["key"], "secret": pair["secret"]}


def bindings(accounts, groups):
    """Associate candidate credential labels without inferring account access from a file name."""
    result = {}
    for prefix, fields in groups.items():
        if set(fields) != {"key", "secret"}:
            continue
        org, _, subtype = prefix.partition("_")
        provider = PROVIDER_NAMES.get(org)
        if provider is None:
            # A custom institution prefix may be ambiguous. Suggest only when multiple
            # distinct subtypes independently overlap a single provider's workbook.
            family = {k.partition("_")[2] for k in groups if k.startswith(org + "_")}
            matches = {p for p, _ in accounts if len(family & {
                a["label"].casefold() for (q, _), a in accounts.items() if q == p}) >= 2}
            if len(matches) != 1:
                continue
            provider = matches.pop()
            status = "기관 약칭 확인 필요"
        else:
            status = "조회 권한 확인 전" if provider in store.CRYPTO else "키 쌍 있음 · 국내 API 보류"
        candidates = [(p, alias) for (p, alias), item in accounts.items() if p == provider and
                      (not subtype or subtype in (alias, item["label"].casefold()) or
                       (subtype == "general" and alias == "brokerage"))]
        if len(candidates) == 1:
            result[candidates[0]] = status
    return result


def secure_directory(path):
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.lstat()
    if (path.resolve() != path or not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise ValueError("개인 설정 디렉터리의 경로·소유자·권한(0700)을 확인하세요.")


def protect_input(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise ValueError("개인 입력은 본인 소유의 일반 파일이어야 합니다.")
        os.fchmod(fd, 0o600)
    finally:
        os.close(fd)


def prepare(root):
    """Adopt the initial env without a backup copy; publish only non-secret binding states."""
    import fcntl
    import json
    import tempfile

    package = root / "private_accounts"
    workbook = package / "accounts_stocks.xlsx"
    local = package / ".local"
    secure_directory(local)
    vault = local / "credentials.env"
    initial = root / ".env"
    lock = os.open(local, os.O_RDONLY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        protect_input(workbook)
        if root == store.ROOT:
            store.exclude_from_mac_backup(workbook, local)
        when, accounts = workbook_accounts(workbook)
        if vault.exists():
            protect_input(vault)
            if initial.exists():
                with open_private(initial) as f:
                    if any(line.strip() and not line.lstrip().startswith(b"#") for line in f):
                        raise ValueError("기존 보호 키 파일이 있습니다. 새 키는 로컬 credentials.env에서 갱신하세요.")
        else:
            protect_input(initial)
        source = vault if vault.exists() else initial
        groups = credential_groups(source)
        links = bindings(accounts, groups)
        ready = [p for p in store.CRYPTO if fields_ready(groups.get(p, {}))]
        manifest = {"workbook_file_time": when, "ready": ready, "accounts": [
            {"provider": p, "alias": a, "credential_status": links.get((p, a))}
            for p, a in sorted(accounts)]}
        if not vault.exists():
            os.rename(initial, vault)
        if not initial.exists():
            fd = os.open(initial, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w") as stream:
                stream.write("# Local credentials are managed in private_accounts/.local/credentials.env\n")
        with tempfile.NamedTemporaryFile(mode="w", dir=local, delete=False) as tmp:
            json.dump(manifest, tmp, ensure_ascii=False)
        os.replace(tmp.name, local / "bindings.json")
    finally:
        os.close(lock)
    return manifest


def fields_ready(pair):
    return set(pair) == {"key", "secret"} and all(re.fullmatch(r"[!-~]{1,1022}", v) for v in pair.values())


def metadata(package):
    import json
    if package is None:
        return {}
    path = package / ".local/bindings.json"
    if not path.exists():
        return {}
    with open_private(path) as stream:
        return json.load(stream)


def workbook_view(account, when):
    # Reuse the existing within-currency weights. Detailed account metrics stay in the workbook.
    from decimal import Decimal, localcontext
    totals = {}
    with localcontext() as ctx:
        ctx.prec = 100
        for symbol, ccy, qty, val, *_ in account["rows"]:
            q, v = totals.get((symbol, ccy), (Decimal(0), Decimal(0)))
            totals[symbol, ccy] = (q + Decimal(qty), v + Decimal(val))
    rows = [(sym, ccy, store.fixed(q), store.fixed(v)) for (sym, ccy), (q, v) in totals.items()]
    doc = store.weighted_view(sorted(r for r in rows if r[2] != "0"), when)
    doc["source"] = "workbook"
    doc["time_basis"] = "file_modified"
    return doc
