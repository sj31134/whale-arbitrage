#!/usr/bin/env python3
"""
내부 whale_transactions 데이터를 집계하여 온체인 지표를 생성합니다.

확장된 기능:
- bitinfocharts_whale: 일별 고래 거래량, 평균 거래 금액
- whale_daily_stats: 일별 거래소 유입/유출량, 순유입, 활성 주소 수, 대형 거래 건수
- whale_weekly_stats: 주별 집계 데이터
"""

import os
import pandas as pd
import numpy as np
import time
import sqlite3
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client, Client
try:
    from supabase.lib.client_options import ClientOptions
except ImportError:
    ClientOptions = None

ROOT = Path(__file__).resolve().parent.parents[2]
env_path = ROOT / "config" / ".env"
print(f"Loading .env from: {env_path}")
load_dotenv(env_path, override=True)

# Supabase Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Local SQLite Connection
DB_PATH = ROOT / "data" / "project.db"

# 대형 거래 기준 (USD)
LARGE_TX_THRESHOLD_USD = 100000  # $100,000 이상

def get_sqlite_engine():
    return create_engine(f"sqlite:///{DB_PATH}")


def ensure_tables():
    """필요한 테이블이 없으면 생성"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # whale_daily_stats 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whale_daily_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            coin_symbol VARCHAR(20) NOT NULL,
            exchange_inflow_usd DECIMAL(30, 8),
            exchange_outflow_usd DECIMAL(30, 8),
            net_flow_usd DECIMAL(30, 8),
            whale_to_whale_usd DECIMAL(30, 8),
            active_addresses INTEGER,
            large_tx_count INTEGER,
            avg_tx_size_usd DECIMAL(20, 8),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, coin_symbol)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whale_daily_date ON whale_daily_stats(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_whale_daily_coin ON whale_daily_stats(coin_symbol)")
    
    # whale_weekly_stats 테이블 (이미 있을 수 있음)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS whale_weekly_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            coin_symbol VARCHAR(20) NOT NULL,
            net_inflow_usd DECIMAL(30, 8),
            exchange_inflow_usd DECIMAL(30, 8),
            active_addresses INTEGER,
            transaction_count INTEGER,
            avg_buy_price DECIMAL(20, 8),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, coin_symbol)
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()


def fetch_whale_transactions_with_direction(supabase, start_date, end_date, coin_symbols=None):
    """
    whale_transactions에서 거래 방향(transaction_direction) 포함하여 데이터 가져오기
    """
    if coin_symbols is None:
        coin_symbols = ["BTC", "ETH", "BNB"]
    
    all_txs = []
    current_start = start_date
    
    while current_start < end_date:
        current_end = current_start + pd.DateOffset(months=1)
        start_str = current_start.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = current_end.strftime("%Y-%m-%dT%H:%M:%S")
        
        print(f"  📅 {start_str[:10]} ~ {end_str[:10]} 조회 중...")
        
        offset = 0
        limit = 1000
        
        while True:
            try:
                response = supabase.table("whale_transactions") \
                    .select("block_timestamp, amount, amount_usd, coin_symbol, from_address, to_address, transaction_direction") \
                    .gte("block_timestamp", start_str) \
                    .lt("block_timestamp", end_str) \
                    .in_("coin_symbol", coin_symbols) \
                    .range(offset, offset + limit - 1) \
                    .execute()
                
                data = response.data
                if not data:
                    break
                    
                all_txs.extend(data)
                offset += limit
                
                if len(data) < limit:
                    break
                    
                time.sleep(0.1)
                
            except Exception as e:
                print(f"  ❌ 오류 발생: {e}")
                break
        
        current_start = current_end
    
    return all_txs


def aggregate_daily_whale_stats(supabase, start_date, end_date):
    """
    일별 고래 통계 집계:
    - 거래소 유입/유출량
    - 순유입
    - 고래간 거래량
    - 활성 주소 수
    - 대형 거래 건수
    """
    print("\n📊 일별 고래 통계 집계 중...")
    
    all_txs = fetch_whale_transactions_with_direction(supabase, start_date, end_date)
    
    if not all_txs:
        print("⚠️ 데이터 없음")
        return
    
    df = pd.DataFrame(all_txs)
    df['block_timestamp'] = pd.to_datetime(df['block_timestamp'])
    df['date'] = df['block_timestamp'].dt.date
    df['amount_usd'] = pd.to_numeric(df['amount_usd'], errors='coerce').fillna(0)
    
    # 거래 방향별 집계
    results = []
    
    for coin in df['coin_symbol'].unique():
        coin_df = df[df['coin_symbol'] == coin]
        
        for date in coin_df['date'].unique():
            day_df = coin_df[coin_df['date'] == date]
            
            # 거래소 유입 (exchange_inflow)
            inflow_df = day_df[day_df['transaction_direction'] == 'exchange_inflow']
            exchange_inflow = inflow_df['amount_usd'].sum()
            
            # 거래소 유출 (exchange_outflow)
            outflow_df = day_df[day_df['transaction_direction'] == 'exchange_outflow']
            exchange_outflow = outflow_df['amount_usd'].sum()
            
            # 순유입
            net_flow = exchange_inflow - exchange_outflow
            
            # 고래간 거래 (whale_to_whale)
            w2w_df = day_df[day_df['transaction_direction'] == 'whale_to_whale']
            whale_to_whale = w2w_df['amount_usd'].sum()
            
            # 활성 주소 수 (from + to 유니크)
            active_from = set(day_df['from_address'].dropna().unique())
            active_to = set(day_df['to_address'].dropna().unique())
            active_addresses = len(active_from | active_to)
            
            # 대형 거래 건수 ($100K 이상)
            large_tx_count = len(day_df[day_df['amount_usd'] >= LARGE_TX_THRESHOLD_USD])
            
            # 평균 거래 크기
            avg_tx_size = day_df['amount_usd'].mean() if len(day_df) > 0 else 0
            
            results.append({
                'date': date,
                'coin_symbol': coin,
                'exchange_inflow_usd': exchange_inflow,
                'exchange_outflow_usd': exchange_outflow,
                'net_flow_usd': net_flow,
                'whale_to_whale_usd': whale_to_whale,
                'active_addresses': active_addresses,
                'large_tx_count': large_tx_count,
                'avg_tx_size_usd': avg_tx_size
            })
    
    # SQLite에 저장
    if results:
        sqlite_engine = get_sqlite_engine()
        
        with sqlite_engine.connect() as conn:
            for row in results:
                sql = text("""
                    INSERT OR REPLACE INTO whale_daily_stats 
                    (date, coin_symbol, exchange_inflow_usd, exchange_outflow_usd, 
                     net_flow_usd, whale_to_whale_usd, active_addresses, 
                     large_tx_count, avg_tx_size_usd)
                    VALUES (:date, :coin_symbol, :exchange_inflow_usd, :exchange_outflow_usd,
                            :net_flow_usd, :whale_to_whale_usd, :active_addresses,
                            :large_tx_count, :avg_tx_size_usd)
                """)
                conn.execute(sql, {
                    "date": row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                    "coin_symbol": row['coin_symbol'],
                    "exchange_inflow_usd": row['exchange_inflow_usd'],
                    "exchange_outflow_usd": row['exchange_outflow_usd'],
                    "net_flow_usd": row['net_flow_usd'],
                    "whale_to_whale_usd": row['whale_to_whale_usd'],
                    "active_addresses": row['active_addresses'],
                    "large_tx_count": row['large_tx_count'],
                    "avg_tx_size_usd": row['avg_tx_size_usd']
                })
            conn.commit()
        
        print(f"✅ {len(results)}건의 일별 통계 저장 완료")
    
    return results


def aggregate_weekly_whale_stats():
    """
    whale_daily_stats를 기반으로 주별 집계
    """
    print("\n📊 주별 고래 통계 집계 중...")
    
    sqlite_engine = get_sqlite_engine()
    
    # 일별 데이터 로드
    query = """
        SELECT date, coin_symbol, exchange_inflow_usd, exchange_outflow_usd,
               net_flow_usd, active_addresses, large_tx_count
        FROM whale_daily_stats
        ORDER BY date
    """
    
    df = pd.read_sql(query, sqlite_engine)
    
    if df.empty:
        print("⚠️ 일별 데이터 없음")
        return
    
    df['date'] = pd.to_datetime(df['date'])
    df['week_start'] = df['date'] - pd.to_timedelta(df['date'].dt.dayofweek, unit='D')
    
    # 주별 집계
    weekly_df = df.groupby(['week_start', 'coin_symbol']).agg({
        'exchange_inflow_usd': 'sum',
        'net_flow_usd': 'sum',
        'active_addresses': 'mean',  # 평균 활성 주소
        'large_tx_count': 'sum'
    }).reset_index()
    
    weekly_df.columns = ['date', 'coin_symbol', 'exchange_inflow_usd', 'net_inflow_usd', 
                         'active_addresses', 'transaction_count']
    
    # SQLite에 저장
    with sqlite_engine.connect() as conn:
        for _, row in weekly_df.iterrows():
            sql = text("""
                INSERT OR REPLACE INTO whale_weekly_stats 
                (date, coin_symbol, net_inflow_usd, exchange_inflow_usd, 
                 active_addresses, transaction_count)
                VALUES (:date, :coin_symbol, :net_inflow_usd, :exchange_inflow_usd,
                        :active_addresses, :transaction_count)
            """)
            conn.execute(sql, {
                "date": row['date'].strftime('%Y-%m-%d'),
                "coin_symbol": row['coin_symbol'],
                "net_inflow_usd": row['net_inflow_usd'],
                "exchange_inflow_usd": row['exchange_inflow_usd'],
                "active_addresses": int(row['active_addresses']),
                "transaction_count": int(row['transaction_count'])
            })
        conn.commit()
    
    print(f"✅ {len(weekly_df)}건의 주별 통계 저장 완료")

def aggregate_whale_stats():
    # 환경 변수 로드 디버깅
    print(f"DEBUG: SUPABASE_URL={os.getenv('SUPABASE_URL') is not None}")
    print(f"DEBUG: SUPABASE_KEY={os.getenv('SUPABASE_KEY') is not None}")
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    print("🔄 고래 활동 지표 집계 중 (Source: Supabase whale_transactions)...")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase 설정 오류: .env 파일 확인 필요")
        # 하드코딩이나 대체 방법 시도 (보안상 비권장)
        return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Supabase REST API (PostgREST)로 집계 쿼리는 어려움 (RPC 사용 권장)
    # 하지만 여기서는 간단하게 RPC 함수를 호출하거나, 
    # 또는 데이터를 일별로 가져와서 Pandas로 집계 (데이터 양이 많으면 비효율적일 수 있음)
    
    # 가장 좋은 방법: SQL 함수(RPC)를 만들고 호출
    # 차선책: Raw SQL 실행 (supabase-py에서는 rpc로 실행하거나 client.table().select() 사용)
    
    # 여기서는 supabase-py로 직접 쿼리 실행이 제한적이므로,
    # 'whale_transactions'에서 필요한 컬럼만 가져와서 Pandas로 처리 (배치 처리)
    
    # 1. 데이터 가져오기 (월별 분할 수집)
    all_txs = []
    
    # 수집 기간 설정 (2023-01 ~ 현재)
    start_date = pd.Timestamp("2023-01-01")
    end_date = pd.Timestamp.now()
    
    current_start = start_date
    
    print("📥 월별 데이터 다운로드 중...")
    
    while current_start < end_date:
        current_end = current_start + pd.DateOffset(months=1)
        start_str = current_start.strftime("%Y-%m-%dT%H:%M:%S")
        end_str = current_end.strftime("%Y-%m-%dT%H:%M:%S")
        
        print(f"  📅 {start_str} ~ {end_str} 조회 중...")
        
        offset = 0
        limit = 1000 # 월 단위로 끊으면 1000개씩 가져와도 괜찮을 수 있음
        
        while True:
            try:
                response = supabase.table("whale_transactions") \
                    .select("block_timestamp, amount, coin_symbol") \
                    .gte("block_timestamp", start_str) \
                    .lt("block_timestamp", end_str) \
                    .in_("coin_symbol", ["BTC", "WBTC"]) \
                    .range(offset, offset + limit - 1) \
                    .execute()
                
                data = response.data
                if not data:
                    break
                    
                all_txs.extend(data)
                offset += limit
                
                if len(data) < limit:
                    break
                    
                time.sleep(0.1) # Rate limit
                
            except Exception as e:
                print(f"  ❌ 오류 발생 ({start_str}): {e}")
                # 해당 월 건너뛰고 다음으로 진행 (또는 재시도)
                break
        
        current_start = current_end
        print(f"  => 누적 {len(all_txs)}건")

    if not all_txs:
        print("⚠️ BTC 데이터 없음. ETH 데이터로 시도...")
        # ETH 시도 로직 추가 가능 (생략)
        return

    df = pd.DataFrame(all_txs)
    df['block_timestamp'] = pd.to_datetime(df['block_timestamp'])
    df['date'] = df['block_timestamp'].dt.date
    df['amount'] = pd.to_numeric(df['amount'])
    
    # 2. 집계
    agg_df = df.groupby('date').agg(
        tx_count=('amount', 'count'),
        total_volume=('amount', 'sum'),
        avg_tx_value=('amount', 'mean')
    ).reset_index()
    
    agg_df['coin'] = 'BTC'
    
    print(f"📊 {len(agg_df)}일치 데이터 집계 완료")
    
    # 3. 지표 가공 및 저장
    max_vol = agg_df['total_volume'].max()
    if max_vol == 0: max_vol = 1
    
    agg_df['top100_richest_pct'] = (agg_df['total_volume'] / max_vol) * 100
    agg_df['avg_transaction_value_btc'] = agg_df['avg_tx_value']
    
    sqlite_engine = get_sqlite_engine()
    
    with sqlite_engine.connect() as conn:
        for _, row in agg_df.iterrows():
            sql = text("""
                INSERT OR REPLACE INTO bitinfocharts_whale 
                (date, coin, top100_richest_pct, avg_transaction_value_btc)
                VALUES (:date, :coin, :pct, :avg_val)
            """)
            conn.execute(sql, {
                "date": row['date'].strftime('%Y-%m-%d'),
                "coin": row['coin'],
                "pct": row['top100_richest_pct'],
                "avg_val": row['avg_transaction_value_btc']
            })
        conn.commit()
        
    print("✅ SQLite 저장 완료")

def run_full_aggregation():
    """전체 집계 실행"""
    print("=" * 80)
    print("📊 고래 활동 지표 전체 집계")
    print("=" * 80)
    
    ensure_tables()
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Supabase 설정 오류: .env 파일 확인 필요")
        return
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 수집 기간 설정
    start_date = pd.Timestamp("2023-01-01")
    end_date = pd.Timestamp.now()
    
    # 1. 기존 bitinfocharts_whale 집계
    print("\n[1/3] bitinfocharts_whale 집계...")
    aggregate_whale_stats()
    
    # 2. 일별 고래 통계 집계
    print("\n[2/3] 일별 고래 통계 집계...")
    aggregate_daily_whale_stats(supabase, start_date, end_date)
    
    # 3. 주별 고래 통계 집계
    print("\n[3/3] 주별 고래 통계 집계...")
    aggregate_weekly_whale_stats()
    
    print("\n" + "=" * 80)
    print("✅ 전체 집계 완료!")
    print("=" * 80)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        run_full_aggregation()
    else:
        aggregate_whale_stats()

