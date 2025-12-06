#!/usr/bin/env python3
"""
Supabase에서 로컬 SQLite DB로 데이터 복구
오늘 fetch_futures_metrics.py 실행으로 손상된 sum_open_interest 데이터 복구
"""

import os
import sys
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

from supabase import create_client

DB_PATH = PROJECT_ROOT / "data" / "project.db"

def get_supabase_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY가 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def check_supabase_data():
    """Supabase에 데이터가 있는지 확인"""
    print("=== Supabase 데이터 확인 ===")
    try:
        supabase = get_supabase_client()
        
        # BTCUSDT의 sum_open_interest가 0이 아닌 레코드 확인
        response = supabase.table("binance_futures_metrics") \
            .select("date, sum_open_interest") \
            .eq("symbol", "BTCUSDT") \
            .gt("sum_open_interest", 0) \
            .order("date", desc=True) \
            .limit(10) \
            .execute()
        
        if response.data and len(response.data) > 0:
            print(f"✅ Supabase에 유효한 OI 데이터 존재!")
            print(f"   최근 데이터 예시:")
            for row in response.data[:5]:
                print(f"   {row['date']}: {row['sum_open_interest']}")
            return True
        else:
            print("❌ Supabase에 유효한 OI 데이터가 없습니다.")
            return False
            
    except Exception as e:
        print(f"❌ Supabase 연결 오류: {e}")
        return False

def restore_from_supabase():
    """Supabase에서 로컬 DB로 데이터 복구"""
    print("\n=== Supabase에서 로컬 DB로 복구 시작 ===")
    
    try:
        supabase = get_supabase_client()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for symbol in ["BTCUSDT", "ETHUSDT"]:
            print(f"\n📊 {symbol} 복구 중...")
            
            # Supabase에서 모든 데이터 가져오기
            all_data = []
            offset = 0
            limit = 1000
            
            while True:
                response = supabase.table("binance_futures_metrics") \
                    .select("*") \
                    .eq("symbol", symbol) \
                    .order("date") \
                    .range(offset, offset + limit - 1) \
                    .execute()
                
                if not response.data or len(response.data) == 0:
                    break
                    
                all_data.extend(response.data)
                offset += limit
                
                if len(response.data) < limit:
                    break
            
            print(f"   Supabase에서 {len(all_data)}건 조회됨")
            
            # 로컬 DB 업데이트 (sum_open_interest가 0이 아닌 경우에만)
            restored_count = 0
            for row in all_data:
                date_str = row['date']
                sum_oi = row.get('sum_open_interest', 0)
                avg_funding = row.get('avg_funding_rate', 0)
                long_short = row.get('long_short_ratio', 0)
                volatility = row.get('volatility_24h', 0)
                
                # sum_open_interest가 0이 아닌 경우에만 업데이트
                if sum_oi and sum_oi > 0:
                    cursor.execute("""
                        INSERT INTO binance_futures_metrics (
                            date, symbol, avg_funding_rate, sum_open_interest, 
                            long_short_ratio, volatility_24h
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(date, symbol) DO UPDATE SET
                            sum_open_interest = excluded.sum_open_interest
                        WHERE binance_futures_metrics.sum_open_interest = 0 
                           OR binance_futures_metrics.sum_open_interest IS NULL
                    """, (date_str, symbol, avg_funding, sum_oi, long_short, volatility))
                    restored_count += 1
            
            conn.commit()
            print(f"   ✅ {symbol}: {restored_count}건 복구 완료")
        
        conn.close()
        print("\n✅ Supabase에서 복구 완료!")
        return True
        
    except Exception as e:
        print(f"❌ 복구 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_restoration():
    """복구 결과 확인"""
    print("\n=== 복구 결과 확인 ===")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for symbol in ["BTCUSDT", "ETHUSDT"]:
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN sum_open_interest > 0 THEN 1 ELSE 0 END) as valid,
                SUM(CASE WHEN sum_open_interest = 0 OR sum_open_interest IS NULL THEN 1 ELSE 0 END) as zero
            FROM binance_futures_metrics
            WHERE symbol = ?
        """, (symbol,))
        row = cursor.fetchone()
        print(f"{symbol}: 전체 {row[0]}건, 유효 {row[1]}건, 0값 {row[2]}건")
        
        # 최근 데이터 확인
        cursor.execute("""
            SELECT date, sum_open_interest 
            FROM binance_futures_metrics 
            WHERE symbol = ? 
            ORDER BY date DESC 
            LIMIT 5
        """, (symbol,))
        print(f"   최근 데이터:")
        for r in cursor.fetchall():
            print(f"   {r[0]}: {r[1]}")
    
    conn.close()

if __name__ == "__main__":
    # 1. Supabase 데이터 확인
    has_supabase_data = check_supabase_data()
    
    if has_supabase_data:
        # 2. Supabase에서 복구
        restore_from_supabase()
        
        # 3. 복구 결과 확인
        verify_restoration()
    else:
        print("\n⚠️ Supabase에 데이터가 없습니다. Binance Vision Archive에서 복구가 필요합니다.")

