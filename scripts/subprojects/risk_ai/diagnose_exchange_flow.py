#!/usr/bin/env python3
"""
거래소 유입/유출 데이터가 0인 문제 진단 스크립트

문제: whale_daily_stats의 exchange_inflow_usd, exchange_outflow_usd가 모두 0
원인 파악:
1. whale_transactions의 transaction_direction 값 확인
2. 집계 로직 검증
3. 데이터 동기화 상태 확인
"""

import os
import sys
import sqlite3
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

ROOT = Path(__file__).resolve().parent.parents[2]
env_path = ROOT / "config" / ".env"
load_dotenv(env_path, override=True)

# 데이터베이스 경로
DB_PATH = ROOT / "data" / "project.db"

# Supabase 연결
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def diagnose_sqlite():
    """SQLite 데이터베이스 진단"""
    print("=" * 80)
    print("📊 SQLite 데이터베이스 진단")
    print("=" * 80)
    
    if not DB_PATH.exists():
        print(f"❌ SQLite 파일이 없습니다: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. whale_daily_stats 현황
    print("\n[1] whale_daily_stats 현황:")
    query1 = """
    SELECT 
        coin_symbol,
        COUNT(*) as total_rows,
        SUM(CASE WHEN exchange_inflow_usd > 0 THEN 1 ELSE 0 END) as inflow_nonzero,
        SUM(CASE WHEN exchange_outflow_usd > 0 THEN 1 ELSE 0 END) as outflow_nonzero,
        SUM(CASE WHEN net_flow_usd != 0 THEN 1 ELSE 0 END) as netflow_nonzero,
        AVG(exchange_inflow_usd) as avg_inflow,
        AVG(exchange_outflow_usd) as avg_outflow,
        MAX(exchange_inflow_usd) as max_inflow,
        MAX(exchange_outflow_usd) as max_outflow
    FROM whale_daily_stats
    GROUP BY coin_symbol
    """
    
    df1 = pd.read_sql(query1, conn)
    print(df1.to_string())
    
    # 2. whale_transactions 테이블 존재 여부
    print("\n[2] whale_transactions 테이블 확인:")
    try:
        # 테이블 존재 여부 확인
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='whale_transactions'
        """)
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            print("⚠️ whale_transactions 테이블이 SQLite에 없습니다.")
            print("   → Supabase에서만 데이터가 있을 수 있습니다.")
            conn.close()
            return
        
        query2 = """
        SELECT 
            coin_symbol,
            COUNT(*) as total_txs,
            COUNT(DISTINCT date(block_timestamp)) as unique_dates,
            MIN(block_timestamp) as min_date,
            MAX(block_timestamp) as max_date
        FROM whale_transactions
        GROUP BY coin_symbol
        """
        df2 = pd.read_sql(query2, conn)
        print(df2.to_string())
        
        # transaction_direction 분포
        query3 = """
        SELECT 
            coin_symbol,
            transaction_direction,
            COUNT(*) as count,
            SUM(amount_usd) as total_amount
        FROM whale_transactions
        WHERE transaction_direction IS NOT NULL
        GROUP BY coin_symbol, transaction_direction
        ORDER BY coin_symbol, transaction_direction
        """
        df3 = pd.read_sql(query3, conn)
        print("\n[2-1] transaction_direction 분포:")
        print(df3.to_string())
        
        # NULL 또는 빈 값 확인
        query4 = """
        SELECT 
            coin_symbol,
            COUNT(*) as total,
            SUM(CASE WHEN transaction_direction IS NULL THEN 1 ELSE 0 END) as null_count,
            SUM(CASE WHEN transaction_direction = '' THEN 1 ELSE 0 END) as empty_count,
            COUNT(DISTINCT transaction_direction) as unique_directions
        FROM whale_transactions
        GROUP BY coin_symbol
        """
        df4 = pd.read_sql(query4, conn)
        print("\n[2-2] transaction_direction NULL/빈 값 확인:")
        print(df4.to_string())
        
    except sqlite3.OperationalError as e:
        print(f"❌ whale_transactions 테이블 조회 실패: {e}")
        print("   → Supabase에서만 데이터가 있을 수 있습니다.")
    
    conn.close()


def diagnose_supabase():
    """Supabase 데이터베이스 진단"""
    print("\n" + "=" * 80)
    print("📊 Supabase 데이터베이스 진단")
    print("=" * 80)
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase 환경변수가 설정되지 않았습니다.")
        return
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # 1. whale_transactions의 transaction_direction 분포
        print("\n[1] whale_transactions transaction_direction 분포:")
        try:
            response = supabase.table('whale_transactions').select(
                'coin_symbol, transaction_direction'
            ).limit(10000).execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                
                # 분포 계산
                dist = df.groupby(['coin_symbol', 'transaction_direction']).size().reset_index(name='count')
                print(dist.to_string())
                
                # NULL/빈 값 확인
                null_info = df.groupby('coin_symbol').agg({
                    'transaction_direction': [
                        lambda x: x.isnull().sum(),
                        lambda x: (x == '').sum(),
                        'nunique'
                    ]
                }).reset_index()
                print("\n[1-1] NULL/빈 값 확인:")
                print(null_info.to_string())
            else:
                print("⚠️ 데이터가 없습니다.")
        except Exception as e:
            print(f"❌ Supabase 조회 실패: {e}")
        
        # 2. whale_daily_stats 현황
        print("\n[2] whale_daily_stats 현황 (Supabase):")
        try:
            response = supabase.table('whale_daily_stats').select(
                'coin_symbol, exchange_inflow_usd, exchange_outflow_usd, net_flow_usd'
            ).limit(1000).execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                
                summary = df.groupby('coin_symbol').agg({
                    'exchange_inflow_usd': ['count', lambda x: (x > 0).sum(), 'mean', 'max'],
                    'exchange_outflow_usd': ['count', lambda x: (x > 0).sum(), 'mean', 'max'],
                    'net_flow_usd': ['count', lambda x: (x != 0).sum(), 'mean']
                }).reset_index()
                print(summary.to_string())
            else:
                print("⚠️ 데이터가 없습니다.")
        except Exception as e:
            print(f"❌ Supabase 조회 실패: {e}")
            
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")


def test_aggregation_logic():
    """집계 로직 테스트"""
    print("\n" + "=" * 80)
    print("🔍 집계 로직 테스트")
    print("=" * 80)
    
    if not DB_PATH.exists():
        print(f"❌ SQLite 파일이 없습니다: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    
    # 테이블 존재 여부 확인
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='whale_transactions'
    """)
    table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        print("⚠️ whale_transactions 테이블이 SQLite에 없습니다.")
        print("   → Supabase에서 데이터를 확인하거나 동기화가 필요합니다.")
        conn.close()
        return
    
    # whale_transactions에서 샘플 데이터로 집계 테스트
    try:
        query = """
        SELECT 
            date(block_timestamp) as date,
            coin_symbol,
            transaction_direction,
            SUM(amount_usd) as total_amount
        FROM whale_transactions
        WHERE transaction_direction IS NOT NULL
        AND transaction_direction != ''
        AND coin_symbol IN ('BTC', 'ETH')
        GROUP BY date(block_timestamp), coin_symbol, transaction_direction
        ORDER BY date DESC
        LIMIT 100
        """
        
        df = pd.read_sql(query, conn)
        
        if len(df) > 0:
            print("\n[1] 샘플 거래 데이터:")
            print(df.head(20).to_string())
            
            # 집계 로직 시뮬레이션
            print("\n[2] 집계 로직 시뮬레이션:")
            test_date = df['date'].iloc[0]
            test_coin = df['coin_symbol'].iloc[0]
            
            test_df = df[(df['date'] == test_date) & (df['coin_symbol'] == test_coin)]
            
            inflow = test_df[test_df['transaction_direction'] == 'exchange_inflow']['total_amount'].sum()
            outflow = test_df[test_df['transaction_direction'] == 'exchange_outflow']['total_amount'].sum()
            
            print(f"   날짜: {test_date}, 코인: {test_coin}")
            print(f"   exchange_inflow: {inflow}")
            print(f"   exchange_outflow: {outflow}")
            print(f"   net_flow: {inflow - outflow}")
            
            if inflow == 0 and outflow == 0:
                print("   ⚠️ 이 날짜에도 유입/유출이 0입니다.")
                print("   → transaction_direction 값이 'exchange_inflow'/'exchange_outflow'가 아닐 수 있습니다.")
        else:
            print("⚠️ 테스트할 데이터가 없습니다.")
            
    except sqlite3.OperationalError as e:
        print(f"❌ 테이블 조회 실패: {e}")
    
    conn.close()


def generate_recommendations():
    """문제 해결 권장사항 생성"""
    print("\n" + "=" * 80)
    print("💡 문제 해결 권장사항")
    print("=" * 80)
    
    print("""
[1] transaction_direction이 NULL이거나 잘못된 값인 경우:
    → sql/batch/update_direction_and_unknown.sql 실행
    → 또는 scripts/labeling/label_transaction_direction_fast_batch.py 재실행

[2] transaction_direction 값이 'exchange_inflow'/'exchange_outflow'가 아닌 경우:
    → scripts/labeling/post_process_labels.py의 is_exchange() 함수 확인
    → 거래소 라벨 매칭 로직 검토

[3] 집계 로직 문제:
    → scripts/subprojects/risk_ai/aggregate_whale_stats.py의 필터링 조건 확인
    → transaction_direction 필터링 로직 재검토

[4] 데이터 동기화 문제:
    → Supabase와 SQLite 간 데이터 동기화 확인
    → scripts/maintenance/sync_sqlite_to_supabase.py 실행

[5] 재집계 실행:
    → 문제 해결 후 aggregate_whale_stats.py --rebuild-all 실행
    """)


def main():
    """메인 실행"""
    print("=" * 80)
    print("🔍 거래소 유입/유출 데이터 진단 시작")
    print("=" * 80)
    
    # SQLite 진단
    diagnose_sqlite()
    
    # Supabase 진단
    diagnose_supabase()
    
    # 집계 로직 테스트
    test_aggregation_logic()
    
    # 권장사항
    generate_recommendations()
    
    print("\n" + "=" * 80)
    print("✅ 진단 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()

