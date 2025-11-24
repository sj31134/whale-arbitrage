#!/usr/bin/env python3
"""
모든 변수가 동일 기간 데이터를 가지도록 검증
데이터 정렬 및 일치 여부 확인
"""

import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"

def verify_data_alignment():
    print("=" * 80)
    print("🔍 데이터 정렬 및 일치 여부 검증")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. 각 테이블의 데이터 기간 확인
    print("\n1️⃣ 테이블별 데이터 기간")
    print("-" * 80)
    
    # binance_futures_metrics
    df_futures = pd.read_sql("""
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(*) as total_count,
            SUM(CASE WHEN avg_funding_rate > 0 THEN 1 ELSE 0 END) as funding_count,
            SUM(CASE WHEN sum_open_interest > 0 THEN 1 ELSE 0 END) as oi_count,
            SUM(CASE WHEN volatility_24h > 0 THEN 1 ELSE 0 END) as vol_count
        FROM binance_futures_metrics
        WHERE symbol = 'BTCUSDT'
    """, conn)
    
    print(f"\n📊 binance_futures_metrics:")
    print(f"   기간: {df_futures['min_date'].iloc[0]} ~ {df_futures['max_date'].iloc[0]}")
    print(f"   총 레코드: {df_futures['total_count'].iloc[0]:,}건")
    print(f"   펀딩비 > 0: {df_futures['funding_count'].iloc[0]:,}건 ({df_futures['funding_count'].iloc[0]/df_futures['total_count'].iloc[0]*100:.1f}%)")
    print(f"   OI > 0: {df_futures['oi_count'].iloc[0]:,}건 ({df_futures['oi_count'].iloc[0]/df_futures['total_count'].iloc[0]*100:.1f}%)")
    print(f"   변동성 > 0: {df_futures['vol_count'].iloc[0]:,}건 ({df_futures['vol_count'].iloc[0]/df_futures['total_count'].iloc[0]*100:.1f}%)")
    
    # bitinfocharts_whale
    df_whale = pd.read_sql("""
        SELECT 
            MIN(date) as min_date,
            MAX(date) as max_date,
            COUNT(*) as total_count,
            SUM(CASE WHEN top100_richest_pct > 0 THEN 1 ELSE 0 END) as pct_count,
            SUM(CASE WHEN avg_transaction_value_btc > 0 THEN 1 ELSE 0 END) as tx_count
        FROM bitinfocharts_whale
        WHERE coin = 'BTC'
    """, conn)
    
    print(f"\n🐋 bitinfocharts_whale:")
    print(f"   기간: {df_whale['min_date'].iloc[0]} ~ {df_whale['max_date'].iloc[0]}")
    print(f"   총 레코드: {df_whale['total_count'].iloc[0]:,}건")
    print(f"   top100_richest_pct > 0: {df_whale['pct_count'].iloc[0]:,}건 ({df_whale['pct_count'].iloc[0]/df_whale['total_count'].iloc[0]*100:.1f}%)")
    print(f"   avg_transaction_value_btc > 0: {df_whale['tx_count'].iloc[0]:,}건 ({df_whale['tx_count'].iloc[0]/df_whale['total_count'].iloc[0]*100:.1f}%)")
    
    # 2. 데이터 매칭 확인
    print("\n2️⃣ 데이터 매칭 및 정렬 확인")
    print("-" * 80)
    
    df_merged = pd.read_sql("""
        SELECT 
            f.date,
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
    
    df_merged['date'] = pd.to_datetime(df_merged['date'])
    
    # 각 변수의 유효 데이터 기간
    print("\n   각 변수의 유효 데이터 기간:")
    
    # 펀딩비
    funding_valid = df_merged[df_merged['avg_funding_rate'] > 0]
    if len(funding_valid) > 0:
        print(f"     - avg_funding_rate: {funding_valid['date'].min().date()} ~ {funding_valid['date'].max().date()} ({len(funding_valid)}일)")
    
    # OI
    oi_valid = df_merged[df_merged['sum_open_interest'] > 0]
    if len(oi_valid) > 0:
        print(f"     - sum_open_interest: {oi_valid['date'].min().date()} ~ {oi_valid['date'].max().date()} ({len(oi_valid)}일)")
    else:
        print(f"     - sum_open_interest: 데이터 없음")
    
    # 변동성
    vol_valid = df_merged[df_merged['volatility_24h'] > 0]
    if len(vol_valid) > 0:
        print(f"     - volatility_24h: {vol_valid['date'].min().date()} ~ {vol_valid['date'].max().date()} ({len(vol_valid)}일)")
    
    # 고래 데이터
    whale_valid = df_merged[df_merged['top100_richest_pct'].notna()]
    if len(whale_valid) > 0:
        print(f"     - top100_richest_pct: {whale_valid['date'].min().date()} ~ {whale_valid['date'].max().date()} ({len(whale_valid)}일)")
    
    tx_valid = df_merged[df_merged['avg_transaction_value_btc'] > 0]
    if len(tx_valid) > 0:
        print(f"     - avg_transaction_value_btc: {tx_valid['date'].min().date()} ~ {tx_valid['date'].max().date()} ({len(tx_valid)}일)")
    
    # 3. 공통 기간 확인
    print("\n3️⃣ 공통 유효 기간 분석")
    print("-" * 80)
    
    # 모든 변수가 유효한 기간
    all_valid = df_merged[
        (df_merged['avg_funding_rate'] > 0) &
        (df_merged['volatility_24h'] > 0) &
        (df_merged['top100_richest_pct'].notna()) &
        (df_merged['avg_transaction_value_btc'] > 0)
    ]
    
    print(f"\n   모든 변수 유효 (OI 제외):")
    if len(all_valid) > 0:
        print(f"     기간: {all_valid['date'].min().date()} ~ {all_valid['date'].max().date()}")
        print(f"     일수: {len(all_valid):,}일")
    else:
        print(f"     데이터 없음")
    
    # OI 포함한 경우
    all_valid_with_oi = df_merged[
        (df_merged['avg_funding_rate'] > 0) &
        (df_merged['sum_open_interest'] > 0) &
        (df_merged['volatility_24h'] > 0) &
        (df_merged['top100_richest_pct'].notna()) &
        (df_merged['avg_transaction_value_btc'] > 0)
    ]
    
    print(f"\n   모든 변수 유효 (OI 포함):")
    if len(all_valid_with_oi) > 0:
        print(f"     기간: {all_valid_with_oi['date'].min().date()} ~ {all_valid_with_oi['date'].max().date()}")
        print(f"     일수: {len(all_valid_with_oi):,}일")
    else:
        print(f"     데이터 없음")
    
    # 4. 문제점 및 권장사항
    print("\n4️⃣ 문제점 및 권장사항")
    print("-" * 80)
    
    issues = []
    recommendations = []
    
    # OI 데이터 부족
    if len(oi_valid) < 100:
        issues.append(f"❌ OI 데이터 부족: {len(oi_valid)}일만 있음 (필요: 최소 1년 이상)")
        recommendations.append("   - 매일 자동 수집 스크립트 실행하여 데이터 축적")
        recommendations.append("   - 또는 OI 특성을 제거하고 다른 특성만 사용")
    
    # 데이터 기간 불일치
    min_date = min(
        funding_valid['date'].min() if len(funding_valid) > 0 else datetime.max,
        vol_valid['date'].min() if len(vol_valid) > 0 else datetime.max,
        whale_valid['date'].min() if len(whale_valid) > 0 else datetime.max
    )
    max_date = max(
        funding_valid['date'].max() if len(funding_valid) > 0 else datetime.min,
        vol_valid['date'].max() if len(vol_valid) > 0 else datetime.min,
        whale_valid['date'].max() if len(whale_valid) > 0 else datetime.min
    )
    
    if issues:
        print("\n   발견된 문제:")
        for issue in issues:
            print(f"   {issue}")
    
    if recommendations:
        print("\n   권장사항:")
        for rec in recommendations:
            print(f"   {rec}")
    
    # 5. 분석 가능한 기간 제안
    print("\n5️⃣ 분석 가능한 기간 제안")
    print("-" * 80)
    
    # OI 제외한 경우
    print(f"\n   OI 제외 분석:")
    print(f"     권장 기간: {all_valid['date'].min().date()} ~ {all_valid['date'].max().date()}")
    print(f"     일수: {len(all_valid):,}일")
    print(f"     사용 가능한 특성: avg_funding_rate, volatility_24h, top100_richest_pct, avg_transaction_value_btc")
    
    # OI 포함한 경우
    if len(all_valid_with_oi) > 0:
        print(f"\n   OI 포함 분석:")
        print(f"     권장 기간: {all_valid_with_oi['date'].min().date()} ~ {all_valid_with_oi['date'].max().date()}")
        print(f"     일수: {len(all_valid_with_oi):,}일")
        print(f"     사용 가능한 특성: 모든 특성")
    else:
        print(f"\n   OI 포함 분석:")
        print(f"     ⚠️ 데이터 부족으로 분석 불가")
        print(f"     OI 데이터가 {len(oi_valid)}일만 있어서 다른 데이터와 매칭 불가")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 검증 완료!")
    print("=" * 80)
    
    return {
        'all_valid_days': len(all_valid),
        'all_valid_with_oi_days': len(all_valid_with_oi),
        'oi_days': len(oi_valid)
    }

if __name__ == "__main__":
    verify_data_alignment()

