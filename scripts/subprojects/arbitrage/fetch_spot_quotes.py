#!/usr/bin/env python3
"""
업비트/KRW와 바이낸스/USDT 과거 일봉 데이터를 수집하여 SQLite에 저장하는 서브 프로젝트 스크립트입니다.
"""

import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
load_dotenv(ROOT / "config" / ".env")
DB_PATH = ROOT / "data" / "project.db"

UPBIT_BASE = "https://api.upbit.com/v1/candles/days"
BINANCE_BASE = "https://api.binance.com/api/v3/klines"
BITGET_BASE = "https://api.bitget.com/api/spot/v1/market/candles"


def ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.close()


def upsert_rows(table, rows, columns):
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    placeholders = ", ".join("?" for _ in columns)
    column_list = ", ".join(columns)
    stmt = f"INSERT OR REPLACE INTO {table} ({column_list}) VALUES ({placeholders})"
    cursor.executemany(stmt, rows)
    conn.commit()
    cursor.close()
    conn.close()


def fetch_upbit_daily(market):
    """Upbit 2023-01-01부터 현재까지 수집 (역순)"""
    target_date = datetime.now()
    stop_date = datetime(2023, 1, 1)
    
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)

    while target_date > stop_date:
        to_str = target_date.strftime("%Y-%m-%d %H:%M:%S")
        params = {"market": market, "to": to_str, "count": 200}
        headers = {"Accept": "application/json"}
        
        try:
            response = session.get(UPBIT_BASE, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            if not data:
                break
                
            rows = []
            min_date = None
            
            for candle in data:
                kst_str = candle["candle_date_time_kst"]
                dt_obj = datetime.strptime(kst_str, "%Y-%m-%dT%H:%M:%S")
                rows.append(
                    (
                        market,
                        kst_str.split("T")[0],
                        candle.get("opening_price", candle.get("trade_price")),  # opening_price
                        candle.get("high_price", candle.get("trade_price")),     # high_price
                        candle.get("low_price", candle.get("trade_price")),      # low_price
                        candle["trade_price"],                                    # trade_price (close)
                        candle.get("candle_acc_trade_volume", candle.get("acc_trade_volume", 0.0)),
                        candle.get("candle_acc_trade_price", candle.get("acc_trade_price", 0.0)),
                    )
                )
                if min_date is None or dt_obj < min_date:
                    min_date = dt_obj

            upsert_rows(
                "upbit_daily",
                rows,
                ["market", "date", "opening_price", "high_price", "low_price", "trade_price", "acc_trade_volume_24h", "acc_trade_price_24h"],
            )
            print(f"✅ Upbit {market}: ~{to_str.split()[0]} ({len(rows)}건)")
            
            if min_date:
                target_date = min_date - timedelta(days=1)
            else:
                break
                
            time.sleep(0.1) # Rate limit 조절
            
        except Exception as e:
            print(f"⚠️ Upbit {market} fetch error: {e}")
            time.sleep(1)
            break


def fetch_binance_spot(symbol):
    """Binance 2023-01-01부터 현재까지 수집 (정순)"""
    start_dt = datetime(2023, 1, 1)
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(datetime.now().timestamp() * 1000)
    
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)

    while start_ts < end_ts:
        params = {"symbol": symbol, "interval": "1d", "startTime": start_ts, "limit": 1000}
        try:
            response = session.get(BINANCE_BASE, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data:
                break
                
            rows = []
            last_ts = start_ts
            
            for kline in data:
                ts = int(kline[0])
                dt_str = datetime.utcfromtimestamp(ts / 1000).date().isoformat()
                # kline: [open_time, open, high, low, close, volume, close_time, quote_volume, ...]
                rows.append((
                    symbol, 
                    dt_str, 
                    float(kline[1]),  # open
                    float(kline[2]),  # high
                    float(kline[3]),  # low
                    float(kline[4]),  # close
                    float(kline[5]),  # volume
                    float(kline[7])   # quote_volume
                ))
                last_ts = ts
            
            upsert_rows(
                "binance_spot_daily",
                rows,
                ["symbol", "date", "open", "high", "low", "close", "volume", "quote_volume"],
            )
            
            last_dt_str = datetime.utcfromtimestamp(last_ts / 1000).strftime('%Y-%m-%d')
            print(f"✅ Binance {symbol}: ~{last_dt_str} ({len(rows)}건)")
            
            start_ts = last_ts + 24 * 60 * 60 * 1000 # Next day
            time.sleep(0.1)
            
        except Exception as e:
            print(f"⚠️ Binance {symbol} fetch error: {e}")
            time.sleep(1)
            break


def fetch_bitget_spot(symbol, start_date_str="2024-01-01"):
    """Bitget 지정 날짜부터 현재까지 수집 (정순)"""
    # Bitget symbol 형식: BTCUSDT_SPBL (SPBL = Spot)
    if not symbol.endswith("_SPBL"):
        symbol_api = f"{symbol}_SPBL"
    else:
        symbol_api = symbol
        symbol = symbol.replace("_SPBL", "")
    
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(datetime.now().timestamp() * 1000)
    
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)

    print(f"🔄 Bitget {symbol} 수집 시작 ({start_date_str} ~ 현재)...")
    
    # 비트겟 API는 before와 after를 모두 지정하면 최신 데이터부터 역순으로 반환
    # 따라서 before를 점진적으로 줄여가며 과거 데이터를 수집해야 함
    current_end_ts = end_ts  # 현재 시간부터 시작
    
    while current_end_ts > start_ts:
        # Bitget API: symbol (BTCUSDT_SPBL), period (1day), after (startTime), before (endTime), limit
        # before를 점진적으로 줄여가며 과거 데이터 수집
        params = {
            "symbol": symbol_api,
            "period": "1day",  # Bitget는 "1day" 형식 사용
            "after": str(start_ts),
            "before": str(current_end_ts),  # 점진적으로 줄임
            "limit": 200
        }
        try:
            response = session.get(BITGET_BASE, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"⚠️ Bitget {symbol} HTTP {response.status_code}: {response.text[:200]}")
                break
            
            result = response.json()
            
            # Bitget 응답 형식: {"code": "00000", "msg": "success", "data": [...]}
            # 또는 {"code": 200, "data": [...]} 형식일 수 있음
            if result.get("code") not in ["00000", 200, "200"] or not result.get("data"):
                print(f"⚠️ Bitget {symbol} API 응답 오류: {result.get('msg', result.get('message', 'Unknown error'))}")
                break
            
            data = result["data"]
            if not data:
                break
                
            rows = []
            timestamps = []
            
            for candle in data:
                # Bitget 응답: {"ts": timestamp, "open": ..., "high": ..., "close": ..., "quoteVol": ..., "baseVol": ...}
                ts = int(candle.get("ts", 0))
                if ts == 0:
                    continue
                    
                timestamps.append(ts)
                dt_str = datetime.utcfromtimestamp(ts / 1000).date().isoformat()
                # symbol에서 _SPBL 제거하여 저장 (BTCUSDT_SPBL -> BTCUSDT)
                symbol_clean = symbol.replace("_SPBL", "")
                
                rows.append((
                    symbol_clean,
                    dt_str,
                    float(candle.get("open", 0)),
                    float(candle.get("high", 0)),
                    float(candle.get("low", 0)),
                    float(candle.get("close", 0)),
                    float(candle.get("baseVol", 0)),  # base volume
                    float(candle.get("quoteVol", candle.get("usdtVol", 0))),  # quote volume (USDT)
                ))
            
            if rows:
                upsert_rows(
                    "bitget_spot_daily",
                    rows,
                    ["symbol", "date", "open", "high", "low", "close", "volume", "quote_volume"],
                )
                
                # Bitget API는 최신 -> 과거 순으로 반환하므로, 가장 오래된 타임스탬프를 찾아야 함
                oldest_ts = min(timestamps)
                newest_ts = max(timestamps)
                oldest_dt = datetime.utcfromtimestamp(oldest_ts / 1000).strftime('%Y-%m-%d')
                newest_dt = datetime.utcfromtimestamp(newest_ts / 1000).strftime('%Y-%m-%d')
                
                print(f"✅ Bitget {symbol_clean}: {oldest_dt} ~ {newest_dt} ({len(rows)}건)")
                
                # 가장 오래된 타임스탬프의 1ms 전을 다음 before로 설정 (중복 방지)
                current_end_ts = oldest_ts - 1
                
                # 더 이상 진행할 수 없으면 종료 (가장 오래된 데이터가 요청 시작일보다 이전인 경우)
                if oldest_ts <= start_ts:
                    print(f"✅ Bitget {symbol_clean}: 수집 완료 (시작일 도달)")
                    break
            else:
                # 데이터가 없으면 종료
                print(f"⚠️ Bitget {symbol_clean}: 더 이상 데이터 없음")
                break
                
            time.sleep(0.1)
            
        except Exception as e:
            print(f"⚠️ Bitget {symbol} fetch error: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(1)
            break


def main():
    ensure_db()
    upbit_markets = os.getenv("UPBIT_MARKETS", "KRW-BTC,KRW-ETH").split(",")
    binance_symbols = os.getenv("BINANCE_SYMBOLS", "BTCUSDT,ETHUSDT").split(",")
    bitget_symbols = os.getenv("BITGET_SYMBOLS", "BTCUSDT,ETHUSDT").split(",")

    print("📊 업비트 데이터 수집 시작...")
    for market in upbit_markets:
        fetch_upbit_daily(market.strip())
    
    print("\n📊 바이낸스 데이터 수집 시작...")
    for symbol in binance_symbols:
        fetch_binance_spot(symbol.strip())
    
    print("\n📊 비트겟 데이터 수집 시작...")
    for symbol in bitget_symbols:
        fetch_bitget_spot(symbol.strip(), start_date_str="2024-01-01")


if __name__ == "__main__":
    main()

