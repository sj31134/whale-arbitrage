#!/usr/bin/env python3
"""
일봉 선물 데이터를 주봉으로 집계하여 SQLite에 저장
- binance_futures_metrics (일봉) → binance_futures_weekly (주봉)
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"


def get_week_end_date(date_obj):
    """주봉 종료일 계산 (일요일)"""
    # 월요일 = 0, 일요일 = 6
    days_until_sunday = (6 - date_obj.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7  # 일요일이면 다음 주 일요일
    week_end = date_obj + timedelta(days=days_until_sunday)
    return week_end


def aggregate_futures_weekly(symbol="BTCUSDT", start_date="2022-08-11"):
    """일봉 선물 데이터를 주봉으로 집계"""
    print("=" * 80)
    print(f"📊 선물 데이터 주봉 집계 ({symbol})")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. 일봉 데이터 로드
    print(f"\n📥 일봉 데이터 로드 중...")
    query = """
        SELECT date, symbol, avg_funding_rate, sum_open_interest
        FROM binance_futures_metrics
        WHERE symbol = ?
        AND date >= ?
        ORDER BY date
    """
    
    df = pd.read_sql(query, conn, params=(symbol, start_date))
    
    if len(df) == 0:
        print(f"⚠️ {symbol} 일봉 데이터가 없습니다.")
        conn.close()
        return
    
    print(f"   ✅ {len(df)}일 데이터 로드 완료")
    print(f"   기간: {df['date'].min()} ~ {df['date'].max()}")
    
    df['date'] = pd.to_datetime(df['date'])
    
    # 2. 주 종료일 계산 (일요일)
    print(f"\n📅 주 종료일 계산 중...")
    df['week_end'] = df['date'].apply(get_week_end_date)
    
    # 3. 주별 집계
    print(f"\n📊 주별 집계 중...")
    weekly_df = df.groupby(['week_end', 'symbol']).agg({
        'avg_funding_rate': 'mean',  # 주간 평균 펀딩비
        'sum_open_interest': 'last'   # 주 종료일 OI (현재 시점 반영)
    }).reset_index()
    
    weekly_df = weekly_df.rename(columns={'week_end': 'week_end_date'})
    
    # 4. OI 성장률 계산 (전주 대비)
    print(f"   OI 성장률 계산 중...")
    weekly_df['oi_growth_7d'] = weekly_df.groupby('symbol')['sum_open_interest'].pct_change()
    
    # 5. 펀딩비 Z-Score 계산 (30주 롤링 윈도우)
    print(f"   펀딩비 Z-Score 계산 중...")
    weekly_df = weekly_df.sort_values('week_end_date')
    
    # 30주 롤링 윈도우로 평균/표준편차 계산
    weekly_df['funding_rate_mean'] = weekly_df.groupby('symbol')['avg_funding_rate'].rolling(
        window=30, min_periods=1
    ).mean().reset_index(0, drop=True)
    
    weekly_df['funding_rate_std'] = weekly_df.groupby('symbol')['avg_funding_rate'].rolling(
        window=30, min_periods=1
    ).std().reset_index(0, drop=True)
    
    # Z-Score 계산 (표준편차가 0이면 0으로 설정)
    weekly_df['funding_rate_zscore'] = np.where(
        weekly_df['funding_rate_std'] > 0,
        (weekly_df['avg_funding_rate'] - weekly_df['funding_rate_mean']) / weekly_df['funding_rate_std'],
        0.0
    )
    
    # 불필요한 컬럼 제거
    weekly_df = weekly_df.drop(columns=['funding_rate_mean', 'funding_rate_std'])
    
    # 결측치 처리
    weekly_df['oi_growth_7d'] = weekly_df['oi_growth_7d'].fillna(0.0)
    weekly_df['funding_rate_zscore'] = weekly_df['funding_rate_zscore'].fillna(0.0)
    
    print(f"   ✅ {len(weekly_df)}주 데이터 집계 완료")
    
    # 6. SQLite에 저장
    print(f"\n💾 SQLite 저장 중...")
    cursor = conn.cursor()
    
    # 테이블 생성 (없으면)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS binance_futures_weekly (
            symbol VARCHAR(20) NOT NULL,
            week_end_date DATE NOT NULL,
            avg_funding_rate DECIMAL(20, 10),
            sum_open_interest DECIMAL(30, 10),
            oi_growth_7d DECIMAL(10, 6),
            funding_rate_zscore DECIMAL(10, 6),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (symbol, week_end_date)
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_futures_weekly_symbol 
        ON binance_futures_weekly(symbol)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_futures_weekly_date 
        ON binance_futures_weekly(week_end_date)
    """)
    
    conn.commit()
    
    # 데이터 저장 (INSERT OR REPLACE)
    saved_count = 0
    for _, row in weekly_df.iterrows():
        cursor.execute("""
            INSERT OR REPLACE INTO binance_futures_weekly 
            (symbol, week_end_date, avg_funding_rate, sum_open_interest, 
             oi_growth_7d, funding_rate_zscore)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            row['symbol'],
            row['week_end_date'].strftime('%Y-%m-%d'),
            float(row['avg_funding_rate']) if pd.notna(row['avg_funding_rate']) else None,
            float(row['sum_open_interest']) if pd.notna(row['sum_open_interest']) else None,
            float(row['oi_growth_7d']) if pd.notna(row['oi_growth_7d']) else 0.0,
            float(row['funding_rate_zscore']) if pd.notna(row['funding_rate_zscore']) else 0.0
        ))
        saved_count += 1
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"   ✅ {saved_count}주 데이터 저장 완료")
    
    # 7. 결과 요약
    print(f"\n📊 집계 결과 요약:")
    print(f"   주간 평균 펀딩비: {weekly_df['avg_funding_rate'].mean():.6f}")
    print(f"   주간 평균 OI: {weekly_df['sum_open_interest'].mean():,.0f}")
    print(f"   OI 성장률 평균: {weekly_df['oi_growth_7d'].mean():.4f}")
    print(f"   펀딩비 Z-Score 평균: {weekly_df['funding_rate_zscore'].mean():.2f}")


def main():
    print("=" * 80)
    print("📊 선물 데이터 주봉 집계")
    print("=" * 80)
    
    # BTC와 ETH 모두 집계
    for symbol in ["BTCUSDT", "ETHUSDT"]:
        try:
            aggregate_futures_weekly(symbol, start_date="2022-08-11")
            print()
        except Exception as e:
            print(f"⚠️ {symbol} 집계 중 오류: {e}")
            print()
    
    print("=" * 80)
    print("✅ 선물 데이터 주봉 집계 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()


