#!/usr/bin/env python3
"""
프로젝트 3 데이터 품질 분석 및 문제점 진단
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"

def analyze_data_quality():
    print("=" * 80)
    print("📊 프로젝트 3 데이터 품질 분석")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. 데이터 기간 비교
    print("\n1️⃣ 데이터 기간 비교")
    print("-" * 80)
    
    df_futures = pd.read_sql("""
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(*) as total_count,
            SUM(CASE WHEN sum_open_interest > 0 THEN 1 ELSE 0 END) as oi_count,
            SUM(CASE WHEN volatility_24h > 0 THEN 1 ELSE 0 END) as vol_count
        FROM binance_futures_metrics
        WHERE symbol = 'BTCUSDT'
    """, conn)
    
    df_whale = pd.read_sql("""
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(*) as total_count
        FROM bitinfocharts_whale
        WHERE coin = 'BTC'
    """, conn)
    
    print(f"\n📊 binance_futures_metrics:")
    print(f"   기간: {df_futures['min_date'].iloc[0]} ~ {df_futures['max_date'].iloc[0]}")
    print(f"   총 레코드: {df_futures['total_count'].iloc[0]:,}건")
    print(f"   OI > 0: {df_futures['oi_count'].iloc[0]:,}건 ({df_futures['oi_count'].iloc[0]/df_futures['total_count'].iloc[0]*100:.1f}%)")
    print(f"   Volatility > 0: {df_futures['vol_count'].iloc[0]:,}건 ({df_futures['vol_count'].iloc[0]/df_futures['total_count'].iloc[0]*100:.1f}%)")
    
    print(f"\n🐋 bitinfocharts_whale:")
    print(f"   기간: {df_whale['min_date'].iloc[0]} ~ {df_whale['max_date'].iloc[0]}")
    print(f"   총 레코드: {df_whale['total_count'].iloc[0]:,}건")
    
    # OI 데이터 기간 확인
    df_oi_dates = pd.read_sql("""
        SELECT date, sum_open_interest
        FROM binance_futures_metrics
        WHERE symbol = 'BTCUSDT' AND sum_open_interest > 0
        ORDER BY date
    """, conn)
    
    if len(df_oi_dates) > 0:
        print(f"\n   ⚠️ OI 데이터 기간:")
        print(f"   시작: {df_oi_dates['date'].min()}")
        print(f"   종료: {df_oi_dates['date'].max()}")
        print(f"   일수: {len(df_oi_dates)}일 (매우 부족!)")
        print(f"   다른 데이터 대비: {df_futures['total_count'].iloc[0] - len(df_oi_dates):,}일 부족")
    
    # 2. 고래 데이터 이상치 분석
    print("\n2️⃣ 고래 데이터 이상치 분석")
    print("-" * 80)
    
    df_whale = pd.read_sql("""
        SELECT 
            date,
            top100_richest_pct,
            avg_transaction_value_btc
        FROM bitinfocharts_whale
        WHERE coin = 'BTC'
        ORDER BY date
    """, conn)
    
    df_whale['date'] = pd.to_datetime(df_whale['date'])
    
    # IQR 방법으로 이상치 탐지
    def detect_outliers_iqr(series):
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        return (series < lower_bound) | (series > upper_bound), lower_bound, upper_bound
    
    # top100_richest_pct 이상치
    outliers_pct, lb_pct, ub_pct = detect_outliers_iqr(df_whale['top100_richest_pct'])
    print(f"\n   top100_richest_pct:")
    print(f"   - 정상 범위: {lb_pct:.2f}% ~ {ub_pct:.2f}%")
    print(f"   - 이상치 개수: {outliers_pct.sum()}건 ({outliers_pct.sum()/len(df_whale)*100:.1f}%)")
    
    if outliers_pct.sum() > 0:
        print(f"\n   ⚠️ 이상치 샘플:")
        outlier_data = df_whale[outliers_pct].nlargest(5, 'top100_richest_pct')[['date', 'top100_richest_pct']]
        for _, row in outlier_data.iterrows():
            print(f"     {row['date'].date()}: {row['top100_richest_pct']:.2f}% (정상 범위 초과)")
            if row['top100_richest_pct'] > 100:
                print(f"       ⚠️ 100% 초과 - 명백한 오류 가능성!")
    
    # avg_transaction_value_btc 이상치
    outliers_tx, lb_tx, ub_tx = detect_outliers_iqr(df_whale['avg_transaction_value_btc'])
    print(f"\n   avg_transaction_value_btc:")
    print(f"   - 정상 범위: {lb_tx:.2f} ~ {ub_tx:.2f} BTC")
    print(f"   - 이상치 개수: {outliers_tx.sum()}건 ({outliers_tx.sum()/len(df_whale)*100:.1f}%)")
    
    if outliers_tx.sum() > 0:
        print(f"\n   ⚠️ 이상치 샘플 (상위 5개):")
        outlier_data = df_whale[outliers_tx].nlargest(5, 'avg_transaction_value_btc')[['date', 'avg_transaction_value_btc']]
        for _, row in outlier_data.iterrows():
            print(f"     {row['date'].date()}: {row['avg_transaction_value_btc']:.2f} BTC (정상 범위 초과)")
            if row['avg_transaction_value_btc'] > 10000:
                print(f"       ⚠️ 10,000 BTC 초과 - 명백한 오류 가능성!")
    
    # 0값 분석
    print(f"\n3️⃣ 0값 및 결측치 분석")
    print("-" * 80)
    
    zero_pct = (df_whale['top100_richest_pct'] == 0).sum()
    zero_tx = (df_whale['avg_transaction_value_btc'] == 0).sum()
    
    print(f"   top100_richest_pct = 0: {zero_pct}건 ({zero_pct/len(df_whale)*100:.1f}%)")
    print(f"   avg_transaction_value_btc = 0: {zero_tx}건 ({zero_tx/len(df_whale)*100:.1f}%)")
    
    # 연속 0값 구간
    df_whale['tx_is_zero'] = df_whale['avg_transaction_value_btc'] == 0
    groups = (df_whale['tx_is_zero'] != df_whale['tx_is_zero'].shift()).cumsum()
    consecutive = df_whale.groupby(groups).agg({
        'date': ['first', 'last', 'count'],
        'tx_is_zero': 'first'
    })
    consecutive = consecutive[consecutive[('tx_is_zero', 'first')] == True]
    
    if len(consecutive) > 0:
        max_consec = consecutive[('date', 'count')].max()
        print(f"\n   ⚠️ 연속 0값 구간: {len(consecutive)}개")
        print(f"   최대 연속 일수: {max_consec}일")
    
    # 4. 데이터 분포 통계
    print(f"\n4️⃣ 데이터 분포 통계")
    print("-" * 80)
    
    print(f"\n   top100_richest_pct:")
    print(f"     - 중앙값: {df_whale['top100_richest_pct'].median():.2f}%")
    print(f"     - 평균: {df_whale['top100_richest_pct'].mean():.2f}%")
    print(f"     - 표준편차: {df_whale['top100_richest_pct'].std():.2f}%")
    print(f"     - 1% 분위수: {df_whale['top100_richest_pct'].quantile(0.01):.2f}%")
    print(f"     - 99% 분위수: {df_whale['top100_richest_pct'].quantile(0.99):.2f}%")
    
    print(f"\n   avg_transaction_value_btc:")
    print(f"     - 중앙값: {df_whale['avg_transaction_value_btc'].median():.2f} BTC")
    print(f"     - 평균: {df_whale['avg_transaction_value_btc'].mean():.2f} BTC")
    print(f"     - 표준편차: {df_whale['avg_transaction_value_btc'].std():.2f} BTC")
    print(f"     - 1% 분위수: {df_whale['avg_transaction_value_btc'].quantile(0.01):.2f} BTC")
    print(f"     - 99% 분위수: {df_whale['avg_transaction_value_btc'].quantile(0.99):.2f} BTC")
    
    # 5. 문제점 요약
    print(f"\n5️⃣ 문제점 요약")
    print("-" * 80)
    
    issues = []
    
    # OI 데이터 부족
    if len(df_oi_dates) < 100:
        issues.append(f"❌ OI 데이터 부족: {len(df_oi_dates)}일만 있음 (필요: 최소 1년 이상)")
    
    # 고래 데이터 이상치
    if outliers_pct.sum() > 0:
        extreme_outliers = (df_whale['top100_richest_pct'] > 100).sum()
        if extreme_outliers > 0:
            issues.append(f"❌ top100_richest_pct 극단적 이상치: {extreme_outliers}건 (100% 초과)")
    
    if outliers_tx.sum() > 0:
        extreme_outliers = (df_whale['avg_transaction_value_btc'] > 10000).sum()
        if extreme_outliers > 0:
            issues.append(f"❌ avg_transaction_value_btc 극단적 이상치: {extreme_outliers}건 (10,000 BTC 초과)")
    
    # 0값 문제
    if zero_tx > 0:
        issues.append(f"⚠️ avg_transaction_value_btc 0값: {zero_tx}건 ({zero_tx/len(df_whale)*100:.1f}%)")
    
    if issues:
        print("\n   발견된 문제:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n   ✅ 특별한 문제 없음")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 분석 완료!")
    print("=" * 80)
    
    return {
        'oi_days': len(df_oi_dates),
        'whale_outliers_pct': outliers_pct.sum(),
        'whale_outliers_tx': outliers_tx.sum(),
        'zero_tx': zero_tx
    }

if __name__ == "__main__":
    analyze_data_quality()

