"""Fetch public market-wide quotes. Only the native reader signs authenticated requests."""
import json
import os
import platform
import subprocess
import sys
import tempfile
from decimal import Decimal, localcontext
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, build_opener

from .store import ROOT, holding, number

READER = ROOT / ".local-build/account-reader"
SOURCE = Path(__file__).resolve().parent / "native/AccountReader.swift"
TICKERS = {"upbit": "https://api.upbit.com/v1/ticker/all?quote_currencies=KRW",
           "binance": "https://api.binance.com/api/v3/ticker/price"}


def build_reader():
    if platform.system() != "Darwin":
        raise ValueError("키체인 수집기는 macOS에서 빌드하세요.")
    READER.parent.mkdir(mode=0o700, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=READER.parent) as temp:
        exe = Path(temp) / READER.name
        subprocess.run(["/usr/bin/swiftc", "-parse-as-library", "-O", "-module-cache-path",
                        str(Path(temp) / "modules"), str(SOURCE), "-o", str(exe)], check=True)
        subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-", "--identifier",
                        "local.whale-tracking.account-reader", str(exe)], check=True)
        exe.chmod(0o700)
        os.replace(exe, READER)


def native(action, provider, alias, credentials=None):
    if not READER.is_file():
        raise ValueError("먼저 python3 -m private_accounts build 를 실행하세요.")
    payload = None
    if action == "connect-env":
        # Detect an older binary before handing any key material to it.
        check = subprocess.run([str(READER), "--supports-env"], capture_output=True, env={"PATH": "/usr/bin:/bin"})
        if check.returncode != 0 or check.stdout.strip() != b"1":
            raise ValueError("환경파일 등록을 사용하려면 먼저 수집기를 새 버전으로 빌드하세요.")
        payload = json.dumps(credentials).encode("utf-8")
    proc = subprocess.run([str(READER), action, provider, alias], check=True,
                          input=payload, stdout=subprocess.PIPE, env={"PATH": "/usr/bin:/bin"})
    if action == "sync":
        return json.loads(proc.stdout)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def public_prices(provider):
    with build_opener(NoRedirect()).open(TICKERS[provider], timeout=12) as response:
        data = response.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            raise ValueError("시세 응답이 너무 큽니다.")
    quotes = json.loads(data, parse_float=Decimal, parse_int=Decimal)
    prices = {}
    for row in quotes:
        if provider == "upbit" and row["market"].startswith("KRW-"):
            prices[row["market"][4:]] = number(row["trade_price"])
        elif provider == "binance" and row["symbol"].endswith("USDT"):
            prices[row["symbol"][:-4]] = number(row["price"])
    return prices


def sync_rows(provider, alias):
    balances = native("sync", provider, alias)
    try:
        prices = public_prices(provider)
    except (ValueError, TypeError, KeyError, OSError, HTTPError, URLError):
        print("공개 시세를 받지 못해 시세가 필요한 평가액은 비워 둡니다.", file=sys.stderr)
        prices = {}
    currency = "KRW" if provider == "upbit" else "USDT"
    prices[currency] = Decimal(1)
    with localcontext() as ctx:
        ctx.prec = 100
        rows = []
        for row in balances:
            symbol = row["symbol"]
            quantity = number(row["free"]) + number(row["locked"])
            price = prices.get(symbol)
            value = quantity * price if price is not None and price > 0 else None
            rows.append(holding(symbol, quantity, currency, value))
        return rows
