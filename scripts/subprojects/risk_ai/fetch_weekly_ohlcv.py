#!/usr/bin/env python3
"""
Binance 주봉(Weekly) OHLCV 데이터를 수집하여 SQLite에 저장하는 스크립트입니다.
제안된 5가지 고래-변동성 분석 패턴 구현을 위한 주봉 데이터 수집
"""

import sqlite3
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"
load_dotenv(ROOT / "config" / ".env")

BINANCE_BASE = "https://api.binance.com/api/v3/klines"


def ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


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


def fetch_binance_weekly(symbol, start_date_str="2023-01-01"):
    """Binance 주봉 데이터 수집 (2023-01-01부터 현재까지)"""
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(datetime.now().timestamp() * 1000)
    
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)

    print(f"🔄 Binance Weekly {symbol} 수집 시작 ({start_date_str} ~ 현재)...")
    
    all_rows = []
    
    while start_ts < end_ts:
        params = {
            "symbol": symbol,
            "interval": "1w",  # 주봉
            "startTime": start_ts,
            "limit": 1000  # 최대 1000개 (약 19년치)
        }
        
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
                # 주봉 종료일 (일요일)을 date로 사용
                close_ts = int(kline[6])  # close_time
                dt_str = datetime.utcfromtimestamp(close_ts / 1000).date().isoformat()
                
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
            
            all_rows.extend(rows)
            
            last_dt_str = datetime.utcfromtimestamp(last_ts / 1000).strftime('%Y-%m-%d')
            print(f"   ✅ ~{last_dt_str} ({len(rows)}주 수집)")
            
            # 다음 주로 이동 (7일 후)
            start_ts = last_ts + 7 * 24 * 60 * 60 * 1000
            
            # 마지막 데이터가 end_ts를 넘었으면 종료
            if last_ts >= end_ts:
                break
                
            time.sleep(0.1)
            
        except Exception as e:
            print(f"⚠️ Binance Weekly {symbol} fetch error: {e}")
            time.sleep(1)
            break
    
    # 일괄 저장
    if all_rows:
        upsert_rows(
            "binance_spot_weekly",
            all_rows,
            ["symbol", "date", "open", "high", "low", "close", "volume", "quote_volume"],
        )
        print(f"✅ Binance Weekly {symbol}: 총 {len(all_rows)}주 저장 완료")
    
    return len(all_rows)


def main():
    ensure_db()
    
    print("=" * 80)
    print("📊 Binance 주봉 OHLCV 데이터 수집")
    print("=" * 80)
    
    symbols = ["BTCUSDT"]  # BTC만 수집 (필요시 확장 가능)
    
    total_weeks = 0
    for symbol in symbols:
        weeks = fetch_binance_weekly(symbol, start_date_str="2023-01-01")
        total_weeks += weeks
        time.sleep(0.5)
    
    print("\n" + "=" * 80)
    print(f"✅ 총 {total_weeks}주 데이터 수집 완료")
    print("=" * 80)
    
    # 결과 확인
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(*) as count
        FROM binance_spot_weekly
        WHERE symbol = 'BTCUSDT'
    """)
    result = cursor.fetchone()
    conn.close()
    
    if result and result[0]:
        print(f"\n📊 저장된 데이터:")
        print(f"   기간: {result[0]} ~ {result[1]}")
        print(f"   총 주수: {result[2]}주")


if __name__ == "__main__":
    main()




