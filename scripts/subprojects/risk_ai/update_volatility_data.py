#!/usr/bin/env python3
"""
기존 binance_futures_metrics 데이터에 volatility_24h를 업데이트하는 스크립트
전체 재수집 대신 volatility만 업데이트하여 시간 절약
"""

import sys
from pathlib import Path
import sqlite3
from datetime import datetime
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))

from fetch_futures_metrics import fetch_daily_klines

DB_PATH = ROOT / "data" / "project.db"

def update_volatility_for_existing_data(symbol="BTCUSDT"):
    """기존 데이터의 volatility_24h를 업데이트"""
    print("=" * 80)
    print(f"🔄 {symbol} volatility_24h 업데이트 시작")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 기존 데이터의 날짜 범위 확인
    cursor.execute("""
        SELECT MIN(date), MAX(date) 
        FROM binance_futures_metrics 
        WHERE symbol = ?
    """, (symbol,))
    min_date_str, max_date_str = cursor.fetchone()
    
    if not min_date_str:
        print("❌ 기존 데이터가 없습니다. 전체 수집을 실행하세요.")
        conn.close()
        return
    
    min_date = datetime.strptime(min_date_str, "%Y-%m-%d").date()
    max_date = datetime.strptime(max_date_str, "%Y-%m-%d").date()
    
    print(f"\n📅 기존 데이터 기간: {min_date} ~ {max_date}")
    
    # 2. volatility가 0인 날짜 확인
    cursor.execute("""
        SELECT date 
        FROM binance_futures_metrics 
        WHERE symbol = ? AND (volatility_24h = 0 OR volatility_24h IS NULL)
        ORDER BY date
    """, (symbol,))
    dates_to_update = [row[0] for row in cursor.fetchall()]
    
    if not dates_to_update:
        print("✅ 모든 데이터의 volatility가 이미 업데이트되어 있습니다.")
        conn.close()
        return
    
    print(f"📊 업데이트 필요한 날짜: {len(dates_to_update)}일")
    print(f"   첫 날짜: {dates_to_update[0]}")
    print(f"   마지막 날짜: {dates_to_update[-1]}")
    
    # 3. Klines 데이터 수집
    start_ts = int(datetime.strptime(dates_to_update[0], "%Y-%m-%d").timestamp() * 1000)
    end_date = datetime.strptime(dates_to_update[-1], "%Y-%m-%d").date()
    end_ts = int((datetime.combine(end_date, datetime.max.time()).timestamp() + 86400) * 1000)
    
    print(f"\n📥 Klines 데이터 수집 중...")
    print(f"   기간: {dates_to_update[0]} ~ {dates_to_update[-1]}")
    
    klines_by_date = fetch_daily_klines(symbol, start_ts, end_ts)
    
    print(f"   ✅ {len(klines_by_date)}일치 데이터 수집 완료")
    
    # 4. DB 업데이트
    print(f"\n💾 DB 업데이트 중...")
    updated_count = 0
    
    for date_str in dates_to_update:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        volatility = klines_by_date.get(date_obj, 0.0)
        
        cursor.execute("""
            UPDATE binance_futures_metrics
            SET volatility_24h = ?
            WHERE symbol = ? AND date = ?
        """, (volatility, symbol, date_str))
        
        updated_count += 1
        
        if updated_count % 100 == 0:
            conn.commit()
            print(f"   진행: {updated_count}/{len(dates_to_update)}")
    
    conn.commit()
    print(f"   ✅ {updated_count}건 업데이트 완료")
    
    # 5. 결과 확인
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN volatility_24h > 0 THEN 1 ELSE 0 END) as non_zero
        FROM binance_futures_metrics
        WHERE symbol = ?
    """, (symbol,))
    total, non_zero = cursor.fetchone()
    
    print(f"\n📊 업데이트 결과:")
    print(f"   총 레코드: {total}건")
    print(f"   volatility > 0: {non_zero}건 ({non_zero/total*100:.1f}%)")
    
    if non_zero > 0:
        cursor.execute("""
            SELECT AVG(volatility_24h), MIN(volatility_24h), MAX(volatility_24h)
            FROM binance_futures_metrics
            WHERE symbol = ? AND volatility_24h > 0
        """, (symbol,))
        avg_vol, min_vol, max_vol = cursor.fetchone()
        print(f"   평균 변동성: {avg_vol:.4f} ({avg_vol*100:.2f}%)")
        print(f"   최소 변동성: {min_vol:.4f} ({min_vol*100:.2f}%)")
        print(f"   최대 변동성: {max_vol:.4f} ({max_vol*100:.2f}%)")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 업데이트 완료!")
    print("=" * 80)

if __name__ == "__main__":
    update_volatility_for_existing_data("BTCUSDT")

