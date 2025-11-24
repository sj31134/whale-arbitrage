#!/usr/bin/env python3
"""
whale_transactions.csv를 SQLite bitinfocharts_whale 테이블로 변환 및 저장
- 시간별 집계 데이터 → 일별 집계
- top100_richest_pct: 일별 거래량 정규화 (최대값 대비 백분율)
- avg_transaction_value_btc: 일별 평균 거래 금액
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"
CSV_PATH = ROOT / "data" / "exports" / "whale_transactions.csv"

def get_sqlite_engine():
    return create_engine(f"sqlite:///{DB_PATH}")

def import_whale_transactions():
    print("=" * 80)
    print("🔄 whale_transactions.csv → bitinfocharts_whale 변환 시작")
    print("=" * 80)
    
    # 1. CSV 파일 로드
    print(f"\n📥 CSV 파일 로드 중: {CSV_PATH}")
    if not CSV_PATH.exists():
        print(f"❌ 파일을 찾을 수 없습니다: {CSV_PATH}")
        return
    
    df = pd.read_csv(CSV_PATH)
    print(f"   ✅ {len(df):,}줄 로드 완료")
    
    # 2. 시간 파싱 및 일별 집계
    print("\n📊 일별 집계 중...")
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce')
    df = df.dropna(subset=['Time'])
    df['date'] = df['Time'].dt.date
    
    # 일별 집계
    daily_df = df.groupby('date').agg({
        'frequency': 'sum',      # 일별 총 거래 횟수
        'sum_amount': 'sum',     # 일별 총 거래량
        'sum_amount_usd': 'sum'  # 일별 총 USD 가치
    }).reset_index()
    
    # 평균 거래 금액 계산 (거래량 / 거래 횟수)
    daily_df['avg_transaction_value_btc'] = daily_df['sum_amount'] / daily_df['frequency']
    daily_df['avg_transaction_value_btc'] = daily_df['avg_transaction_value_btc'].fillna(0)
    
    # top100_richest_pct 계산 (일별 거래량을 최대값 대비 백분율로 정규화)
    max_volume = daily_df['sum_amount'].max()
    if max_volume == 0:
        max_volume = 1
    
    daily_df['top100_richest_pct'] = (daily_df['sum_amount'] / max_volume) * 100
    
    # coin 컬럼 추가 (BTC로 가정)
    daily_df['coin'] = 'BTC'
    
    print(f"   ✅ {len(daily_df)}일치 데이터 집계 완료")
    print(f"\n📈 집계 통계:")
    print(f"   - 기간: {daily_df['date'].min()} ~ {daily_df['date'].max()}")
    print(f"   - 총 거래량: {daily_df['sum_amount'].sum():,.2f}")
    print(f"   - 평균 일별 거래량: {daily_df['sum_amount'].mean():,.2f}")
    print(f"   - 평균 일별 거래 횟수: {daily_df['frequency'].mean():.1f}")
    print(f"   - 평균 거래 금액: {daily_df['avg_transaction_value_btc'].mean():,.2f} BTC")
    
    # 3. SQLite에 저장
    print("\n💾 SQLite 저장 중...")
    sqlite_engine = get_sqlite_engine()
    
    saved_count = 0
    with sqlite_engine.connect() as conn:
        for _, row in daily_df.iterrows():
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
            saved_count += 1
        conn.commit()
    
    print(f"   ✅ {saved_count}건 저장 완료")
    
    # 4. 저장 결과 확인
    print("\n🔍 저장 결과 확인...")
    with sqlite_engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM bitinfocharts_whale WHERE coin = 'BTC'"))
        total_count = result.scalar()
        print(f"   - bitinfocharts_whale 테이블의 BTC 데이터: {total_count}건")
        
        result = conn.execute(text("""
            SELECT MIN(date), MAX(date) 
            FROM bitinfocharts_whale 
            WHERE coin = 'BTC'
        """))
        min_date, max_date = result.fetchone()
        print(f"   - 데이터 기간: {min_date} ~ {max_date}")
    
    print("\n" + "=" * 80)
    print("✅ 변환 완료!")
    print("=" * 80)

if __name__ == "__main__":
    import_whale_transactions()

