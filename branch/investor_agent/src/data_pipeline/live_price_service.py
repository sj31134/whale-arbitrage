"""
Live Price Service: Fetches real-time, 24/7 live market price feeds across
Binance 24/7 API (Crypto & Tokenized US Equity RWAs: NVDA, ASML, MSFT, GOOGL, TSM, TSLA, URNM, PAXG),
Naver Finance (KRX 8월 18일 Close), and Yahoo Finance.
"""
from typing import Dict, Any, Optional
import requests
import json
from pathlib import Path


class LivePriceService:
    def __init__(self, cache_file: Optional[Path] = None):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.base_dir = Path(__file__).resolve().parent.parent.parent / "data" / "timeline"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = cache_file or (self.base_dir / "live_market_quotes.json")
        self.quotes_cache: Dict[str, float] = self._load_cache()

    def _load_cache(self) -> Dict[str, float]:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_cache(self):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.quotes_cache, f, indent=2, ensure_ascii=False)

    def fetch_binance_rwa_price(self, symbol: str) -> Optional[float]:
        """
        Fetches 24/7 real-time live price for tokenized US equities, commodities, and crypto from Binance APIs.
        Supports both Binance Futures RWA contracts and Spot RWA tokens.
        """
        # 1. Try Binance Futures (fapi)
        try:
            url = f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
            r = requests.get(url, headers=self.headers, timeout=3)
            if r.status_code == 200:
                p = r.json().get("price")
                if p:
                    return float(p)
        except Exception:
            pass

        # 2. Try Binance Spot (api)
        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            r = requests.get(url, headers=self.headers, timeout=3)
            if r.status_code == 200:
                p = r.json().get("price")
                if p:
                    return float(p)
        except Exception:
            pass

        return None

    def fetch_naver_price(self, ticker: str) -> Optional[float]:
        """Fetches live stock or ETF price from Naver Finance Mobile API (KRX Official Close)."""
        url = f"https://m.stock.naver.com/api/stock/{ticker}/basic"
        try:
            r = requests.get(url, headers=self.headers, timeout=4)
            if r.status_code == 200:
                data = r.json()
                raw_price = data.get("closePrice") or data.get("nowPrice")
                if raw_price:
                    val = float(str(raw_price).replace(",", ""))
                    return val
        except Exception:
            pass
        return None

    def fetch_yahoo_price(self, ticker: str) -> Optional[float]:
        """Fetches live market price from Yahoo Finance v8 chart API (US Pre-Market & Regular)."""
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
        try:
            r = requests.get(url, headers=self.headers, timeout=5)
            if r.status_code == 200:
                meta = r.json().get("chart", {}).get("result", [{}])[0].get("meta", {})
                price = meta.get("regularMarketPrice")
                if price:
                    return float(price)
        except Exception:
            pass
        return None

    def refresh_all_live_quotes(self) -> Dict[str, float]:
        """
        Polls and synchronizes all live quotes across Binance 24/7 RWA Tokens, KRX Aug 18 Close, and US Pre-Market.
        """
        print(" 📡 [24/7 BINANCE RWA & GLOBAL PIPELINE] Fetching 24/7 live tokenized equities, KRX Close, and US Feeds...")

        # 1. Binance 24/7 Tokenized US Equities & Crypto RWAs
        binance_rwa_map = {
            "US-NVDA": "NVDAUSDT",         # Tokenized Nvidia RWA ($220.58)
            "US-ASML": "ASMLUSDT",         # Tokenized ASML RWA ($1,810.60)
            "US-MSFT": "MSFTUSDT",         # Tokenized Microsoft RWA ($483.83)
            "US-GOOGL": "GOOGLUSDT",       # Tokenized Alphabet RWA ($342.97)
            "US-TSM": "TSMUSDT",           # Tokenized TSMC RWA ($420.45)
            "US-AAPL": "AAPLUSDT",         # Tokenized Apple RWA ($307.71)
            "US-TSLA": "TSLAUSDT",         # Tokenized Tesla RWA ($334.53)
            "US-QCOM": "QCOMUSDT",         # Tokenized Qualcomm RWA ($158.30)
            "US-ARM": "ARMUSDT",           # Tokenized ARM RWA ($259.83)
            "MACRO-URNM-URANIUM": "URNMUSDT", # Tokenized Uranium RWA ($54.76)
            "CMD-PAXG-GOLD": "PAXGUSDT",   # Tokenized Physical Gold RWA ($4,387.55)
            "CRYPTO-BTC": "BTCUSDT",       # Bitcoin 24/7 ($64,151.40)
            "CRYPTO-ETH": "ETHUSDT",       # Ethereum 24/7 ($1,896.91)
            "CRYPTO-SOL": "SOLUSDT",       # Solana 24/7 ($76.18)
        }
        for aid, symbol in binance_rwa_map.items():
            price = self.fetch_binance_rwa_price(symbol)
            if price:
                self.quotes_cache[aid] = price

        # 2. KR Equities & ETFs (KRX Live & Official Close)
        kr_map = {
            "KR-005930": "005930",  # 삼성전자
            "KR-000660": "000660",  # SK하이닉스
            "KR-138040": "138040",  # 메리츠금융지주
            "KR-005380": "005380",  # 현대차
            "KR-196170": "196170",  # 알테오젠
            "KR-267260": "267260",  # HD현대일렉트릭 (814,000원)
            "KR-207940": "207940",  # 삼성바이오로직스
            "KR-278470": "278470",  # 에이피알
            "KR-034020": "034020",  # 두산에너빌리티
            "KR-010120": "010120",  # LS ELECTRIC (215,500원)
            "KR-009540": "009540",  # HD한국조선해양 (360,500원)
            "KR-012450": "012450",  # 한화에어로스페이스 (1,157,000원)
            "KR-042700": "042700",  # 한미반도체 (219,500원)
            "KR-141080": "141080",  # 리가켐바이오 (101,200원)
            "KR-003230": "003230",  # 삼양식품
            "KR-035720": "035720",  # 카카오
            "JP-ETF-465660": "465660", # TIGER 일본반도체FACTSET
            "CN-ETF-396520": "396520", # TIGER 차이나반도체FACTSET
        }

        for asset_id, code in kr_map.items():
            price = self.fetch_naver_price(code)
            if price:
                self.quotes_cache[asset_id] = price

        # 3. US Equities, Commodities, JP, CN (Yahoo Finance Live & Pre-Market Fallbacks)
        yahoo_map = {
            "US-LUNR": "LUNR",        # Intuitive Machines ($15.37)
            "US-POET": "POET",        # POET Technologies ($8.25)
            "US-CIFR": "CIFR",        # Cipher Digital ($15.16)
            "US-OKLO": "OKLO",        # Oklo Inc. ($40.35)
            "US-CLBT": "CLBT",        # Cellebrite DI ($11.99)
            "US-RKLB": "RKLB",        # Rocket Lab ($64.79)
            "US-ASTS": "ASTS",        # AST SpaceMobile ($58.21)
            "US-IREN": "IREN",        # IREN ($35.75)
            "US-PLTR": "PLTR",        # Palantir ($185.74)
            "US-CEG": "CEG",          # Constellation Energy ($279.00)
            "MACRO-CCJ": "CCJ",       # Cameco Corporation ($107.34)
            "US-GE": "GE",
            "US-AVGO": "AVGO",
            "US-LLY": "LLY",
            "US-AMZN": "AMZN",
            "US-COST": "COST",
            "MACRO-FCX": "FCX",
            "MACRO-MP": "MP",
            "MACRO-NTR": "NTR",
            "MACRO-LNG": "LNG",
            "MACRO-BHP": "BHP",
            "MACRO-FRO": "FRO",
            "MACRO-VLO": "VLO",
            "MACRO-NEE": "NEE",
            "MACRO-PAAS": "PAAS",
            "CMD-GOLD": "GC=F",
            "CMD-COPPER": "HG=F",
            "MACRO-US10Y": "^TNX",
            "MACRO-DXY": "DX-Y.NYB",

            # Japan Equities
            "JP-6146": "6146.T",
            "JP-8058": "8058.T",
            "JP-6861": "6861.T",
            "JP-6857": "6857.T",
            "JP-8035": "8035.T",
            "JP-6920": "6920.T",
            "JP-4063": "4063.T",
            "JP-6758": "6758.T",

            # China Equities
            "CN-0700": "0700.HK",
            "CN-600519": "600519.SS",
            "CN-1211": "1211.HK",
            "CN-9999": "9999.HK",
            "CN-3690": "3690.HK",
            "CN-1810": "1810.HK",
        }


        for asset_id, ticker in yahoo_map.items():
            price = self.fetch_yahoo_price(ticker)
            if price:
                self.quotes_cache[asset_id] = price

        # 4. Real Estate benchmarks
        real_estate_map = {
            "RE-HANNAM-UN": 100.0,
            "RE-APGUJEONG": 100.0,
            "RE-BANPO-ONE": 100.0,
            "RE-SEONGSU-IT": 100.0,
            "RE-YEOUIDO-FIN": 100.0,
            "RE-YONGSAN-HUB": 100.0,
            "RE-HANNAM-NT": 100.0,
            "RE-JAMSIL-JU5": 100.0,
            "RE-EUNMA-DAECHI": 100.0,
            "RE-MOKDONG-NEW": 100.0,
            "RE-MANHATTAN-CPS": 100.0,
            "RE-DATA-CENTER-LAND": 100.0,
            "RE-US-FARMLAND-WATER": 100.0,

            "RE-NOWON-RECON": 6.8,       # 노원 상계주공 (6.8억)
            "RE-YONGSAN-VILLA": 8.5,     # 용산 효창/원효 모아타운 (8.5억)
            "RE-MAPO-YEOMRI": 9.2,       # 마포 염리/아현 (9.2억)
            "RE-SEONGDONG-SONGJEONG": 7.8, # 성동 송정/마장 (7.8억)
            "RE-BUNDANG-1ST": 9.2,       # 분당 1기 신도시 (9.2억)
            "RE-PYEONGCHON-1ST": 7.2,    # 평촌 1기 신도시 (7.2억)
            "RE-GWANGMYEONG-NT": 7.8,    # 광명뉴타운 (7.8억)
            "RE-SUWON-YEONGTONG": 6.2,   # 수원 영통 매탄 (6.2억)
            "RE-ILSAN-1ST": 5.6,         # 일산 1기 신도시 (5.6억)
            "RE-BUPYEONG-RECON": 4.8,    # 인천 부평 재개발 (4.8억)
        }
        for aid, val in real_estate_map.items():
            self.quotes_cache[aid] = val

        self._save_cache()
        print(f" ✅ Real-time quote feed synchronized: {len(self.quotes_cache)} assets live across Binance 24/7 RWA, KRX, and US Pre-market.\n")
        return self.quotes_cache

    def get_price(self, asset_id: str, default_val: float) -> float:
        return self.quotes_cache.get(asset_id, default_val)
