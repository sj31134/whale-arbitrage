#!/usr/bin/env python3
"""
Binance/Bybit Futures 지표(펀딩비/OI/롱숏/변동성/Taker비율)를 수집하여 SQLite에 저장하는 스크립트입니다.
확장된 버전: 롱숏비율, Taker비율, Bybit 펀딩비 추가
"""

import os
import sqlite3
import time
import argparse
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"
load_dotenv(ROOT / "config" / ".env")

# Binance Futures API Endpoints
FUNDING_ENDPOINT = "https://fapi.binance.com/fapi/v1/fundingRate"
OI_ENDPOINT = "https://fapi.binance.com/futures/data/openInterestHist"
TICKER_ENDPOINT = "https://fapi.binance.com/fapi/v1/ticker/24hr"
KLINES_ENDPOINT = "https://fapi.binance.com/fapi/v1/klines"

# 추가 Binance Futures API Endpoints (롱숏비율, Taker비율)
LONG_SHORT_RATIO_ENDPOINT = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
TAKER_RATIO_ENDPOINT = "https://fapi.binance.com/futures/data/takerlongshortRatio"
TOP_TRADER_POSITION_ENDPOINT = "https://fapi.binance.com/futures/data/topLongShortPositionRatio"

# Bybit API Endpoints
BYBIT_FUNDING_ENDPOINT = "https://api.bybit.com/v5/market/funding/history"
BYBIT_OI_ENDPOINT = "https://api.bybit.com/v5/market/open-interest"


def ensure_db():
    """DB 디렉토리 생성 및 확장 테이블 스키마 확인"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 확장 테이블 생성: futures_extended_metrics (롱숏비율, Taker비율 등)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS futures_extended_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            symbol VARCHAR(20) NOT NULL,
            long_short_ratio DECIMAL(10, 6),
            long_account_pct DECIMAL(10, 6),
            short_account_pct DECIMAL(10, 6),
            taker_buy_sell_ratio DECIMAL(10, 6),
            taker_buy_vol DECIMAL(30, 8),
            taker_sell_vol DECIMAL(30, 8),
            top_trader_long_short_ratio DECIMAL(10, 6),
            bybit_funding_rate DECIMAL(20, 10),
            bybit_oi DECIMAL(30, 10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, symbol)
        )
    """)
    
    # 인덱스 생성
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ext_metrics_date ON futures_extended_metrics(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ext_metrics_symbol ON futures_extended_metrics(symbol)")
    
    conn.commit()
    cur.close()
    conn.close()


def upsert_extended_metrics(rows):
    """확장 지표 저장 (롱숏비율, Taker비율, Bybit 데이터)"""
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT OR REPLACE INTO futures_extended_metrics
        (date, symbol, long_short_ratio, long_account_pct, short_account_pct,
         taker_buy_sell_ratio, taker_buy_vol, taker_sell_vol,
         top_trader_long_short_ratio, bybit_funding_rate, bybit_oi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    cur.close()
    conn.close()


def upsert_metrics(rows):
    """
    metrics 데이터를 DB에 저장
    주의: sum_open_interest가 0인 경우 기존 데이터를 유지하여 데이터 손실 방지
    """
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    for row in rows:
        date_str, symbol, avg_funding, oi_value, ls_ratio, volatility, target_vol = row
        
        # 기존 데이터 확인
        cur.execute("""
            SELECT avg_funding_rate, sum_open_interest, volatility_24h 
            FROM binance_futures_metrics 
            WHERE date = ? AND symbol = ?
        """, (date_str, symbol))
        existing = cur.fetchone()
        
        # 기존 데이터가 있고, 새 값이 0인 경우 기존 값 유지
        if existing:
            old_funding, old_oi, old_vol = existing
            if oi_value == 0 and old_oi and old_oi > 0:
                oi_value = old_oi
            if avg_funding == 0 and old_funding and old_funding != 0:
                avg_funding = old_funding
            if volatility == 0 and old_vol and old_vol > 0:
                volatility = old_vol
        
        cur.execute(
            """
            INSERT OR REPLACE INTO binance_futures_metrics
            (date, symbol, avg_funding_rate, sum_open_interest, long_short_ratio, volatility_24h, target_volatility_24h)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (date_str, symbol, avg_funding, oi_value, ls_ratio, volatility, target_vol),
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


def fetch_long_short_ratio(symbol, start_ts, end_ts):
    """Binance 글로벌 롱숏 계정 비율 수집"""
    ratio_by_date = defaultdict(list)
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)
    
    # 최근 데이터만 limit으로 가져오고, start_ts~end_ts 범위만 필터링 (Binance가 startTime을 거부하는 경우 대응)
    try:
        params = {"symbol": symbol, "period": "1d", "limit": 500}
        response = session.get(LONG_SHORT_RATIO_ENDPOINT, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        for entry in data or []:
            ts = int(entry.get("timestamp", 0))
            if ts <= 0:
                continue
            if ts < start_ts or ts >= end_ts:
                continue
            dt = datetime.utcfromtimestamp(ts / 1000).date()
            ratio_by_date[dt].append({
                "long_short_ratio": float(entry.get("longShortRatio", 0) or 0),
                "long_account": float(entry.get("longAccount", 0) or 0),
                "short_account": float(entry.get("shortAccount", 0) or 0),
            })
    except Exception as e:
        print(f"  ⚠️ Long/Short Ratio fetch error: {e}")
    
    return ratio_by_date


def fetch_taker_ratio(symbol, start_ts, end_ts):
    """Binance Taker 매수/매도 비율 수집"""
    taker_by_date = defaultdict(list)
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)
    
    try:
        params = {"symbol": symbol, "period": "1d", "limit": 500}
        response = session.get(TAKER_RATIO_ENDPOINT, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        for entry in data or []:
            ts = int(entry.get("timestamp", 0))
            if ts <= 0:
                continue
            if ts < start_ts or ts >= end_ts:
                continue
            dt = datetime.utcfromtimestamp(ts / 1000).date()
            taker_by_date[dt].append({
                "buy_sell_ratio": float(entry.get("buySellRatio", 0) or 0),
                "buy_vol": float(entry.get("buyVol", 0) or 0),
                "sell_vol": float(entry.get("sellVol", 0) or 0),
            })
    except Exception as e:
        print(f"  ⚠️ Taker Ratio fetch error: {e}")
    
    return taker_by_date


def fetch_top_trader_position(symbol, start_ts, end_ts):
    """Binance 탑 트레이더 포지션 비율 수집"""
    position_by_date = defaultdict(list)
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)
    
    try:
        params = {"symbol": symbol, "period": "1d", "limit": 500}
        response = session.get(TOP_TRADER_POSITION_ENDPOINT, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        for entry in data or []:
            ts = int(entry.get("timestamp", 0))
            if ts <= 0:
                continue
            if ts < start_ts or ts >= end_ts:
                continue
            dt = datetime.utcfromtimestamp(ts / 1000).date()
            position_by_date[dt].append(float(entry.get("longShortRatio", 0) or 0))
    except Exception as e:
        print(f"  ⚠️ Top Trader Position fetch error: {e}")
    
    return position_by_date


def fetch_bybit_funding_history(symbol, start_ts, end_ts):
    """Bybit 펀딩비 히스토리 수집"""
    funding_by_date = defaultdict(list)
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)
    
    cursor = None
    
    while True:
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "limit": 200
            }
            if cursor:
                params["cursor"] = cursor
            
            response = session.get(BYBIT_FUNDING_ENDPOINT, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get("retCode") != 0:
                print(f"  ⚠️ Bybit Funding API 오류: {result.get('retMsg')}")
                break
            
            data = result.get("result", {}).get("list", [])
            if not data:
                break
            
            for entry in data:
                ts = int(entry.get("fundingRateTimestamp", 0))
                if ts < start_ts:
                    break
                if ts > end_ts:
                    continue
                
                dt = datetime.utcfromtimestamp(ts / 1000).date()
                funding_by_date[dt].append(float(entry.get("fundingRate", 0)))
            
            # 다음 페이지
            next_cursor = result.get("result", {}).get("nextPageCursor")
            if not next_cursor:
                break
            
            # 시작 시간 이전 데이터에 도달했는지 확인
            if data:
                oldest_ts = int(data[-1].get("fundingRateTimestamp", 0))
                if oldest_ts < start_ts:
                    break
            
            cursor = next_cursor
            time.sleep(0.1)
            
        except Exception as e:
            print(f"  ⚠️ Bybit Funding fetch error: {e}")
            break
    
    return funding_by_date


def fetch_bybit_oi(symbol, start_ts, end_ts):
    """Bybit OI 히스토리 수집"""
    oi_by_date = defaultdict(list)
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)
    
    cursor = None
    
    while True:
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "intervalTime": "D",  # 일별
                "limit": 200
            }
            if cursor:
                params["cursor"] = cursor
            
            response = session.get(BYBIT_OI_ENDPOINT, params=params, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if result.get("retCode") != 0:
                print(f"  ⚠️ Bybit OI API 오류: {result.get('retMsg')}")
                break
            
            data = result.get("result", {}).get("list", [])
            if not data:
                break
            
            for entry in data:
                ts = int(entry.get("timestamp", 0))
                if ts < start_ts:
                    break
                if ts > end_ts:
                    continue
                
                dt = datetime.utcfromtimestamp(ts / 1000).date()
                oi_by_date[dt].append(float(entry.get("openInterest", 0)))
            
            # 다음 페이지
            next_cursor = result.get("result", {}).get("nextPageCursor")
            if not next_cursor:
                break
            
            # 시작 시간 이전 데이터에 도달했는지 확인
            if data:
                oldest_ts = int(data[-1].get("timestamp", 0))
                if oldest_ts < start_ts:
                    break
            
            cursor = next_cursor
            time.sleep(0.1)
            
        except Exception as e:
            print(f"  ⚠️ Bybit OI fetch error: {e}")
            break
    
    return oi_by_date


def build_extended_metrics(symbol, start_dt: datetime = None, end_dt_exclusive: datetime = None):
    """확장 지표 수집 및 저장 (롱숏비율, Taker비율, Bybit 데이터)"""
    # 수집 기간 설정 (최근 30일 - API 제한)
    now_ts = int(time.time() * 1000)
    if end_dt_exclusive is None:
        end_ts = now_ts
    else:
        # 반드시 UTC 기준 epoch(ms)로 변환 (로컬 타임존 혼입 방지)
        if end_dt_exclusive.tzinfo is None:
            end_dt_exclusive = end_dt_exclusive.replace(tzinfo=timezone.utc)
        end_ts = int(end_dt_exclusive.timestamp() * 1000)
        # Binance/Bybit API는 미래 endTime을 싫어하므로 현재 시각으로 클램프
        end_ts = min(end_ts, now_ts)
    start_ts = end_ts - (30 * 24 * 60 * 60 * 1000)
    if start_dt is not None:
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        start_ts = max(start_ts, int(start_dt.timestamp() * 1000))
    
    print(f"\n📊 Fetching Extended Metrics for {symbol}...")
    print(f"   기간: {datetime.utcfromtimestamp(start_ts/1000).date()} ~ {datetime.utcfromtimestamp(end_ts/1000).date()}")
    
    # 1. 롱숏 비율
    print("   🔄 롱숏 비율 수집...")
    long_short_data = fetch_long_short_ratio(symbol, start_ts, end_ts)
    print(f"      ✅ {len(long_short_data)} days")
    
    # 2. Taker 비율
    print("   🔄 Taker 비율 수집...")
    taker_data = fetch_taker_ratio(symbol, start_ts, end_ts)
    print(f"      ✅ {len(taker_data)} days")
    
    # 3. 탑 트레이더 포지션
    print("   🔄 탑 트레이더 포지션 수집...")
    top_trader_data = fetch_top_trader_position(symbol, start_ts, end_ts)
    print(f"      ✅ {len(top_trader_data)} days")
    
    # 4. Bybit 펀딩비
    print("   🔄 Bybit 펀딩비 수집...")
    bybit_funding_data = fetch_bybit_funding_history(symbol, start_ts, end_ts)
    print(f"      ✅ {len(bybit_funding_data)} days")
    
    # 5. Bybit OI
    print("   🔄 Bybit OI 수집...")
    bybit_oi_data = fetch_bybit_oi(symbol, start_ts, end_ts)
    print(f"      ✅ {len(bybit_oi_data)} days")
    
    # 데이터 집계 및 저장
    all_dates = sorted(set(
        list(long_short_data.keys()) + 
        list(taker_data.keys()) + 
        list(top_trader_data.keys()) +
        list(bybit_funding_data.keys()) +
        list(bybit_oi_data.keys())
    ))
    
    rows = []
    for date_ in all_dates:
        # end-date 클램프: end_dt_exclusive가 있으면 그 이전 날짜만 저장
        if end_dt_exclusive is not None and date_ >= end_dt_exclusive.date():
            continue

        # 롱숏 비율 평균
        ls_list = long_short_data.get(date_, [])
        if ls_list:
            avg_ls_ratio = sum(d['long_short_ratio'] for d in ls_list) / len(ls_list)
            avg_long_pct = sum(d['long_account'] for d in ls_list) / len(ls_list)
            avg_short_pct = sum(d['short_account'] for d in ls_list) / len(ls_list)
        else:
            avg_ls_ratio, avg_long_pct, avg_short_pct = 0.0, 0.0, 0.0
        
        # Taker 비율 평균
        taker_list = taker_data.get(date_, [])
        if taker_list:
            avg_taker_ratio = sum(d['buy_sell_ratio'] for d in taker_list) / len(taker_list)
            avg_buy_vol = sum(d['buy_vol'] for d in taker_list) / len(taker_list)
            avg_sell_vol = sum(d['sell_vol'] for d in taker_list) / len(taker_list)
        else:
            avg_taker_ratio, avg_buy_vol, avg_sell_vol = 0.0, 0.0, 0.0
        
        # 탑 트레이더 포지션 평균
        tt_list = top_trader_data.get(date_, [])
        avg_tt_ratio = sum(tt_list) / len(tt_list) if tt_list else 0.0
        
        # Bybit 펀딩비 평균
        bybit_funding_list = bybit_funding_data.get(date_, [])
        avg_bybit_funding = sum(bybit_funding_list) / len(bybit_funding_list) if bybit_funding_list else 0.0
        
        # Bybit OI 평균
        bybit_oi_list = bybit_oi_data.get(date_, [])
        avg_bybit_oi = sum(bybit_oi_list) / len(bybit_oi_list) if bybit_oi_list else 0.0
        
        rows.append((
            date_.isoformat(),
            symbol,
            avg_ls_ratio,
            avg_long_pct,
            avg_short_pct,
            avg_taker_ratio,
            avg_buy_vol,
            avg_sell_vol,
            avg_tt_ratio,
            avg_bybit_funding,
            avg_bybit_oi
        ))
    
    upsert_extended_metrics(rows)
    print(f"   ✅ {symbol}: {len(rows)} extended metrics saved.")
    
    return len(rows)


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


def build_daily_metrics(symbol, start_dt: datetime = None, end_dt_exclusive: datetime = None):
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)
    
    if start_dt is None:
        start_dt = datetime(2023, 1, 1, tzinfo=timezone.utc)
    elif start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)

    # 일자 기반 API 파라미터의 안정성을 위해 UTC 00:00 기준으로 정규화
    start_dt = datetime(start_dt.year, start_dt.month, start_dt.day, tzinfo=timezone.utc)
    start_ts = int(start_dt.timestamp() * 1000)

    now_ts = int(time.time() * 1000)
    if end_dt_exclusive is None:
        end_ts = now_ts
    else:
        if end_dt_exclusive.tzinfo is None:
            end_dt_exclusive = end_dt_exclusive.replace(tzinfo=timezone.utc)
        end_dt_exclusive = datetime(end_dt_exclusive.year, end_dt_exclusive.month, end_dt_exclusive.day, tzinfo=timezone.utc)
        end_ts = int(end_dt_exclusive.timestamp() * 1000)
        end_ts = min(end_ts, now_ts)

    end_exclusive_date = None
    if end_dt_exclusive is not None:
        end_exclusive_date = end_dt_exclusive.date()

    print(f"🔄 Fetching Futures Metrics for {symbol} ({start_dt.strftime('%Y-%m-%d')} ~ {datetime.utcfromtimestamp(end_ts/1000).date()})...")

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
    
    # Binance OI History API is limited to "최근 약 30일" 이지만,
    # end-start가 정확히 30일이면 400(startTime invalid)이 발생하는 케이스가 있음.
    # 안전하게 29일 윈도우로 제한.
    # 최근 30일 데이터라도 수집하여 활용
    oi_limit_ts = end_ts - (29 * 24 * 60 * 60 * 1000)
    if start_ts < oi_limit_ts:
        curr_start = oi_limit_ts
        print(f"ℹ️ Open Interest history is limited to last 30 days. Collecting from {datetime.utcfromtimestamp(curr_start/1000).date()}.")
    else:
        curr_start = start_ts
        print(f"ℹ️ Collecting Open Interest from {datetime.utcfromtimestamp(curr_start/1000).date()}.")
    
    while curr_start < end_ts:
        try:
            # Max window 7 days for safety (29일 범위를 7일 단위로 잘라 수집)
            req_end = min(curr_start + 7 * 24 * 60 * 60 * 1000, end_ts)
            
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
        # end-date(포함) 기준 클램프: end_dt_exclusive가 있으면 그 이전 날짜만 저장
        if end_exclusive_date is not None and date_ >= end_exclusive_date:
            continue
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
    parser = argparse.ArgumentParser(description="Binance/Bybit Futures metrics collection into SQLite")
    parser.add_argument("--start-date", type=str, default=None, help="시작일 (YYYY-MM-DD). 미지정 시 2023-01-01")
    parser.add_argument("--end-date", type=str, default=None, help="종료일(포함) (YYYY-MM-DD). 미지정 시 오늘")
    args = parser.parse_args()

    start_dt = datetime(2023, 1, 1, tzinfo=timezone.utc) if not args.start_date else datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if args.end_date:
        end_inclusive = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt_exclusive = end_inclusive + timedelta(days=1)
    else:
        end_dt_exclusive = None

    symbols = os.getenv("BINANCE_FUTURES_SYMBOLS", "BTCUSDT,ETHUSDT").split(",")
    
    print("=" * 80)
    print("📊 Futures Metrics Collection (기본 + 확장)")
    print("=" * 80)
    
    for symbol in symbols:
        symbol = symbol.strip()
        
        # 1. 기본 지표 수집 (펀딩비, OI, 변동성)
        print(f"\n{'='*40}")
        print(f"[{symbol}] 기본 지표 수집")
        print(f"{'='*40}")
        build_daily_metrics(symbol, start_dt=start_dt, end_dt_exclusive=end_dt_exclusive)
        
        # 2. 확장 지표 수집 (롱숏비율, Taker비율, Bybit)
        print(f"\n{'='*40}")
        print(f"[{symbol}] 확장 지표 수집")
        print(f"{'='*40}")
        build_extended_metrics(symbol, start_dt=start_dt, end_dt_exclusive=end_dt_exclusive)
    
    print("\n" + "=" * 80)
    print("✅ 모든 Futures Metrics 수집 완료!")
    print("=" * 80)


def collect_extended_only():
    """확장 지표만 수집 (테스트용)"""
    ensure_db()
    symbols = os.getenv("BINANCE_FUTURES_SYMBOLS", "BTCUSDT,ETHUSDT").split(",")
    
    print("=" * 80)
    print("📊 Extended Futures Metrics Collection Only")
    print("=" * 80)
    
    for symbol in symbols:
        symbol = symbol.strip()
        build_extended_metrics(symbol)
    
    print("\n✅ 확장 지표 수집 완료!")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--extended-only":
        collect_extended_only()
    else:
        main()

