#!/usr/bin/env python3
"""
Open Interest 과거 데이터 수집 (Binance API 제한 우회 시도)
매일 실행하여 데이터를 축적하는 방식
"""

import sqlite3
import requests
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"

OI_ENDPOINT = "https://fapi.binance.com/futures/data/openInterestHist"

def ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_existing_oi_dates(symbol="BTCUSDT"):
    """DB에 이미 저장된 OI 데이터 날짜 목록"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT date 
        FROM binance_futures_metrics 
        WHERE symbol = ? AND sum_open_interest > 0
        ORDER BY date
    """, (symbol,))
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    return dates

def fetch_oi_for_date_range(symbol, start_ts, end_ts):
    """특정 기간의 OI 데이터 수집"""
    oi_by_date = defaultdict(list)
    
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)
    
    current_start = start_ts
    
    while current_start < end_ts:
        try:
            # 최대 30일 윈도우
            req_end = min(current_start + 30 * 24 * 60 * 60 * 1000, end_ts)
            
            params = {
                "symbol": symbol,
                "period": "1h",
                "startTime": int(current_start),
                "endTime": int(req_end),
                "limit": 500
            }
            
            response = session.get(OI_ENDPOINT, params=params, timeout=30)
            
            if response.status_code == 400:
                print(f"  ⚠️ 400 Error (범위 제한): {response.text[:100]}")
                break
            
            response.raise_for_status()
            data = response.json()
            
            if not data:
                current_start = req_end + 1
                continue
            
            last_ts = 0
            for entry in data:
                ts = int(entry["timestamp"])
                last_ts = ts
                dt = datetime.utcfromtimestamp(ts / 1000).date()
                val = float(entry.get("sumOpenInterestValue") or entry.get("sumOpenInterest", 0.0))
                oi_by_date[dt].append(val)
            
            if last_ts > 0:
                current_start = last_ts + 1
            else:
                current_start = req_end + 1
            
            time.sleep(0.2)  # Rate limit 방지
            
        except Exception as e:
            print(f"  ⚠️ 오류: {e}")
            current_start += 30 * 24 * 60 * 60 * 1000
            time.sleep(1)
    
    return oi_by_date

def update_oi_in_db(symbol, oi_by_date):
    """OI 데이터를 DB에 업데이트"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updated_count = 0
    for date_str, oi_values in oi_by_date.items():
        if not oi_values:
            continue
        
        avg_oi = sum(oi_values) / len(oi_values)
        
        cursor.execute("""
            UPDATE binance_futures_metrics
            SET sum_open_interest = ?
            WHERE symbol = ? AND date = ?
        """, (avg_oi, symbol, date_str))
        
        if cursor.rowcount > 0:
            updated_count += 1
    
    conn.commit()
    conn.close()
    
    return updated_count

def collect_oi_historical(symbol="BTCUSDT", days_back=30):
    """
    최근 N일의 OI 데이터 수집
    매일 실행하여 데이터를 축적
    """
    print("=" * 80)
    print(f"📊 Open Interest 데이터 수집 ({symbol})")
    print("=" * 80)
    
    ensure_db()
    
    # 기존 데이터 확인
    existing_dates = get_existing_oi_dates(symbol)
    print(f"\n📅 기존 OI 데이터: {len(existing_dates)}일")
    if existing_dates:
        print(f"   기간: {existing_dates[0]} ~ {existing_dates[-1]}")
    
    # 수집할 기간 설정 (최근 N일)
    end_ts = int(time.time() * 1000)
    start_ts = end_ts - (days_back * 24 * 60 * 60 * 1000)
    
    start_date = datetime.utcfromtimestamp(start_ts / 1000).date()
    end_date = datetime.utcfromtimestamp(end_ts / 1000).date()
    
    print(f"\n📥 수집 기간: {start_date} ~ {end_date} ({days_back}일)")
    
    # OI 데이터 수집
    print("\n🔄 데이터 수집 중...")
    oi_by_date = fetch_oi_for_date_range(symbol, start_ts, end_ts)
    
    print(f"   ✅ {len(oi_by_date)}일치 데이터 수집 완료")
    
    if not oi_by_date:
        print("   ⚠️ 수집된 데이터가 없습니다.")
        return
    
    # DB 업데이트
    print("\n💾 DB 업데이트 중...")
    updated_count = update_oi_in_db(symbol, oi_by_date)
    
    print(f"   ✅ {updated_count}건 업데이트 완료")
    
    # 결과 확인
    new_dates = get_existing_oi_dates(symbol)
    print(f"\n📊 업데이트 후 OI 데이터: {len(new_dates)}일")
    if new_dates:
        print(f"   기간: {new_dates[0]} ~ {new_dates[-1]}")
        print(f"   추가된 일수: {len(new_dates) - len(existing_dates)}일")
    
    print("\n" + "=" * 80)
    print("✅ 수집 완료!")
    print("=" * 80)
    print("\n💡 매일 실행하여 데이터를 축적하세요:")
    print("   python3 scripts/subprojects/risk_ai/collect_oi_historical.py")

if __name__ == "__main__":
    collect_oi_historical("BTCUSDT", days_back=30)

