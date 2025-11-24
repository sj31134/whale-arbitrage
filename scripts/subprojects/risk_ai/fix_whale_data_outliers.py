#!/usr/bin/env python3
"""
고래 데이터 이상치 처리 및 정제
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"

def fix_whale_data_outliers():
    print("=" * 80)
    print("🔧 고래 데이터 이상치 처리")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. 현재 데이터 로드
    print("\n📥 데이터 로드 중...")
    df = pd.read_sql("""
        SELECT 
            date,
            coin,
            top100_richest_pct,
            avg_transaction_value_btc
        FROM bitinfocharts_whale
        WHERE coin = 'BTC'
        ORDER BY date
    """, conn)
    
    print(f"   총 레코드: {len(df):,}건")
    
    # 2. 이상치 탐지 및 처리
    print("\n🔍 이상치 탐지 중...")
    
    # top100_richest_pct 이상치 처리
    # 정상 범위: 0% ~ 100% (비율이므로 100% 초과는 명백한 오류)
    # IQR 방법으로도 탐지
    Q1_pct = df['top100_richest_pct'].quantile(0.25)
    Q3_pct = df['top100_richest_pct'].quantile(0.75)
    IQR_pct = Q3_pct - Q1_pct
    upper_bound_pct = Q3_pct + 1.5 * IQR_pct
    
    # 100% 초과는 명백한 오류로 처리
    extreme_outliers_pct = df['top100_richest_pct'] > 100
    outliers_pct = df['top100_richest_pct'] > min(100, upper_bound_pct)
    
    print(f"\n   top100_richest_pct:")
    print(f"   - 극단적 이상치 (>100%): {extreme_outliers_pct.sum()}건")
    print(f"   - IQR 이상치: {outliers_pct.sum()}건")
    
    # avg_transaction_value_btc 이상치 처리
    # 정상 범위: 0 ~ 합리적 최대값 (예: 10,000 BTC)
    Q1_tx = df['avg_transaction_value_btc'].quantile(0.25)
    Q3_tx = df['avg_transaction_value_btc'].quantile(0.75)
    IQR_tx = Q3_tx - Q1_tx
    upper_bound_tx = Q3_tx + 1.5 * IQR_tx
    
    # 10,000 BTC 초과는 명백한 오류로 처리
    extreme_outliers_tx = df['avg_transaction_value_btc'] > 10000
    outliers_tx = df['avg_transaction_value_btc'] > min(10000, upper_bound_tx)
    
    print(f"\n   avg_transaction_value_btc:")
    print(f"   - 극단적 이상치 (>10,000 BTC): {extreme_outliers_tx.sum()}건")
    print(f"   - IQR 이상치: {outliers_tx.sum()}건")
    
    # 3. 이상치 처리 방법 선택
    print("\n🔧 이상치 처리 방법:")
    print("   1. Forward Fill (전일 값으로 대체)")
    print("   2. 중앙값으로 대체")
    print("   3. 상한선으로 제한 (Clipping)")
    print("   4. 삭제 후 Forward Fill")
    
    # 방법: Forward Fill (시계열 데이터이므로)
    df_fixed = df.copy()
    
    # top100_richest_pct 처리
    # 100% 초과는 100%로 제한, 그 외 이상치는 Forward Fill
    df_fixed.loc[extreme_outliers_pct, 'top100_richest_pct'] = 100.0
    df_fixed.loc[outliers_pct & ~extreme_outliers_pct, 'top100_richest_pct'] = np.nan
    df_fixed['top100_richest_pct'] = df_fixed['top100_richest_pct'].ffill()
    
    # avg_transaction_value_btc 처리
    # 10,000 BTC 초과는 99% 분위수로 제한, 그 외 이상치는 Forward Fill
    p99_tx = df['avg_transaction_value_btc'].quantile(0.99)
    df_fixed.loc[extreme_outliers_tx, 'avg_transaction_value_btc'] = p99_tx
    df_fixed.loc[outliers_tx & ~extreme_outliers_tx, 'avg_transaction_value_btc'] = np.nan
    df_fixed['avg_transaction_value_btc'] = df_fixed['avg_transaction_value_btc'].ffill()
    
    # 0값 처리 (avg_transaction_value_btc만)
    # 0값도 Forward Fill로 처리
    zero_mask = df_fixed['avg_transaction_value_btc'] == 0
    df_fixed.loc[zero_mask, 'avg_transaction_value_btc'] = np.nan
    df_fixed['avg_transaction_value_btc'] = df_fixed['avg_transaction_value_btc'].ffill()
    
    # Forward Fill로 채워지지 않은 값은 중앙값으로
    if df_fixed['top100_richest_pct'].isna().sum() > 0:
        median_pct = df['top100_richest_pct'].median()
        df_fixed['top100_richest_pct'] = df_fixed['top100_richest_pct'].fillna(median_pct)
    
    if df_fixed['avg_transaction_value_btc'].isna().sum() > 0:
        median_tx = df['avg_transaction_value_btc'].median()
        df_fixed['avg_transaction_value_btc'] = df_fixed['avg_transaction_value_btc'].fillna(median_tx)
    
    # 4. 처리 결과 확인
    print("\n📊 처리 결과:")
    print(f"   top100_richest_pct:")
    print(f"     - 최소: {df_fixed['top100_richest_pct'].min():.2f}%")
    print(f"     - 최대: {df_fixed['top100_richest_pct'].max():.2f}%")
    print(f"     - 평균: {df_fixed['top100_richest_pct'].mean():.2f}%")
    
    print(f"\n   avg_transaction_value_btc:")
    print(f"     - 최소: {df_fixed['avg_transaction_value_btc'].min():.2f} BTC")
    print(f"     - 최대: {df_fixed['avg_transaction_value_btc'].max():.2f} BTC")
    print(f"     - 평균: {df_fixed['avg_transaction_value_btc'].mean():.2f} BTC")
    
    # 5. DB 업데이트
    print("\n💾 DB 업데이트 중...")
    cursor = conn.cursor()
    
    updated_count = 0
    for _, row in df_fixed.iterrows():
        cursor.execute("""
            UPDATE bitinfocharts_whale
            SET top100_richest_pct = ?,
                avg_transaction_value_btc = ?
            WHERE date = ? AND coin = ?
        """, (
            row['top100_richest_pct'],
            row['avg_transaction_value_btc'],
            row['date'],
            row['coin']
        ))
        updated_count += 1
    
    conn.commit()
    print(f"   ✅ {updated_count}건 업데이트 완료")
    
    # 6. 변경 사항 요약
    print("\n📋 변경 사항 요약:")
    changed_pct = (df['top100_richest_pct'] != df_fixed['top100_richest_pct']).sum()
    changed_tx = (df['avg_transaction_value_btc'] != df_fixed['avg_transaction_value_btc']).sum()
    
    print(f"   top100_richest_pct 변경: {changed_pct}건")
    print(f"   avg_transaction_value_btc 변경: {changed_tx}건")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 이상치 처리 완료!")
    print("=" * 80)

if __name__ == "__main__":
    fix_whale_data_outliers()

