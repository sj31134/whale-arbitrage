"""Public-only 6-axis market leader discovery engine. Never accepts portfolio inputs."""

import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import ipaddress
import json
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from agents import analyst_feeds as feeds, intelligence as intel
from . import live_valuation, price_history, store, strategy_registry

FILE = "market_discovery.json"
SNS_FILE = "discovery_sns_notes.json"
SNS_TONES = ("호재 확산", "과열·설거지 주의", "악재 우려", "중립 관찰")

# Curated structural moat universe supplemented dynamically by live top-momentum public listings.
KR_UNIVERSE = {
    "012450": ("한화에어로스페이스", "방산·우주", "유럽·중동 자주포·천무 수출 독점 및 항공엔진·우주 발사체 해자", "수출 수주 취소 또는 국방예산 감축"),
    "267260": ("HD현대일렉트릭", "AI 전력망", "북미 AI 데이터센터·노후 전력망 초고압 변압기(500kV+) 공급 병목", "북미 변압기 수주 단가 하락·관세 부과"),
    "000660": ("SK하이닉스", "AI 반도체", "HBM3E·HBM4 메모리 글로벌 선두 및 AI 가속기 필수 패키징 파트너", "HBM 단가 인하 또는 AI 서버 Capex 축소"),
    "005930": ("삼성전자", "AI 반도체", "글로벌 1위 메모리 생산능력과 100조 원대 순현금 기반 밸류업 안전마진", "첨단 D램/HBM 점유율 추가 하락"),
    "196170": ("알테오젠", "바이오 플랫폼", "정맥주사를 피하주사(SC)로 전환하는 인간 히알루로니다제 글로벌 빅파마 독점 라이선스", "주요 파트너 임상·품목허가 지연"),
    "034020": ("두산에너빌리티", "원전·가스터빈", "대형 원전 주기기·SMR 파운드리 및 데이터센터용 대형 가스터빈 공급 병목", "글로벌 원전 발주 지연·금리 급등"),
    "329180": ("HD현대중공업", "조선·방산MRO", "고부가 LNG선·암모니아선 선가 강세 및 미 해군 함정 MRO·특수선 수혜", "후판가 급등 또는 신규 선박 발주 급감"),
    "042660": ("한화오션", "조선·방산MRO", "미 해군 함정 유지보수(MRO) 수주 확대 및 잠수함·LNG선 건조 도크 선점", "특수선 인도 지연 또는 유상증자 희석"),
    "010120": ("LS일렉트릭", "AI 전력망", "AI 데이터센터 배전반·초고압 변압기 증설로 북미 빅테크향 직납 확대", "북미 데이터센터 증설 속도 둔화"),
    "207940": ("삼성바이오로직스", "바이오 CDMO", "미국 생물보안법 반사이익과 초격차 5공장 위탁생산(CDMO) 수주 잔고", "미국 생물보안법 무산 또는 바이오 시황 위축"),
    "005380": ("현대차", "모빌리티·로봇", "하이브리드 고수익성·인도 시장 성장·자사주 소각 및 로보틱스 옵션", "대미 자동차 고율 관세 현실화"),
    "000270": ("기아", "모빌리티·밸류업", "글로벌 완성차 최고 수준 영업이익률과 고배당·자사주 소각 주주환원", "북미 인센티브 급증 및 마진율 훼손"),
    "138040": ("메리츠금융지주", "금융·밸류업", "순이익 50% 이상 자사주 매입·소각 원칙을 지키는 자본배치 선두주", "부동산 PF 대손충당금 급증 또는 환원율 축소"),
    "105560": ("KB금융", "금융·밸류업", "보통주자본비율(CET1) 최상위 기반 분기 배당·자사주 소각 확대", "규제 개입에 따른 주주환원 축소"),
    "278470": ("에이피알", "글로벌 K뷰티", "홈 뷰티 디바이스 미국·일본·유럽 직판 고성장 및 높은 영업레버리지", "해외 마케팅비 급증으로 마진 하락"),
    "141080": ("리가켐바이오", "바이오 플랫폼", "글로벌 빅파마향 차세대 항체약물접합체(ADC) 링커·플랫폼 기술수출 파이프라인", "기술이전 파이프라인 임상 중단"),
}

US_UNIVERSE = {
    "NVDA": ("NVIDIA", "NASDAQ", "AI 반도체", "CUDA 생태계와 차세대 AI 가속기 독점 공급 게이트키퍼", "빅테크 자체 ASIC 전환 가속·수출통제 강화"),
    "TSM": ("TSMC", "NYSE", "AI 반도체", "전 세계 2nm·3nm 첨단 칩 및 CoWoS 패키징 90% 독점 파운드리", "대만 해협 군사적 긴장 고조"),
    "ASML": ("ASML", "NASDAQ", "AI 반도체", "첨단 반도체 미세공정에 필수인 EUV·High-NA 노광장비 전 세계 단독 독점", "대중국 반도체 장비 추가 수출통제"),
    "AVGO": ("Broadcom", "NASDAQ", "AI 반도체", "빅테크 맞춤형 AI ASIC 칩 및 데이터센터 초고속 이더넷 스위치 선두", "주요 클라우드 고객사 칩 내재화 이탈"),
    "PLTR": ("Palantir", "NASDAQ", "방산·AI OS", "서방 국방·정보기관 전장 AI 및 미국 기업용 온톨로지 AI 운영체제 확산", "정부 국방 계약 지연 또는 고밸류 멀티플 압축"),
    "CEG": ("Constellation Energy", "NASDAQ", "원전·AI 전력", "미국 최대 무탄소 원전 발전사로 빅테크 AI 데이터센터 장기 전력계약(PPA) 수혜", "원전 전력 직접계약 규제 불허"),
    "GE": ("GE Vernova", "NYSE", "AI 전력망", "글로벌 가스터빈·초고압 송배전 장비 수주잔고 급증 및 마진 턴어라운드", "풍력 부문 손실 확대 또는 전력망 투자 지연"),
    "PWR": ("Quanta Services", "NYSE", "AI 전력망", "북미 초고압 송전망·데이터센터 전력 인프라 설계·시공(EPC) 1위", "유틸리티 설비투자(Capex) 축소"),
    "LLY": ("Eli Lilly", "NYSE", "비만·바이오", "GLP-1 비만·당뇨·대사질환 치료제 글로벌 공급 독주 및 경구용 파이프라인", "경쟁사 임상 우위 또는 약가 인하 압박"),
    "MSFT": ("Microsoft", "NASDAQ", "클라우드·AI", "엔터프라이즈 클라우드(Azure)와 기업용 업무 AI 생태계 지배력", "AI 인프라 감가상각 대비 수익화 지연"),
    "META": ("Meta Platforms", "NASDAQ", "플랫폼·AI", "AI 추천 엔진 기반 광고 단가 상승 및 글로벌 30억 사용자 네트워크 해자", "AI 설비투자 과잉으로 잉여현금흐름 급감"),
    "GOOGL": ("Alphabet", "NASDAQ", "클라우드·AI", "글로벌 검색·유튜브 독점 현금흐름과 자체 TPU·클라우드 이익률 개선", "반독점 소송에 따른 핵심 사업 강제 분할"),
    "AMZN": ("Amazon", "NASDAQ", "클라우드·물류", "AWS 클라우드 AI 수요 반등 및 북미 물류 로봇 자동화에 따른 영업이익률 도약", "북미 소비 둔화 또는 클라우드 점유율 하락"),
    "COST": ("Costco", "NASDAQ", "필수소비 요새", "갱신율 90%+ 유료 멤버십 기반 인플레이션·경기방어 현금흐름 요새", "멤버십 갱신율 하락 또는 소비 급랭"),
}

EXPORT_THEMES = {"방산·우주", "AI 전력망", "AI 반도체", "바이오 플랫폼", "바이오 CDMO", "조선·방산MRO", "모빌리티·로봇", "모빌리티·밸류업", "글로벌 K뷰티"}
GEO_BENEFICIARIES = {"방산·우주", "방산·AI OS", "조선·방산MRO", "AI 전력망", "원전·가스터빈", "원전·AI 전력", "바이오 CDMO"}


def _default_get(url):
    req = Request(url, headers={"User-Agent": "whale-tracking/1.0 local public discovery"})
    with urlopen(req, timeout=7) as resp:
        return resp.read(2_500_000)


def _num(text):
    if text is None:
        return None
    cleaned = re.sub(r"[^0-9.\-+]", "", str(text))
    if not cleaned or cleaned in ("+", "-", "."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _clamp(val, lo, hi):
    return max(lo, min(hi, val))


def _naver_bars(code, get_bytes):
    url = (
        f"https://api.finance.naver.com/siseJson.nhn?symbol={code}"
        "&requestType=1&startTime=20260601&endTime=20291231&timeframe=day"
    )
    raw = get_bytes(url).decode("utf-8", errors="replace").strip()
    rows = ast.literal_eval(raw)
    out = []
    for r in rows[1:]:
        if len(r) >= 6 and str(r[0]).isdigit():
            d = str(r[0])
            day = f"{d[:4]}-{d[4:6]}-{d[6:8]}"
            o, h, l, c, v = float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])
            if c > 0:
                out.append(dict(day=day, open=o, high=h, low=l, close=c, volume=v))
    return out


def _yahoo_bars(symbol, get_bytes):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d"
    doc = json.loads(get_bytes(url).decode("utf-8", errors="replace"))["chart"]["result"][0]
    q = doc["indicators"]["quote"][0]
    out = []
    for ts, o, h, l, c, v in zip(
        doc.get("timestamp", ()),
        q.get("open", ()),
        q.get("high", ()),
        q.get("low", ()),
        q.get("close", ()),
        q.get("volume", ()),
    ):
        if c is not None and c > 0:
            day = datetime.fromtimestamp(ts, timezone.utc).date().isoformat()
            out.append(dict(day=day, open=float(o or c), high=float(h or c), low=float(l or c), close=float(c), volume=float(v or 0)))
    return out


def _bars_from_db(db, venue, symbol, currency):
    if db is None:
        return []
    rows, _ = price_history.series(db, (venue, symbol, currency))
    return [
        dict(day=r["day"], open=float(r["opening"]), high=float(r["high"]), low=float(r["low"]), close=float(r["closing"]), volume=0.0)
        for r in rows[-90:]
        if float(r["closing"]) > 0
    ]


def _day_change_pct(bars, cur_price):
    if not cur_price or cur_price <= 0 or not bars:
        return None
    last = bars[-1]["close"]
    if last <= 0:
        return None
    if abs(cur_price - last) / last > 1e-4:
        return round((cur_price / last - 1) * 100, 2)
    if len(bars) >= 2 and bars[-2]["close"] > 0:
        return round((last / bars[-2]["close"] - 1) * 100, 2)
    return 0.0


def _sns_badge_state(sns_note, sns_score, flow_score, rsi):
    if "과열" in sns_note or "FOMO" in sns_note or rsi > 78:
        return "overheat"
    if "악재" in sns_note:
        return "caution"
    if flow_score >= 17.5 and sns_score <= 6.5:
        return "stealth"
    if sns_score >= 7.5:
        return "positive"
    return "normal"


def _compute_tech(bars, cur_price, bench_ret20):
    fallback_px = float(cur_price or (bars[-1]["close"] if bars else 0.0))
    if len(bars) < 21:
        e1 = round(fallback_px, 2) if fallback_px > 0 else None
        e2 = round(fallback_px * 0.96, 2) if fallback_px > 0 else None
        sp = round(fallback_px * 0.92, 2) if fallback_px > 0 else None
        return dict(
            score=10, rs20=0.0, pct20=0.0, pct60=None, rsi=50.0, down_cap=65,
            ma20=e2, ma60=None, entry_1=e1, entry_2=e2, stop_price=sp,
            status="일봉 데이터 축적 중", entry_hint="분할 접근",
        )
    closes = [b["close"] for b in bars]
    if cur_price and cur_price > 0 and abs(cur_price - closes[-1]) / closes[-1] > 1e-5:
        closes = closes + [float(cur_price)]
    cur = closes[-1]
    ret20 = (cur / closes[-21] - 1) * 100
    rs20 = ret20 - bench_ret20
    ma20 = sum(closes[-20:]) / 20
    ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else None
    pct20 = (cur / ma20 - 1) * 100
    pct60 = (cur / ma60 - 1) * 100 if ma60 else None
    diffs = [b - a for a, b in zip(closes[-15:], closes[-14:])]
    up = sum(d for d in diffs if d > 0) / 14
    dn = sum(-d for d in diffs if d < 0) / 14
    rsi = 100.0 if dn == 0 else 100.0 - (100.0 / (1.0 + up / dn))
    down_cap = round(strategy_registry.target("downside-cap", closes[-25:]) * 100) if len(closes) >= 22 else 65

    # Score (0..25): relative strength vs index + trend alignment + healthy RSI
    pts = 10.0
    pts += _clamp(rs20 * 0.55, -6.0, 9.0)
    if cur >= ma20:
        pts += 3.0
    if ma60 and cur >= ma60:
        pts += 3.0
    if 45 <= rsi <= 70:
        pts += 2.0
    elif rsi > 78:
        pts -= 4.0  # short-term overheat penalty
    elif 30 <= rsi < 45 and pct20 > -10:
        pts += 1.0  # early bottom-turn candidate

    if rsi > 78:
        status = f"단기 과열 주의 (RSI {rsi:.0f} · 20일선 {pct20:+.1f}%)"
        entry_hint = f"추격 금지 · 20일선({ma20:,.0f}) 눌림 대기"
        entry_1, entry_2 = round(ma20, 2), round(ma20 * 0.96, 2)
    elif ma60 and cur >= ma20 and cur >= ma60:
        status = f"정배열 주도 추세 (시장대비 {rs20:+.1f}%p · RSI {rsi:.0f})"
        entry_hint = f"15:15 수급확인 종가 선발(40%) + 20일선({ma20:,.0f}) 눌림(60%)"
        entry_1, entry_2 = round(cur, 2), round(ma20, 2)
    elif cur >= ma20:
        status = f"단기 추세 돌파 (20일선 +{pct20:.1f}% · 시장대비 {rs20:+.1f}%p)"
        entry_hint = f"15:15 수급확인 종가 선발(40%) + 20일선({ma20:,.0f}) 지지(60%)"
        entry_1, entry_2 = round(cur, 2), round(ma20, 2)
    elif rsi <= 36:
        status = f"과매도 변곡점 대기 (RSI {rsi:.0f} · 시장대비 {rs20:+.1f}%p)"
        entry_hint = f"20일선({ma20:,.0f}) 회복 확인 후 진입"
        entry_1, entry_2 = round(cur, 2), round(ma20, 2)
    else:
        status = f"조정·바닥 다지기 (20일선 {pct20:+.1f}% · 시장대비 {rs20:+.1f}%p)"
        entry_hint = f"눌림 분할 또는 20일선({ma20:,.0f}) 돌파 확인"
        entry_1, entry_2 = round(cur, 2), round(ma20, 2)
    stop_ref = min(entry_1 * 0.92, (ma60 * 0.97) if (ma60 and cur >= ma60) else entry_1 * 0.92)

    return dict(
        score=round(_clamp(pts, 2.0, 25.0), 1),
        rs20=round(rs20, 1),
        pct20=round(pct20, 1),
        pct60=round(pct60, 1) if pct60 is not None else None,
        ma20=round(ma20, 2),
        ma60=round(ma60, 2) if ma60 else None,
        entry_1=entry_1,
        entry_2=entry_2,
        stop_price=round(stop_ref, 2),
        rsi=round(rsi, 1),
        down_cap=down_cap,
        status=status,
        entry_hint=entry_hint,
    )


def _macro_and_geo_context(package, fx_rate):
    cache = intel.private_json(package, intel.CACHE, {}) if package else {}
    un_items = cache.get("global_events/un_security", {}).get("items", [])
    gdacs_items = cache.get("global_events/gdacs", {}).get("items", [])
    fed_items = cache.get("policy/fed", {}).get("items", [])
    x_hit = cache.get("social/world", {})
    x_items = x_hit.get("items", [])
    dart_items = (intel.private_json(package, intel.CAPTURE_FILE, {}) if package else {}).get("dart_recent", {}).get("items", [])

    un_text = " ".join(i.get("title", "") for i in un_items[:15]).lower()
    conflict_active = bool(re.search(r"fighting|security|attack|missile|war|peacekeep|military|troop|drone|nuclear", un_text)) or bool(un_items)
    fx_high = fx_rate is not None and fx_rate >= 1320.0

    return dict(
        fx_rate=fx_rate,
        fx_high=fx_high,
        conflict_active=conflict_active,
        un_headline=un_items[0]["title"] if un_items else "유엔 평화·안보 원문 대기",
        un_url=un_items[0]["origin"] if un_items else "https://news.un.org/en/",
        gdacs_headline=gdacs_items[0]["title"] if gdacs_items else "재난 경보 특이사항 없음",
        fed_headline=fed_items[0]["title"] if fed_items else "연준 통화정책 발표 대기",
        fed_url=fed_items[0]["origin"] if fed_items else "https://www.federalreserve.gov/feeds/press_monetary.xml",
        x_status=x_hit.get("status", "미수집"),
        x_trends=[i["title"] for i in x_items[:8]],
        dart_companies={d.get("subjects", [""])[0]: d for d in dart_items if d.get("subjects")},
    )


def record_sns_note(package, fields):
    symbol = str(fields.get("symbol", "")).strip().upper()
    market = str(fields.get("market", "KR")).strip().upper()
    tone = str(fields.get("tone", "")).strip()
    summary = str(fields.get("summary", "")).strip()
    url = str(fields.get("url", "")).strip()
    if market not in ("KR", "US") or not re.fullmatch(r"[A-Z0-9.\-]{1,12}", symbol):
        raise ValueError("시장(KR/US)과 종목코드·티커 형식을 확인하세요.")
    if tone not in SNS_TONES or not 0 < len(summary) <= 300:
        raise ValueError("SNS 감성 분류와 요약(300자 이내)을 확인하세요.")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("검증할 게시물의 공개 HTTPS 원문 주소를 입력하세요.")
    host = parsed.hostname.rstrip(".").lower()
    try:
        private = not ipaddress.ip_address(host).is_global
    except ValueError:
        private = "." not in host or host.endswith((".localhost", ".local", ".internal"))
    if private:
        raise ValueError("공개 인터넷 주소를 입력하세요.")

    now = datetime.now(intel.KST).isoformat(timespec="seconds")
    entry = dict(market=market, symbol=symbol, tone=tone, summary=summary, url=url, recorded=now)

    def save(old):
        items = [r for r in old.get("items", []) if not (r["market"] == market and r["symbol"] == symbol and r["url"] == url)]
        items.insert(0, entry)
        return dict(updated=now, items=items[:60])

    intel.update_json(package, SNS_FILE, {}, save)
    return entry


def sns_notes(package):
    if package is None:
        return []
    return intel.private_json(package, SNS_FILE, {}).get("items", [])


def refresh(package, *, fetcher=None, now=None):
    """Collect and score public KR/US market leaders across 6 variables. Zero portfolio input."""
    get_bytes = fetcher or _default_get
    stamp_dt = now or datetime.now(intel.KST)
    stamp = stamp_dt.astimezone(intel.KST).isoformat(timespec="seconds")
    day_key = stamp_dt.astimezone(intel.KST).date().isoformat()

    qb = live_valuation.read(package)
    fx_rate = float(qb.fx["price"]) if qb.fx else 1340.0
    ctx = _macro_and_geo_context(package, fx_rate)
    manual_sns = {}
    for note in sns_notes(package):
        manual_sns.setdefault((note["market"], note["symbol"]), []).append(note)

    # 1) Fetch public global social buzz (ApeWisdom public stock community mentions)
    apewisdom = {}
    sns_top = []
    try:
        aw_doc = json.loads(get_bytes("https://apewisdom.io/api/v1.0/filter/all-stocks/page/1").decode("utf-8", errors="replace"))
        for r in aw_doc.get("results", [])[:60]:
            tk = str(r.get("ticker", "")).upper()
            if tk:
                apewisdom[tk] = r
                if len(sns_top) < 6:
                    sns_top.append(dict(symbol=tk, name=r.get("name", tk), mentions=int(r.get("mentions") or 0), upvotes=int(r.get("upvotes") or 0)))
    except Exception:
        pass

    # 2) Expand candidate pool dynamically with today's live top KRX & US ordinary movers
    kr_pool = dict(KR_UNIVERSE)
    for ep in (
        "https://m.stock.naver.com/api/stocks/up/KOSPI?page=1&pageSize=15",
        "https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page=1&pageSize=20",
        "https://m.stock.naver.com/api/stocks/marketValue/KOSDAQ?page=1&pageSize=12",
    ):
        try:
            rows = json.loads(get_bytes(ep).decode("utf-8", errors="replace")).get("stocks", [])
            for r in rows:
                code = str(r.get("itemCode", ""))
                name = str(r.get("stockName", "")).strip()
                if (
                    re.fullmatch(r"\d{6}", code)
                    and code not in kr_pool
                    and r.get("stockEndType") == "stock"
                    and not any(w in name for w in ("스팩", "리츠", "우B", "1우", "2우", "3우", "인버스", "레버리지"))
                    and len(kr_pool) < 24
                ):
                    kr_pool[code] = (name, "시장 수급 급부상", "당일 거래대금·상승률 상위 포착 상장주 (실적·공시 원문 교차검증 필요)", "단기 테마 수급 이탈 또는 20일선 붕괴")
        except Exception:
            continue

    us_pool = dict(US_UNIVERSE)
    for tk, r in list(apewisdom.items())[:8]:
        if tk not in us_pool and re.fullmatch(r"[A-Z]{2,5}", tk) and tk not in {"SPY", "QQQ", "IWM", "TQQQ", "SQQQ", "SOXL"} and len(us_pool) < 18:
            q_hit = next((q for q in qb.index.get(tk.lower(), []) if q["venue"] in ("NASDAQ", "NYSE", "AMEX")), None)
            if q_hit:
                us_pool[tk] = (q_hit["name"] or r.get("name") or tk, q_hit["venue"], "SNS 관심 급증", "글로벌 커뮤니티 언급 상위 포착 종목 (실적·밸류 대조 필요)", "SNS 과열 식으며 거래량 급감 시")

    # 3) Benchmark 20D return from local DB or fallback
    with live_valuation.connection(package) as db:
        has_bars = bool(db and db.execute("SELECT 1 FROM sqlite_master WHERE name='price_bar'").fetchone())
        kr_bench_bars = _bars_from_db(db if has_bars else None, "KRX", "069500", "KRW")
        us_bench_bars = _bars_from_db(db if has_bars else None, "AMEX", "SPY", "USD")
        db_bars_kr = {code: _bars_from_db(db if has_bars else None, "KRX", code, "KRW") for code in kr_pool}
        db_bars_us = {sym: _bars_from_db(db if has_bars else None, info[1], sym, "USD") for sym, info in us_pool.items()}

    if len(kr_bench_bars) < 21:
        try:
            kr_bench_bars = _naver_bars("069500", get_bytes)
        except Exception:
            kr_bench_bars = []
    if len(us_bench_bars) < 21:
        try:
            us_bench_bars = _yahoo_bars("SPY", get_bytes)
        except Exception:
            us_bench_bars = []

    kr_bench_ret20 = ((kr_bench_bars[-1]["close"] / kr_bench_bars[-21]["close"] - 1) * 100) if len(kr_bench_bars) >= 21 else 0.0
    us_bench_ret20 = ((us_bench_bars[-1]["close"] / us_bench_bars[-21]["close"] - 1) * 100) if len(us_bench_bars) >= 21 else 0.0

    def score_kr(item):
        code, (name, theme, moat, invalidate) = item
        q = qb.match("kis", code, "KRW", (f"stock:KR:{code}",))
        cur_price = float(q["price"]) if q else None
        integ = {}
        try:
            integ = json.loads(get_bytes(f"https://m.stock.naver.com/api/stock/{code}/integration").decode("utf-8", errors="replace"))
        except Exception:
            pass
        infos = {x.get("code"): x.get("value") for x in integ.get("totalInfos", []) if isinstance(x, dict)}
        if cur_price is None:
            try:
                b_doc = json.loads(get_bytes(f"https://m.stock.naver.com/api/stock/{code}/basic").decode("utf-8", errors="replace"))
                cur_price = _num(b_doc.get("closePrice"))
            except Exception:
                cur_price = _num(infos.get("lastClosePrice"))
        bars = db_bars_kr.get(code) or []
        if len(bars) < 25:
            try:
                bars = _naver_bars(code, get_bytes)
            except Exception:
                bars = []
        if cur_price is None and bars:
            cur_price = bars[-1]["close"]
        if not cur_price or cur_price <= 0:
            return None

        # Axis 1: Supply/Demand (0..25)
        trends = integ.get("dealTrendInfos", [])[:5]
        f_days = sum((_num(t.get("foreignerPureBuyQuant")) or 0) > 0 for t in trends)
        i_days = sum((_num(t.get("organPureBuyQuant")) or 0) > 0 for t in trends)
        f_net = sum(_num(t.get("foreignerPureBuyQuant")) or 0 for t in trends)
        i_net = sum(_num(t.get("organPureBuyQuant")) or 0 for t in trends)
        flow_pts = 7.0 + f_days * 1.8 + i_days * 1.8
        if f_net > 0 and i_net > 0:
            flow_pts += 4.0  # dual net buying bonus
        elif f_net > 0 or i_net > 0:
            flow_pts += 1.5
        trade_val = infos.get("accumulatedTradingValue", "")
        if "조" in str(trade_val) or ((_num(trade_val) or 0) >= 500):
            flow_pts += 2.0
        flow_score = round(_clamp(flow_pts, 3.0, 25.0), 1)
        flow_note = (
            f"최근 5거래일 외인 {f_days}일({'순매수' if f_net > 0 else '순매도'}) · "
            f"기관 {i_days}일({'순매수' if i_net > 0 else '순매도'})"
            + (f" · 거래대금 {trade_val}" if trade_val else "")
        )

        # Axis 2: Technicals & Relative Strength (0..25)
        tech = _compute_tech(bars, cur_price, kr_bench_ret20)

        # Axis 3: Catalyst / Intrinsic Value / Filings (0..20)
        cons = integ.get("consensusInfo") or {}
        target_px = _num(cons.get("priceTargetMean"))
        upside_pct = ((target_px / cur_price - 1) * 100) if (target_px and cur_price) else None
        val_pts = 11.0 if code in KR_UNIVERSE else 7.0
        if upside_pct is not None:
            val_pts += _clamp(upside_pct * 0.16, -3.0, 7.0)
        dart_hit = ctx["dart_companies"].get(name)
        if dart_hit:
            val_pts += 2.0
        value_score = round(_clamp(val_pts, 4.0, 20.0), 1)
        value_note = (
            (f"컨센서스 목표가 {target_px:,.0f}원(상승여력 {upside_pct:+.1f}%) · " if upside_pct is not None else "")
            + (f"당일 DART 공시({dart_hit['title']}) · " if dart_hit else "")
            + moat
        )

        # Axis 4: X / SNS & Attention Sentiment (0..10)
        notes = manual_sns.get(("KR", code), [])
        sns_pts = 5.5
        sns_note = "X 공식 토큰 미연결 · 국내 거래대금 관심 정상"
        if "조" in str(trade_val) or ((_num(trade_val) or 0) >= 1500):
            sns_pts += 2.0
            sns_note = f"시장 거래대금 상위 집중({trade_val}) · 기관·개인 동시 주목"
        if any(name.lower() in t.lower() for t in ctx["x_trends"]):
            sns_pts += 2.0
            sns_note = "X 글로벌 실시간 트렌드 언급 확인"
        if notes:
            latest_n = notes[0]
            if latest_n["tone"] == "호재 확산":
                sns_pts += 2.5
            elif latest_n["tone"] in ("과열·설거지 주의", "악재 우려"):
                sns_pts -= 3.0
            sns_note = f"사용자 X·SNS 검증 등록({latest_n['tone']}): {latest_n['summary']}"
        elif tech["rsi"] > 78:
            sns_pts -= 2.0
            sns_note = "단기 급등에 따른 개인 추격 과열 주의"
        sns_score = round(_clamp(sns_pts, 1.0, 10.0), 1)

        # Axis 5: Global Macro Flow (0..10)
        macro_pts = 6.0
        if theme in EXPORT_THEMES and ctx["fx_high"]:
            macro_pts += 2.5
            macro_note = f"원·달러 {ctx['fx_rate']:,.1f}원 고환율 수출 마진 우호 · 글로벌 설비투자 수혜"
        elif "금융" in theme:
            macro_pts += 2.0
            macro_note = "금리 고점권 예대마진 방어 및 코리아 밸류업 자본환원 흐름"
        else:
            macro_note = f"원·달러 {ctx['fx_rate']:,.1f}원 및 연준 통화정책 변화 점검"
        macro_score = round(_clamp(macro_pts, 3.0, 10.0), 1)

        # Axis 6: Geopolitical & Supply-Chain (0..10)
        geo_pts = 5.5
        if theme in GEO_BENEFICIARIES and ctx["conflict_active"]:
            geo_pts += 3.5
            geo_note = f"지정학 안보·공급망 재편 직접 수혜 ({theme})"
        elif theme == "AI 반도체":
            geo_pts += 2.0
            geo_note = "글로벌 소버린 AI 인프라 경쟁 필수재 (단, 미·중 수출통제 변수 상존)"
        else:
            geo_note = "지정학 직접 분쟁 노출 낮음 · 원자재·환율 간접 경로 점검"
        geo_score = round(_clamp(geo_pts, 3.0, 10.0), 1)

        total = round(flow_score + tech["score"] + value_score + sns_score + macro_score + geo_score, 1)
        return dict(
            market="KR",
            venue="KRX",
            symbol=code,
            name=name,
            currency="KRW",
            theme=theme,
            price=cur_price,
            change_pct=_day_change_pct(bars, cur_price),
            target_price=target_px,
            upside_pct=round(upside_pct, 1) if upside_pct is not None else None,
            total=total,
            sns_state=_sns_badge_state(sns_note, sns_score, flow_score, tech["rsi"]),
            scores=dict(flow=flow_score, tech=tech["score"], value=value_score, sns=sns_score, macro=macro_score, geo=geo_score),
            tech=tech,
            flow_note=flow_note,
            value_note=value_note,
            sns_note=sns_note,
            macro_note=macro_note,
            geo_note=geo_note,
            invalidate=invalidate,
            sources=[
                dict(label="네이버 통합수급·컨센서스", url=f"https://m.stock.naver.com/domestic/stock/{code}/total"),
                dict(label="유엔 안보·지정학 피드", url=ctx["un_url"]),
            ],
        )

    def score_us(item):
        sym, (name, venue, theme, moat, invalidate) = item
        q = qb.match("kis", sym, "USD", (f"stock:US:{sym}",))
        cur_price = float(q["price"]) if q else None
        bars = db_bars_us.get(sym) or []
        if len(bars) < 25:
            try:
                bars = _yahoo_bars(sym, get_bytes)
            except Exception:
                bars = []
        if cur_price is None and bars:
            cur_price = bars[-1]["close"]
        if not cur_price or cur_price <= 0:
            return None

        # Axis 1: US Volume & Up/Down Institutional Accumulation (0..25)
        vols = [b.get("volume", 0.0) for b in bars[-21:]]
        up_vol = sum(b.get("volume", 0.0) for a, b in zip(bars[-21:-1], bars[-20:]) if b["close"] >= a["close"])
        dn_vol = sum(b.get("volume", 0.0) for a, b in zip(bars[-21:-1], bars[-20:]) if b["close"] < a["close"])
        ud_ratio = (up_vol / dn_vol) if dn_vol > 0 else 1.15
        flow_pts = 12.0 + _clamp((ud_ratio - 1.0) * 9.0, -5.0, 10.0)
        if sym in US_UNIVERSE:
            flow_pts += 2.0
        flow_score = round(_clamp(flow_pts, 4.0, 25.0), 1)
        flow_note = f"20일 상승일/하락일 거래량 비율 {ud_ratio:.2f}배 ({'기관형 매집 우위' if ud_ratio >= 1.05 else '차익 매물 소화 중'})"

        # Axis 2: Technicals (0..25)
        tech = _compute_tech(bars, cur_price, us_bench_ret20)

        # Axis 3: Moat & Intrinsic Value (0..20)
        upside_pct = 28.0 if sym in US_UNIVERSE else 15.0
        target_px = round(cur_price * (1 + upside_pct / 100), 2)
        value_score = 17.5 if sym in US_UNIVERSE else 12.0
        value_note = f"글로벌 독점 해자 · 기준 시나리오 목표가 ${target_px:,.2f}(+{upside_pct:.0f}%) · {moat}"

        # Axis 4: X / SNS Buzz via ApeWisdom + X Trends + Manual Notes (0..10)
        aw = apewisdom.get(sym)
        notes = manual_sns.get(("US", sym), [])
        sns_pts = 5.5
        if aw:
            mentions = int(aw.get("mentions") or 0)
            prev_m = max(1, int(aw.get("mentions_24h_ago") or mentions or 1))
            growth = mentions / prev_m
            if 0.8 <= growth <= 2.5:
                sns_pts += 2.5
                sns_note = f"글로벌 커뮤니티 언급 #{aw.get('rank')}위({mentions}건, 추천 {aw.get('upvotes')}회) · 건전한 관심 유지"
            elif growth > 2.5 and tech["rsi"] > 75:
                sns_pts -= 2.0
                sns_note = f"SNS 언급 24시간 {growth:.1f}배 폭증 + 차트 과열 · 단기 FOMO 추격 주의"
            else:
                sns_pts += 1.5
                sns_note = f"글로벌 커뮤니티 언급 #{aw.get('rank')}위({mentions}건)"
        else:
            sns_note = "SNS 루머 과열 없음 · 기관 중심 조용한 추세"
        if any(sym.lower() == t.lstrip("$#").lower() for t in ctx["x_trends"]):
            sns_pts += 2.0
            sns_note += " · X 실시간 트렌드 포착"
        if notes:
            latest_n = notes[0]
            sns_pts += 2.0 if latest_n["tone"] == "호재 확산" else (-3.0 if latest_n["tone"] in ("과열·설거지 주의", "악재 우려") else 0.0)
            sns_note = f"사용자 X·SNS 검증({latest_n['tone']}): {latest_n['summary']}"
        sns_score = round(_clamp(sns_pts, 1.0, 10.0), 1)

        # Axis 5: Global Macro (0..10)
        macro_score = 8.5 if theme in {"AI 반도체", "AI 전력망", "원전·AI 전력", "클라우드·AI"} else 7.5
        macro_note = "빅테크 AI 데이터센터 설비투자(Capex) 및 연준 금리 경로 연동"

        # Axis 6: Geopolitics (0..10)
        if sym == "TSM":
            geo_score, geo_note = 5.5, "첨단 칩 독점이나 대만 해협 지정학 리스크 상시 점검 필요"
        elif theme in GEO_BENEFICIARIES:
            geo_score, geo_note = 9.0, f"글로벌 국방·에너지 안보 지출 확대 직접 수혜 ({theme})"
        else:
            geo_score, geo_note = 7.0, "글로벌 관세·공급망 규제 대비 가격 결정력 보유"

        total = round(flow_score + tech["score"] + value_score + sns_score + macro_score + geo_score, 1)
        return dict(
            market="US",
            venue=venue,
            symbol=sym,
            name=name,
            currency="USD",
            theme=theme,
            price=cur_price,
            change_pct=_day_change_pct(bars, cur_price),
            target_price=target_px,
            upside_pct=upside_pct,
            total=total,
            sns_state=_sns_badge_state(sns_note, sns_score, flow_score, tech["rsi"]),
            scores=dict(flow=flow_score, tech=tech["score"], value=value_score, sns=sns_score, macro=macro_score, geo=geo_score),
            tech=tech,
            flow_note=flow_note,
            value_note=value_note,
            sns_note=sns_note,
            macro_note=macro_note,
            geo_note=geo_note,
            invalidate=invalidate,
            sources=[
                dict(label="공개 가격·거래량 차트", url=f"https://stockanalysis.com/stocks/{sym.lower()}/"),
                dict(label="글로벌 SNS 언급 집계(ApeWisdom)", url="https://apewisdom.io/"),
                dict(label="미 연준·유엔 글로벌 피드", url=ctx["fed_url"]),
            ],
        )

    with ThreadPoolExecutor(max_workers=6) as pool:
        kr_items = [r for r in pool.map(score_kr, kr_pool.items()) if r is not None]
        us_items = [r for r in pool.map(score_us, us_pool.items()) if r is not None]

    candidates = sorted(kr_items + us_items, key=lambda r: (-r["total"], -r["scores"]["flow"], r["symbol"]))

    # Update daily history for streak & NEW leader detection
    def merge_history(old):
        hist = dict(old.get("history", {}))
        # Find most recent prior day
        prior_days = sorted(d for d in hist if d < day_key)
        prev_map = hist[prior_days[-1]] if prior_days else {}
        today_summary = {}
        for item in candidates:
            key = f"{item['market']}:{item['symbol']}"
            prev = prev_map.get(key)
            streak = (prev.get("streak", 1) + 1) if prev else 1
            delta = round(item["total"] - prev["total"], 1) if prev else None
            item["is_new"] = prev is None and bool(prior_days)
            item["streak"] = streak
            item["score_delta"] = delta
            today_summary[key] = dict(total=item["total"], streak=streak, name=item["name"], theme=item["theme"])
        # Keep last 30 days
        hist[day_key] = today_summary
        for stale_d in sorted(hist)[:-30]:
            del hist[stale_d]
        return dict(
            updated=stamp,
            day=day_key,
            context=dict(
                fx_rate=ctx["fx_rate"],
                un_headline=ctx["un_headline"],
                un_url=ctx["un_url"],
                gdacs_headline=ctx["gdacs_headline"],
                fed_headline=ctx["fed_headline"],
                fed_url=ctx["fed_url"],
                x_status=ctx["x_status"],
                sns_top=sns_top,
                kr_bench_ret20=round(kr_bench_ret20, 2),
                us_bench_ret20=round(us_bench_ret20, 2),
            ),
            candidates=candidates,
            history=hist,
        )

    if package is not None:
        intel.update_json(package, FILE, {}, merge_history)
        return intel.private_json(package, FILE, {})
    return merge_history({})


def read(package):
    if package is None:
        return {}
    return intel.private_json(package, FILE, {})
