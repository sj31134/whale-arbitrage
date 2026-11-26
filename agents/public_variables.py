"""Fixed BTC/ETH derivatives and spot depth sample, independent of any portfolio."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.error import HTTPError

from . import analyst_feeds as feeds, intelligence as intel

CACHE = "public_desk_variables.json"
SAMPLE = ("BTC", "ETH")
URLS = {"depth": "https://api.upbit.com/v1/orderbook?markets=KRW-BTC,KRW-ETH&count=5"}
for asset in SAMPLE:
    URLS["funding_" + asset] = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={asset}USDT&limit=1"
    URLS["open_interest_" + asset] = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={asset}USDT"


def parse(key, data, now):
    obj = json.loads(data, parse_float=str)
    result = []

    def add(variable, subject, value, ts, basis):
        at = datetime.fromtimestamp(int(ts) / 1000, timezone.utc)
        if at > now:
            raise ValueError("future record")
        result.append(dict(key=variable, asset=subject, value=value, cid="market_flow",
                           origin=URLS[key], observed=at.isoformat(), as_of=at.astimezone(intel.KST).date().isoformat(),
                           analysis=basis + " · " + at.astimezone(intel.KST).strftime("%H:%M:%S KST"),
                           scope="자동 공개 표본"))

    if key == "depth":
        for row in obj:
            symbol = row["market"].removeprefix("KRW-")
            if row["market"] != "KRW-" + symbol or symbol not in SAMPLE:
                continue
            levels = row["orderbook_units"][:5]
            if len(levels) != 5:
                continue
            def side_value(side):
                sizes = [(feeds.num(t[side + "_size"]), feeds.num(t[side + "_price"])) for t in levels]
                if any(size < 0 or price <= 0 for size, price in sizes):
                    raise ValueError("invalid book")
                return sum(size * price for size, price in sizes)
            add("depth", symbol, f'매수 {side_value("bid"):,.0f} / 매도 {side_value("ask"):,.0f} KRW',
                row["timestamp"], "업비트 원화 현물 · 각 방향 상위 5호가 잔량×가격 합계")
    else:
        variable, asset = key.rsplit("_", 1)
        r = obj[-1] if variable == "funding" else obj
        if r["symbol"] != asset + "USDT":
            raise ValueError("wrong contract")
        if variable == "funding":
            add(variable, asset, f'{100*feeds.num(r["fundingRate"]):f} %', r["fundingTime"],
                "바이낸스 USDT 무기한 · 최근 정산 회차")
        else:
            amount = feeds.num(r["openInterest"])
            if amount < 0:
                raise ValueError("invalid interest")
            add(variable, asset, f"{amount:f} {asset}", r["time"], "바이낸스 USDT 무기한 · 기초자산 수량")
    if not result:
        raise ValueError("no usable observations")
    return result


def refresh(package, fetcher=feeds.fetch):
    now = datetime.now(timezone.utc)
    at = now.isoformat()

    def run(key):
        try:
            data = fetcher({"kind": "quotes", "url": URLS[key]})
            rows = parse(key, data, datetime.now(timezone.utc))
            status = "수집 완료" if key != "depth" or {r["asset"] for r in rows} == set(SAMPLE) else "일부 누락"
            return key, dict(attempt=at, success=at, status=status, rows=rows)
        except HTTPError as exc:
            status = f"HTTP {exc.code}"
        except (OSError, ValueError, KeyError, TypeError, ArithmeticError, IndexError):
            status = "수집 실패"
        return key, dict(attempt=at, status=status)

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = dict(pool.map(run, URLS))

    def merge(cache):
        for key, result in results.items():
            old = cache.get(key, {})
            if at < old.get("attempt", ""):
                continue
            rows = {r["asset"]: r for r in old.get("rows", [])}
            for r in result.get("rows", []):
                if r["observed"] >= rows.get(r["asset"], {}).get("observed", ""):
                    rows[r["asset"]] = r
            cache[key] = {**old, **result, "rows": list(rows.values())}
        return cache
    intel.update_json(package, CACHE, {}, merge)



def import_capture(package, key, checked_at, data):
    if key not in URLS or not isinstance(data, list) or not 1 <= len(data) <= len(SAMPLE):
        raise ValueError("고정 표본과 공개 원문 행을 확인하세요.")
    checked = datetime.fromisoformat(intel.store.timestamp(checked_at))
    if key != "depth" and len(data) != 1:
        raise ValueError("파생 원문은 한 계약의 한 관측을 입력하세요.")
    expected = ({"symbol", "openInterest", "time"} if key.startswith("open_interest") else
                {"symbol", "fundingRate", "fundingTime"} if key.startswith("funding") else
                {"market", "timestamp", "orderbook_units"})
    if any(not isinstance(r, dict) or set(r) != expected for r in data):
        raise ValueError("해당 공개 원천의 관측 필드를 확인하세요.")
    raw = data[0] if key.startswith("open_interest") else data
    rows = parse(key, json.dumps(raw), checked)
    if len(rows) != len(data) or len({r["asset"] for r in rows}) != len(rows):
        raise ValueError("고정 시장 표본의 중복 또는 누락을 확인하세요.")
    def merge(cache):
        state = cache.setdefault(key, {})
        captured = {r["asset"]: r for r in state.get("captures", [])}
        for row in rows:
            old = captured.get(row["asset"], {})
            if old.get("observed", "") > row["observed"] or old.get("checked", "") > checked.isoformat():
                raise ValueError("이전 시각의 공개 관측입니다.")
            captured[row["asset"]] = dict(row, checked=checked.isoformat(), scope="원문 확인 표본")
        state["captures"] = list(captured.values())
        return cache
    intel.update_json(package, CACHE, {}, merge)
    return len(rows)
