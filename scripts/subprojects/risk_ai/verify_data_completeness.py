#!/usr/bin/env python3
"""
데이터 완전성 검증: binance_futures_metrics와 bitinfocharts_whale 데이터 매칭 확인
"""

import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"

def verify_data_completeness():
    print("=" * 80)
    print("🔍 데이터 완전성 검증")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. 각 테이블의 데이터 현황 확인
    print("\n1️⃣ 테이블별 데이터 현황")
    print("-" * 80)
    
    # binance_futures_metrics
    df_futures = pd.read_sql("""
        SELECT 
            COUNT(*) as total_count,
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(DISTINCT symbol) as symbol_count
        FROM binance_futures_metrics
        WHERE symbol = 'BTCUSDT'
    """, conn)
    
    print("\n📊 binance_futures_metrics (BTCUSDT):")
    print(f"   - 총 레코드: {df_futures['total_count'].iloc[0]:,}건")
    print(f"   - 기간: {df_futures['min_date'].iloc[0]} ~ {df_futures['max_date'].iloc[0]}")
    print(f"   - 심볼 수: {df_futures['symbol_count'].iloc[0]}개")
    
    # bitinfocharts_whale
    df_whale = pd.read_sql("""
        SELECT 
            COUNT(*) as total_count,
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(DISTINCT coin) as coin_count
        FROM bitinfocharts_whale
        WHERE coin = 'BTC'
    """, conn)
    
    print("\n🐋 bitinfocharts_whale (BTC):")
    print(f"   - 총 레코드: {df_whale['total_count'].iloc[0]:,}건")
    print(f"   - 기간: {df_whale['min_date'].iloc[0]} ~ {df_whale['max_date'].iloc[0]}")
    print(f"   - 코인 수: {df_whale['coin_count'].iloc[0]}개")
    
    # 2. 데이터 매칭 확인
    print("\n2️⃣ 데이터 매칭 확인")
    print("-" * 80)
    
    # JOIN 쿼리로 매칭되는 데이터 확인
    df_merged = pd.read_sql("""
        SELECT 
            f.date,
            f.symbol,
            f.avg_funding_rate,
            f.sum_open_interest,
            f.volatility_24h,
            b.top100_richest_pct,
            b.avg_transaction_value_btc
        FROM binance_futures_metrics f
        LEFT JOIN bitinfocharts_whale b 
            ON f.date = b.date AND b.coin = 'BTC'
        WHERE f.symbol = 'BTCUSDT'
        ORDER BY f.date
    """, conn)
    
    total_futures = len(df_merged)
    matched = df_merged['top100_richest_pct'].notna().sum()
    unmatched = total_futures - matched
    
    print(f"\n📈 매칭 통계:")
    print(f"   - binance_futures_metrics 총 레코드: {total_futures:,}건")
    print(f"   - bitinfocharts_whale와 매칭: {matched:,}건 ({matched/total_futures*100:.1f}%)")
    print(f"   - 매칭 안 됨: {unmatched:,}건 ({unmatched/total_futures*100:.1f}%)")
    
    # 3. 매칭되지 않은 날짜 확인
    if unmatched > 0:
        print("\n⚠️ 매칭되지 않은 날짜 (최근 10개):")
        unmatched_dates = df_merged[df_merged['top100_richest_pct'].isna()]['date'].head(10)
        for date in unmatched_dates:
            print(f"   - {date}")
    
    # 4. 결측치 확인
    print("\n3️⃣ 결측치 확인")
    print("-" * 80)
    
    print("\nbinance_futures_metrics 결측치 및 0값:")
    for col in ['avg_funding_rate', 'sum_open_interest', 'volatility_24h']:
        null_count = df_merged[col].isna().sum()
        zero_count = (df_merged[col] == 0).sum()
        non_zero_count = total_futures - null_count - zero_count
        print(f"   - {col}:")
        print(f"     * NULL: {null_count}건 ({null_count/total_futures*100:.1f}%)")
        print(f"     * 0값: {zero_count}건 ({zero_count/total_futures*100:.1f}%)")
        print(f"     * 유효값: {non_zero_count}건 ({non_zero_count/total_futures*100:.1f}%)")
        
        if non_zero_count > 0:
            valid_data = df_merged[df_merged[col] > 0][col]
            print(f"     * 평균: {valid_data.mean():.6f}")
            print(f"     * 최소: {valid_data.min():.6f}")
            print(f"     * 최대: {valid_data.max():.6f}")
    
    print("\nbitinfocharts_whale 결측치 (매칭된 데이터 중):")
    matched_df = df_merged[df_merged['top100_richest_pct'].notna()]
    if len(matched_df) > 0:
        for col in ['top100_richest_pct', 'avg_transaction_value_btc']:
            null_count = matched_df[col].isna().sum()
            print(f"   - {col}: {null_count}건 ({null_count/len(matched_df)*100:.1f}%)")
    
    # 5. 모델 학습 가능 여부 확인
    print("\n4️⃣ 모델 학습 가능 여부 확인")
    print("-" * 80)
    
    # 결측치 처리 후 데이터 확인
    df_clean = df_merged.copy()
    df_clean['date'] = pd.to_datetime(df_clean['date'])
    
    # Forward fill로 결측치 처리
    df_clean = df_clean.ffill().dropna()
    
    print(f"\n✅ 결측치 처리 후 데이터:")
    print(f"   - 총 레코드: {len(df_clean):,}건")
    print(f"   - 기간: {df_clean['date'].min().date()} ~ {df_clean['date'].max().date()}")
    
    # Train/Test Split 기준 확인
    split_date = pd.Timestamp("2024-10-01")
    train_count = len(df_clean[df_clean['date'] < split_date])
    test_count = len(df_clean[df_clean['date'] >= split_date])
    
    print(f"\n📊 Train/Test Split:")
    print(f"   - Train (2023-01-01 ~ 2024-09-30): {train_count:,}건")
    print(f"   - Test (2024-10-01 ~ 현재): {test_count:,}건")
    
    if train_count < 100:
        print(f"\n⚠️ 경고: 학습 데이터가 부족합니다 ({train_count}건 < 100건)")
    else:
        print(f"\n✅ 학습 데이터 충분: {train_count:,}건")
    
    if test_count < 10:
        print(f"⚠️ 경고: 테스트 데이터가 부족합니다 ({test_count}건 < 10건)")
    else:
        print(f"✅ 테스트 데이터 충분: {test_count:,}건")
    
    # 6. 샘플 데이터 확인
    print("\n5️⃣ 샘플 데이터 (최근 5일)")
    print("-" * 80)
    print(df_clean[['date', 'avg_funding_rate', 'sum_open_interest', 
                    'volatility_24h', 'top100_richest_pct', 'avg_transaction_value_btc']].tail(5).to_string(index=False))
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 검증 완료!")
    print("=" * 80)
    
    return {
        'total_futures': total_futures,
        'matched': matched,
        'unmatched': unmatched,
        'train_count': train_count,
        'test_count': test_count,
        'can_train': train_count >= 100 and test_count >= 10
    }

if __name__ == "__main__":
    verify_data_completeness()

