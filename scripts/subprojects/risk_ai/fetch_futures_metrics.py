#!/usr/bin/env python3
"""
Binance Futures 지표(펀딩비/OI/롱숏/변동성)를 수집하여 SQLite에 저장하는 스크립트입니다.
"""

import os
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"
load_dotenv(ROOT / "config" / ".env")

FUNDING_ENDPOINT = "https://fapi.binance.com/fapi/v1/fundingRate"
OI_ENDPOINT = "https://fapi.binance.com/futures/data/openInterestHist"
TICKER_ENDPOINT = "https://fapi.binance.com/fapi/v1/ticker/24hr"
KLINES_ENDPOINT = "https://fapi.binance.com/fapi/v1/klines"


def ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def upsert_metrics(rows):
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT OR REPLACE INTO binance_futures_metrics
        (date, symbol, avg_funding_rate, sum_open_interest, long_short_ratio, volatility_24h, target_volatility_24h)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    cur.close()
    conn.close()


def fetch_funding(symbol, days=30):
    end_ts = int(time.time() * 1000)
    start_ts = end_ts - days * 24 * 60 * 60 * 1000
    params = {"symbol": symbol, "startTime": start_ts, "endTime": end_ts, "limit": 1000}
    response = requests.get(FUNDING_ENDPOINT, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_oi(symbol, days=30):
    end_time = int(time.time() * 1000)
    start_time = end_time - days * 24 * 60 * 60 * 1000
    params = {
        "symbol": symbol,
        "period": "1h",
        "startTime": start_time,
        "endTime": end_time,
        "limit": 1000,
    }
    response = requests.get(OI_ENDPOINT, params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_volatility(symbol):
    """현재 시점의 24시간 변동성 조회 (실시간용)"""
    response = requests.get(TICKER_ENDPOINT, params={"symbol": symbol}, timeout=30)
    response.raise_for_status()
    data = response.json()
    high = float(data["highPrice"])
    low = float(data["lowPrice"])
    close = float(data["lastPrice"])
    if low == 0:
        return 0.0
    return (high - low) / close


def fetch_daily_klines(symbol, start_ts, end_ts):
    """Binance Futures Klines API를 사용하여 일봉 데이터 수집"""
    klines_by_date = {}
    current_start = start_ts
    
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)
    
    while current_start < end_ts:
        try:
            params = {
                "symbol": symbol,
                "interval": "1d",  # 일봉
                "startTime": current_start,
                "endTime": end_ts,
                "limit": 1000
            }
            response = session.get(KLINES_ENDPOINT, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
            
            for kline in data:
                # kline: [open_time, open, high, low, close, volume, close_time, ...]
                open_time = int(kline[0])
                dt = datetime.utcfromtimestamp(open_time / 1000).date()
                high = float(kline[2])
                low = float(kline[3])
                close = float(kline[4])
                
                # 변동성 계산: (high - low) / close
                if close > 0:
                    volatility = (high - low) / close
                else:
                    volatility = 0.0
                
                klines_by_date[dt] = volatility
            
            # 다음 페이지를 위해 마지막 kline의 close_time + 1을 시작 시간으로 설정
            if len(data) < 1000:
                break
            
            last_close_time = int(data[-1][6])  # close_time
            current_start = last_close_time + 1
            
            time.sleep(0.1)  # Rate limit 방지
            
        except Exception as e:
            print(f"⚠️ Klines fetch error: {e}")
            break
    
    return klines_by_date


def build_daily_metrics(symbol):
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)
    
    start_dt = datetime(2023, 1, 1)
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(time.time() * 1000)

    print(f"🔄 Fetching Futures Metrics for {symbol} (2023-01-01 ~ Now)...")

    # 1. Funding Rate (Limit 1000 per call)
    funding_by_date = defaultdict(list)
    curr_start = start_ts
    
    while curr_start < end_ts:
        try:
            params = {"symbol": symbol, "startTime": curr_start, "endTime": end_ts, "limit": 1000}
            resp = session.get(FUNDING_ENDPOINT, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            if not data:
                break
                
            last_funding_time = 0
            for record in data:
                ft = record["fundingTime"]
                last_funding_time = ft
                dt = datetime.utcfromtimestamp(ft / 1000).date()
                funding_by_date[dt].append(float(record["fundingRate"]))
            
            # Next page starts after the last record
            if last_funding_time > 0:
                curr_start = last_funding_time + 1
            else:
                break
                
            time.sleep(0.1)
            
        except Exception as e:
            print(f"⚠️ Funding rate fetch error: {e}")
            break

    # 2. Open Interest (Limit 500 per call, "1h" period approx 20 days per call)
    oi_by_date = defaultdict(list)
    
    # Binance OI History API is limited to last 30 days
    # 최근 30일 데이터라도 수집하여 활용
    oi_limit_ts = end_ts - (30 * 24 * 60 * 60 * 1000)
    if start_ts < oi_limit_ts:
        curr_start = oi_limit_ts
        print(f"ℹ️ Open Interest history is limited to last 30 days. Collecting from {datetime.utcfromtimestamp(curr_start/1000).date()}.")
    else:
        curr_start = start_ts
        print(f"ℹ️ Collecting Open Interest from {datetime.utcfromtimestamp(curr_start/1000).date()}.")
    
    while curr_start < end_ts:
        try:
            # Max window 30 days for safety
            req_end = min(curr_start + 30 * 24 * 60 * 60 * 1000, end_ts)
            
            params = {
                "symbol": symbol,
                "period": "1h",
                "startTime": int(curr_start),
                "endTime": int(req_end),
                "limit": 500, 
            }
            resp = session.get(OI_ENDPOINT, params=params, timeout=10)
            
            # If 400 error (likely invalid range), just break or skip
            if resp.status_code == 400:
                print(f"⚠️ OI fetch 400 Error (likely range limit): {resp.text}")
                break
                
            resp.raise_for_status()
            data = resp.json()
            
            if not data:
                curr_start += 30 * 24 * 60 * 60 * 1000 # Skip empty month
                continue
                
            last_ts = 0
            for entry in data:
                ts = int(entry["timestamp"])
                last_ts = ts
                dt = datetime.utcfromtimestamp(ts / 1000).date()
                val = float(entry.get("sumOpenInterestValue") or entry.get("sumOpenInterest", 0.0))
                oi_by_date[dt].append(val)
            
            # Move to next
            if last_ts > 0:
                curr_start = last_ts + 1
            else:
                curr_start = req_end + 1
            
            time.sleep(0.1)

        except Exception as e:
            print(f"⚠️ Open Interest fetch error: {e}")
            # If error, skip this window
            curr_start += 30 * 24 * 60 * 60 * 1000
            time.sleep(1)

    # 3. Daily Klines (Volatility)
    print("📊 Fetching daily klines for volatility calculation...")
    klines_by_date = fetch_daily_klines(symbol, start_ts, end_ts)
    print(f"   ✅ {len(klines_by_date)} days of volatility data collected")
    
    # 4. Aggregate & Save
    rows = []
    all_dates = sorted(list(set(funding_by_date.keys()) | set(oi_by_date.keys()) | set(klines_by_date.keys())))
    
    for date_ in all_dates:
        fr_list = funding_by_date.get(date_, [])
        avg_rate = sum(fr_list) / len(fr_list) if fr_list else 0.0
        
        oi_list = oi_by_date.get(date_, [])
        oi_value = sum(oi_list) / len(oi_list) if oi_list else 0.0
        
        long_short_ratio = 0.0 # API limitation for historical
        
        # Volatility from daily klines
        volatility = klines_by_date.get(date_, 0.0)
        # Target volatility: 다음날 변동성 (현재는 0.0으로 설정, 추후 계산 가능)
        target_volatility = 0.0
        
        rows.append(
            (
                date_.isoformat(),
                symbol,
                avg_rate,
                oi_value,
                long_short_ratio,
                volatility,
                target_volatility,
            )
        )

    upsert_metrics(rows)
    print(f"✅ {symbol}: Total {len(rows)} daily records saved.")


def main():
    ensure_db()
    symbols = os.getenv("BINANCE_FUTURES_SYMBOLS", "BTCUSDT,ETHUSDT").split(",")
    for symbol in symbols:
        build_daily_metrics(symbol.strip())


if __name__ == "__main__":
    main()

