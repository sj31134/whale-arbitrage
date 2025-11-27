#!/usr/bin/env python3
"""
Binance API를 사용하여 Open Interest 과거 데이터 수집 (2023-01-01 ~ 현재)
Binance API는 최근 30일만 제공하지만, 매일 수집하여 축적된 데이터를 활용
또는 가능한 범위 내에서 최대한 수집
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
    """특정 기간의 OI 데이터 수집 (Binance API 제한: 최근 30일)"""
    oi_by_date = defaultdict(list)
    
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(max_retries=3)
    session.mount("https://", adapter)
    
    current_start = start_ts
    
    print(f"   수집 기간: {datetime.utcfromtimestamp(start_ts/1000).date()} ~ {datetime.utcfromtimestamp(end_ts/1000).date()}")
    
    while current_start < end_ts:
        try:
            # Binance API 제한: 최대 30일 윈도우
            req_end = min(current_start + 30 * 24 * 60 * 60 * 1000, end_ts)
            
            params = {
                "symbol": symbol,
                "period": "1h",  # 1시간 단위
                "startTime": int(current_start),
                "endTime": int(req_end),
                "limit": 500
            }
            
            response = session.get(OI_ENDPOINT, params=params, timeout=30)
            
            if response.status_code == 400:
                error_text = response.text
                if "Invalid symbol" in error_text or "startTime" in error_text.lower():
                    print(f"  ⚠️ API 제한 도달 또는 오류: {error_text[:100]}")
                    # 최근 30일만 수집 가능
                    break
                else:
                    print(f"  ⚠️ 400 Error: {error_text[:100]}")
                    break
            
            response.raise_for_status()
            data = response.json()
            
            if not data:
                print(f"  ⚠️ 데이터 없음 (기간: {datetime.utcfromtimestamp(current_start/1000).date()} ~ {datetime.utcfromtimestamp(req_end/1000).date()})")
                # 최근 30일만 수집 가능한 경우
                if current_start < end_ts - 30 * 24 * 60 * 60 * 1000:
                    print(f"  ℹ️ Binance API는 최근 30일만 제공합니다. 과거 데이터는 매일 수집하여 축적해야 합니다.")
                    break
                current_start = req_end + 1
                continue
            
            last_ts = 0
            for entry in data:
                ts = int(entry["timestamp"])
                last_ts = ts
                dt = datetime.utcfromtimestamp(ts / 1000).date()
                # sumOpenInterestValue 또는 sumOpenInterest 사용
                val = float(entry.get("sumOpenInterestValue") or entry.get("sumOpenInterest", 0.0))
                if val > 0:
                    oi_by_date[dt].append(val)
            
            if last_ts > 0:
                current_start = last_ts + 1
                print(f"  ✅ {datetime.utcfromtimestamp(last_ts/1000).date()}까지 수집 완료")
            else:
                current_start = req_end + 1
            
            time.sleep(0.2)  # Rate limit 방지
            
        except Exception as e:
            print(f"  ⚠️ 오류: {e}")
            # 최근 30일만 수집 가능한 경우 중단
            if "400" in str(e) or "Invalid" in str(e):
                print(f"  ℹ️ Binance API는 최근 30일만 제공합니다.")
                break
            current_start += 30 * 24 * 60 * 60 * 1000
            time.sleep(1)
    
    return oi_by_date


def update_oi_in_db(symbol, oi_by_date):
    """OI 데이터를 DB에 업데이트 (일별 평균값)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updated_count = 0
    created_count = 0
    
    for date_str, oi_values in sorted(oi_by_date.items()):
        if not oi_values:
            continue
        
        # 일별 평균값 계산
        avg_oi = sum(oi_values) / len(oi_values)
        
        # 기존 레코드 업데이트 또는 생성
        cursor.execute("""
            UPDATE binance_futures_metrics
            SET sum_open_interest = ?
            WHERE symbol = ? AND date = ?
        """, (avg_oi, symbol, date_str.isoformat()))
        
        if cursor.rowcount > 0:
            updated_count += 1
        else:
            # 레코드가 없으면 새로 생성
            cursor.execute("""
                INSERT INTO binance_futures_metrics
                (date, symbol, avg_funding_rate, sum_open_interest, long_short_ratio, volatility_24h, target_volatility_24h)
                VALUES (?, ?, 0.0, ?, 0.0, 0.0, 0.0)
            """, (date_str.isoformat(), symbol, avg_oi))
            created_count += 1
    
    conn.commit()
    conn.close()
    
    return updated_count, created_count


def collect_oi_historical(symbol="BTCUSDT", start_date_str="2023-01-01"):
    """
    OI 과거 데이터 수집 (2023-01-01 ~ 현재)
    Binance API 제한으로 인해 최근 30일만 수집 가능하지만, 
    매일 실행하여 축적된 데이터를 활용
    """
    print("=" * 80)
    print(f"📊 Open Interest 과거 데이터 수집 ({symbol})")
    print("=" * 80)
    
    ensure_db()
    
    # 기존 데이터 확인
    existing_dates = get_existing_oi_dates(symbol)
    print(f"\n📅 기존 OI 데이터: {len(existing_dates)}일")
    if existing_dates:
        print(f"   기간: {existing_dates[0]} ~ {existing_dates[-1]}")
    
    # 수집할 기간 설정
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_dt = datetime.now()
    
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    
    print(f"\n📥 수집 목표 기간: {start_date_str} ~ {end_dt.date()}")
    print(f"   ⚠️ Binance API 제한: 최근 30일만 제공")
    
    # OI 데이터 수집
    print("\n🔄 데이터 수집 중...")
    oi_by_date = fetch_oi_for_date_range(symbol, start_ts, end_ts)
    
    print(f"\n   ✅ {len(oi_by_date)}일치 데이터 수집 완료")
    
    if not oi_by_date:
        print("   ⚠️ 수집된 데이터가 없습니다.")
        print("   ℹ️ Binance API는 최근 30일만 제공합니다.")
        print("   ℹ️ 과거 데이터를 얻으려면 매일 수집하여 축적해야 합니다.")
        return
    
    # DB 업데이트
    print("\n💾 DB 업데이트 중...")
    updated_count, created_count = update_oi_in_db(symbol, oi_by_date)
    
    print(f"   ✅ {updated_count}건 업데이트, {created_count}건 생성 완료")
    
    # 결과 확인
    new_dates = get_existing_oi_dates(symbol)
    print(f"\n📊 업데이트 후 OI 데이터: {len(new_dates)}일")
    if new_dates:
        print(f"   기간: {new_dates[0]} ~ {new_dates[-1]}")
        added_days = len(new_dates) - len(existing_dates)
        if added_days > 0:
            print(f"   추가된 일수: {added_days}일")
    
    # 기간 확인
    if new_dates:
        first_date = datetime.strptime(new_dates[0], "%Y-%m-%d").date()
        target_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        
        if first_date > target_date:
            print(f"\n⚠️ 목표 기간({start_date_str})까지 데이터가 부족합니다.")
            print(f"   현재 최초 데이터: {new_dates[0]}")
            print(f"   ℹ️ Binance API는 최근 30일만 제공하므로, 매일 수집하여 축적해야 합니다.")
            print(f"   ℹ️ 매일 실행: python3 scripts/subprojects/risk_ai/collect_oi_historical.py")
    
    print("\n" + "=" * 80)
    print("✅ 수집 완료!")
    print("=" * 80)


if __name__ == "__main__":
    collect_oi_historical("BTCUSDT", start_date_str="2023-01-01")




