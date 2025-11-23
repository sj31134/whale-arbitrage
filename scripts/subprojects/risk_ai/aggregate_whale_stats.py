#!/usr/bin/env python3
"""
내부 whale_transactions 데이터를 집계하여 bitinfocharts_whale 테이블을 채웁니다.
- top100_richest_pct -> 일별 고래 거래량 / 전체 고래 거래량 (정규화된 값)
- avg_transaction_value_btc -> 일별 고래 평균 거래 금액 (BTC)
"""

import os
import pandas as pd
import numpy as np
import time
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client, Client
try:
    from supabase.lib.client_options import ClientOptions
except ImportError:
    ClientOptions = None
from supabase.lib.client_options import ClientOptions

ROOT = Path(__file__).resolve().parent.parents[2]
env_path = ROOT / "config" / ".env"
print(f"Loading .env from: {env_path}")
load_dotenv(env_path, override=True)

# Supabase Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Local SQLite Connection
DB_PATH = ROOT / "data" / "project.db"

def get_sqlite_engine():
    return create_engine(f"sqlite:///{DB_PATH}")

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

if __name__ == "__main__":
    aggregate_whale_stats()

