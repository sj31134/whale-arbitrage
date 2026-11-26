"""Public collectors. No function here accepts an account, a holding or a search term."""

import csv
import io
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class SourceUnavailable(ValueError):
    pass


FRED_CAPTURES = {
    "UNRATE": ("macro", "미국 실업률", "%"),
    "CPIAUCSL": ("macro", "미국 소비자물가지수", "지수"),
    "INDPRO": ("industry", "미국 산업생산", "지수"),
    "DCOILBRENTEU": ("global_events", "브렌트유 현물 가격", "USD/배럴"),
    "DGS10": ("financial_conditions", "미국 10년 국채금리", "%"),
    "DEXKOUS": ("financial_conditions", "달러당 원화", "원/USD"),
    "BAMLH0A0HYM2": ("financial_conditions", "미국 하이일드 신용 스프레드", "%"),
    "VIXCLS": ("market_flow", "미국 변동성 지수", "지수"),
}
CAPTURES = {**{key: (v[0], v[1] + " · FRED 원문") for key, v in FRED_CAPTURES.items()},
    "upbit_sample": ("market_flow", "업비트 BTC·ETH · 원문 표본"),
    "FX_USDKRW": ("financial_conditions", "하나은행 달러 고시환율 · 네이버 원문"),
    "upbit": ("market_flow", "업비트 원화마켓 · 공식 화면 대조"),
    "edgar": ("fundamentals", "미 SEC 분기공시 · 공식 화면 대조"),
    "dart_recent": ("fundamentals", "DART 최근공시 · 공개 목록 확인분"),
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def fetch(source):
    headers = {"User-Agent": "whale-tracking/1.0 local public research"}
    endpoint = source["url"]
    if source["kind"] == "x":
        token = os.environ.get("X_BEARER_TOKEN")
        if not token:
            raise SourceUnavailable("X 조회 토큰 필요")
        headers["Authorization"] = "Bearer " + token
    if source["kind"] == "dart":
        key = os.environ.get("DART_API_KEY")
        if not key:
            raise SourceUnavailable("DART 조회 키 필요")
        today = date.today()
        endpoint += "?" + urlencode(
            dict(
                crtfc_key=key,
                bgn_de=(today - timedelta(days=13)).strftime("%Y%m%d"),
                end_de=today.strftime("%Y%m%d"),
                pblntf_ty="A",
                page_count=100,
            )
        )
    if source["kind"] == "atom" and os.environ.get("SEC_USER_AGENT"):
        headers["User-Agent"] = os.environ["SEC_USER_AGENT"]
    # Keep credentials on the exact configured HTTPS endpoint, without an ambient proxy.
    req = Request(endpoint, headers=headers)
    with build_opener(ProxyHandler({}), NoRedirect()).open(req, timeout=7) as response:
        data = response.read(4_000_001)
    if len(data) > 4_000_000:
        raise SourceUnavailable("응답 크기 초과")
    return data


def normalized_time(value):
    text = str(value)
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        dt = parsedate_to_datetime(text)
    if dt is None:
        raise ValueError("날짜 없음")
    if dt.tzinfo is None:
        if len(text) != 10:
            raise ValueError("시간대 없음")
        return date.fromisoformat(text).isoformat()
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def observation(title, value, as_of, origin, analysis, subjects=(), domains=()):
    return dict(
        title=str(title)[:350],
        value=str(value)[:220],
        as_of=normalized_time(as_of),
        origin=str(origin)[:1000],
        analysis=str(analysis)[:450],
        subjects=[str(x) for x in subjects if x],
        domains=list(domains),
    )


def num(value):
    try:
        n = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("원천의 숫자 형식을 확인하세요.") from None
    if not n.is_finite() or abs(n.adjusted()) > 100:
        raise ValueError("숫자 범위 오류")
    return n


def fred(s, data):
    rows = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
    vals = sorted(
        (r.get("observation_date") or r.get("DATE"), num(r[s["id"]]))
        for r in rows
        if r[s["id"]] not in ("", ".")
    )
    day, latest = vals[-1]
    unit = s["unit"]
    note = "이전 관측 없음"
    if len(vals) > 1:
        before, prior = vals[-2]
        delta = latest - prior
        note = f"{before} 대비 {delta:+f} {'%p' if unit == '%' else unit}"
    row = observation(s["label"], f"{latest} {unit}", day, "https://fred.stlouisfed.org/series/" + s["id"], note)
    row["history"] = [[d, format(v, "f")] for d, v in vals[-12:]]
    return [row]


def events(s, data):
    root = ET.fromstring(data)
    result = []
    if s["kind"] == "atom":
        for item in root.findall("{*}entry"):
            title = item.findtext("{*}title")
            ref = item.find("{*}link")
            if not title or ref is None:
                continue
            cik = re.search(r"\((\d{1,10})\)", title)
            tags = ["CIK" + cik[1].zfill(10)] if cik else []
            result.append(
                observation(
                    title,
                    "분기공시",
                    item.findtext("{*}updated"),
                    ref.get("href"),
                    "제출 사실 확인. 실적 내용은 공시 원문 검토 대상",
                    tags,
                    ["equities", "us_small_cap_high_beta"],
                )
            )
    else:
        for item in root.findall(".//item"):
            title, day = item.findtext("title"), item.findtext("pubDate") or item.findtext("{*}date")
            if title and day:
                result.append(
                    observation(
                        title,
                        "공개 발표",
                        day,
                        item.findtext("link") or s["url"],
                        "영향 지역·대상과 시행 시점을 대조",
                    )
                )
    return sorted(result, key=lambda r: r["as_of"], reverse=True)[:60]


def read_public(s, data, now):
    kind = s["kind"]
    if kind == "fred":
        return fred(s, data)
    if kind in ("rss", "atom"):
        return events(s, data)
    obj = json.loads(data)
    if kind == "dart":
        if obj.get("status") not in ("000", "013"):
            raise SourceUnavailable("DART 인증 또는 호출 한도 확인")
        result = []
        for r in obj.get("list", []):
            day = datetime.strptime(r["rcept_dt"], "%Y%m%d").date()
            result.append(
                observation(
                    r["corp_name"] + " · " + r["report_nm"],
                    "정기공시",
                    day,
                    "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=" + str(int(r["rcept_no"])),
                    "접수된 정기보고서 · 정정 여부와 실적 원문 확인",
                    [r["corp_name"], r.get("stock_code")],
                    ["equities"],
                )
            )
        return result
    if kind == "votes":
        result = []
        for raw in obj:
            r = {k.lower(): v for k, v in raw.items()}
            day = str(r["date"])[:10]
            result.append(
                observation(
                    r["title"],
                    f"찬성 {int(r['ayecount'])} · 반대 {int(r['nocount'])}",
                    day,
                    f"https://votes.parliament.uk/Votes/Commons/Division/{int(r['divisionid'])}",
                    "영국 하원 표결. 법 시행 여부는 별도 확인",
                )
            )
        return result
    if kind == "x":
        return [
            observation(
                r["trend_name"],
                f"{int(r['tweet_count']):,} 게시물" if r.get("tweet_count") is not None else "게시량 미제공",
                now,
                "https://docs.x.com/x-api/trends/get-trends-by-woeid",
                f"전 세계 WOEID 1 · 응답 순서 {i}위 · 원문 검증 대기",
                [r["trend_name"].lstrip("#$")],
            )
            for i, r in enumerate(obj["data"], 1)
        ]
    if kind == "upbit":
        result = []
        for r in obj:
            quote, symbol = r["market"].split("-", 1)
            if quote != "KRW":
                continue
            when = datetime.fromtimestamp(int(r["trade_timestamp"]) / 1000, timezone.utc).isoformat()
            change = num(r["signed_change_rate"]) * 100
            result.append(
                observation(
                    symbol,
                    f"{num(r['trade_price']):,f} KRW",
                    when,
                    s["url"],
                    f"전일 UTC 종가 대비 {change:+.2f}%",
                    [symbol],
                    ["crypto", "whale"],
                )
            )
        return result
    raise ValueError("알 수 없는 공개 원천")


def captured_observations(source, rows, checked):
    """Normalize independently verified observations from fixed public sources."""
    if source not in CAPTURES or not isinstance(rows, list) or not 1 <= len(rows) <= 1000:
        raise ValueError("공식 원천과 확인한 행 수를 확인하세요.")
    if source in FRED_CAPTURES:
        _, label, unit = FRED_CAPTURES[source]
        unique = {}
        for r in rows:
            if not isinstance(r, dict) or set(r) != {"day", "value"}:
                raise ValueError("FRED 원문의 관측일과 수치를 확인하세요.")
            day = date.fromisoformat(r["day"])
            if day > checked.date() or day in unique:
                raise ValueError("FRED 기준일이 미래이거나 중복입니다.")
            unique[day] = num(r["value"])
        records = [f"{day},{value}" for day, value in sorted(unique.items())]
        data = ("observation_date," + source + "\n" + "\n".join(records)).encode()
        return fred(dict(label=label, unit=unit, id=source), data)
    result = {}
    for r in rows:
        if not isinstance(r, dict):
            raise ValueError("공개 원천 행의 형식을 확인하세요.")
        if source in ("upbit", "upbit_sample"):
            if (set(r) != {"market", "trade_timestamp", "trade_price", "signed_change_rate"}
                    or not isinstance(r["market"], str) or not re.fullmatch(r"KRW-[A-Z0-9]+", r["market"])
                    or type(r["trade_timestamp"]) is not int or not 0 < r["trade_timestamp"] <= int(checked.timestamp() * 1000)
                    or num(r["trade_price"]) <= 0 or num(r["signed_change_rate"]) < -1):
                raise ValueError("원화마켓 코드·체결시각·가격·등락률을 확인하세요.")
            s = dict(kind="upbit", url="https://api.upbit.com/v1/ticker/all?quote_currencies=KRW")
            if source == "upbit_sample":
                if r["market"] not in {"KRW-BTC", "KRW-ETH"}:
                    raise ValueError("고정 표본의 마켓을 확인하세요.")
                s["url"] = "https://api.upbit.com/v1/ticker?markets=KRW-BTC,KRW-ETH"
            row, = read_public(s, json.dumps([r]), checked)
            key = r["market"]
        elif source == "FX_USDKRW":
            if set(r) != {"at", "price"} or len(rows) != 1 or num(r["price"]) <= 0:
                raise ValueError("고시환율 단가 및 기준시각을 확인하세요.")
            at = datetime.fromisoformat(r["at"])
            if at.utcoffset() is None or at > checked:
                raise ValueError("고시환율 시각을 확인하세요.")
            key = "FX_USDKRW"
            row = observation("달러 고시환율", f'{num(r["price"])} 원/USD', r["at"],
                              "https://api.stock.naver.com/marketindex/exchange/FX_USDKRW",
                              "하나은행 고시 · USD 1단위의 원화 환산")
        elif source == "edgar":
            if set(r) != {"title", "url", "time"} or not all(isinstance(v, str) for v in r.values()):
                raise ValueError("SEC 공시 필드를 확인하세요.")
            cik = re.search(r"\((\d{1,10})\)\s*\(Filer\)", r["title"])
            path = re.fullmatch(r"https://www\.sec\.gov/Archives/edgar/data/(\d+)/(\d{18})/(\d{10}-\d{2}-\d{6})-index\.htm", r["url"])
            if (not cik or not path or int(cik[1]) != int(path[1]) or path[2] != path[3].replace("-", "")
                    or not re.match(r"10-Q(?:/A)? - ", r["title"])):
                raise ValueError("SEC 분기공시의 발행인과 접수번호를 확인하세요.")
            if datetime.fromisoformat(r["time"].replace("Z", "+00:00")).utcoffset() is None:
                raise ValueError("SEC 공시 시각의 시간대를 확인하세요.")
            key = r["url"]
            row = observation(r["title"], "분기공시", r["time"], key, "제출 원문 · 정정 여부와 실적 확인",
                              ["CIK" + cik[1].zfill(10)], ["equities", "us_small_cap_high_beta"])
        else:
            if (set(r) != {"title", "company", "url", "day", "time"}
                    or not all(isinstance(v, str) and v.strip() for v in r.values())
                    or not re.fullmatch(r"https://dart\.fss\.or\.kr/dsaf001/main\.do\?rcpNo=\d{14}", r["url"])):
                raise ValueError("DART 공개 목록의 접수번호와 원문을 확인하세요.")
            # The recent-filings page can display older receipt dates. Only the date is unambiguous.
            day = datetime.strptime(r["day"], "%Y.%m.%d").date()
            datetime.strptime(r["time"], "%H:%M")
            key = r["url"]
            row = observation(r["company"] + " · " + r["title"], "공시 접수", day, key,
                              "DART 전체 최근공시 목록 · 접수 사실, 내용은 개별 원문 확인", [r["company"]], ["equities"])
        if key in result:
            raise ValueError("공개 목록에 중복된 시장 또는 접수번호가 있습니다.")
        if len(row["as_of"]) == 10:
            future = date.fromisoformat(row["as_of"]) > checked.astimezone(timezone(timedelta(hours=9))).date()
        else:
            future = datetime.fromisoformat(row["as_of"]) > checked
        if future:
            raise ValueError("확인시각 이후의 관측이 있습니다.")
        result[key] = row
    return list(result.values())


def local_feed(s, root):
    timeline = root / "branch/investor_agent/data/timeline"
    if s["kind"] == "research":
        doc = json.loads((timeline / "timeline_data_feed.json").read_text())
        return [
            observation(
                s["label"],
                f"{doc[s['group']][s['id']]} {s['unit']}",
                doc["as_of_date"],
                "timeline_data_feed.json",
                "저장소 연구 스냅샷 · 원문 재확인 필요",
                domains=["real_estate"],
            )
        ]
    if s["kind"] == "registry":
        doc = json.loads((timeline / "verified_sources.json").read_text())
        result = []
        for key, r in doc["registry"].items():
            roles = {"Equities": ["equities", "us_small_cap_high_beta"], "Real Estate": ["real_estate"]}.get(
                r.get("asset_class")
            )
            if not roles:
                continue
            symbol = key.partition("-")[2]
            result.append(
                observation(
                    r["asset_name"],
                    r["key_metric_verified"],
                    r["last_verified_date"],
                    r.get("source_citation") or "verified_sources.json",
                    "연구 기록의 기초지표 · 원문 재확인 필요",
                    [key, symbol, r["asset_name"]],
                    roles,
                )
            )
        return result
    if s["kind"] == "whale":
        series = {}
        with (root / "data/whale_daily_stats.csv").open() as f:
            for row in csv.DictReader(f):
                series.setdefault(row["coin_symbol"], {})[row["date"]] = num(row["net_flow_usd"])
        return [
            observation(
                sym,
                f"{points[max(points)]:,.2f} USD",
                max(points),
                "data/whale_daily_stats.csv",
                "고래 거래소 순유입 집계 · 지갑 라벨과 내부 이동 확인",
                [sym],
                ["crypto", "whale"],
            )
            for sym, points in series.items()
        ]
    raise ValueError("알 수 없는 로컬 원천")
