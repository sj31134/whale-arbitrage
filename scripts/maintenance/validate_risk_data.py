#!/usr/bin/env python3
"""
리스크 데이터 검증 스크립트

기능:
- 각 테이블 데이터 존재 여부 확인
- 동적 변수 통계 (min, max, percentiles)
- 청산 리스크 분포 시뮬레이션
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "project.db"


def check_table_exists(conn, table_name):
    """테이블 존재 여부 확인"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cursor.fetchone() is not None


def get_table_stats(conn, table_name, date_column='date'):
    """테이블 기본 통계"""
    if not check_table_exists(conn, table_name):
        return None
    
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        if len(df) == 0:
            return {'exists': True, 'count': 0, 'min_date': None, 'max_date': None}
        
        min_date = df[date_column].min() if date_column in df.columns else None
        max_date = df[date_column].max() if date_column in df.columns else None
        
        return {
            'exists': True,
            'count': len(df),
            'min_date': min_date,
            'max_date': max_date,
            'columns': list(df.columns)
        }
    except Exception as e:
        return {'exists': True, 'error': str(e)}


def analyze_dynamic_variables(conn):
    """동적 변수 통계 분석"""
    print("\n" + "=" * 80)
    print("📊 동적 변수 통계 분석")
    print("=" * 80)
    
    # binance_futures_metrics 데이터 로드
    query = """
    SELECT 
        date,
        avg_funding_rate,
        sum_open_interest,
        volatility_24h
    FROM binance_futures_metrics
    WHERE symbol = 'BTCUSDT'
    ORDER BY date
    """
    
    df = pd.read_sql(query, conn)
    
    if len(df) == 0:
        print("❌ binance_futures_metrics 데이터 없음")
        return
    
    df['date'] = pd.to_datetime(df['date'])
    
    # OI 데이터 존재 여부 확인
    has_oi = df['sum_open_interest'].sum() > 0
    
    if not has_oi:
        print("⚠️ sum_open_interest 데이터가 없습니다 (모두 0)")
    
    # 동적 변수 계산
    if has_oi:
        df['oi_growth_7d'] = df['sum_open_interest'].pct_change(7)
        df['oi_delta'] = df['sum_open_interest'].pct_change()
        df['oi_accel'] = df['oi_delta'].diff()
    else:
        df['oi_growth_7d'] = 0.0
        df['oi_delta'] = 0.0
        df['oi_accel'] = 0.0
    
    df['volatility_delta'] = df['volatility_24h'].diff()
    df['volatility_accel'] = df['volatility_delta'].diff()
    
    # 펀딩비 Z-Score
    df['funding_mean'] = df['avg_funding_rate'].rolling(30).mean()
    df['funding_std'] = df['avg_funding_rate'].rolling(30).std()
    df['funding_rate_zscore'] = np.where(
        df['funding_std'] != 0,
        (df['avg_funding_rate'] - df['funding_mean']) / df['funding_std'],
        0
    )
    
    # NaN 제거 (변동성 기반만)
    df = df.dropna(subset=['volatility_delta', 'volatility_accel', 'funding_rate_zscore'])
    
    variables = [
        ('oi_growth_7d', 'OI 7일 변화율'),
        ('funding_rate_zscore', '펀딩비 Z-Score'),
        ('volatility_delta', '변동성 변화율'),
        ('oi_delta', 'OI 일일 변화율'),
        ('volatility_accel', '변동성 가속도'),
        ('oi_accel', 'OI 가속도')
    ]
    
    print(f"\n유효 데이터: {len(df)}건")
    
    print("\n변수별 통계:")
    print("-" * 80)
    print(f"{'변수':<25} {'Min':>12} {'Max':>12} {'Mean':>12} {'Std':>12} {'P95':>12}")
    print("-" * 80)
    
    for var, name in variables:
        if var in df.columns:
            series = df[var].dropna()
            if len(series) > 0:
                print(f"{name:<25} {series.min():>12.6f} {series.max():>12.6f} {series.mean():>12.6f} {series.std():>12.6f} {series.quantile(0.95):>12.6f}")
    
    return df


def simulate_liquidation_risk(df):
    """청산 리스크 분포 시뮬레이션"""
    print("\n" + "=" * 80)
    print("📊 청산 리스크 분포 시뮬레이션")
    print("=" * 80)
    
    # 현재 계산식 (문제 있는 버전)
    df['liq_risk_old'] = df.apply(lambda row: min(100, max(0,
        abs(row.get('oi_growth_7d', 0) or 0) * 40 +
        abs(row.get('funding_rate_zscore', 0) or 0) * 20 +
        abs(row.get('oi_accel', 0) or 0) * 20 +
        abs(row.get('volatility_accel', 0) or 0) * 20
    )), axis=1)
    
    # 수정된 계산식 (스케일 정규화)
    def calc_new_risk(row):
        oi_growth = row.get('oi_growth_7d', 0) or 0
        funding_zscore = row.get('funding_rate_zscore', 0) or 0
        oi_accel = row.get('oi_accel', 0) or 0
        vol_accel = row.get('volatility_accel', 0) or 0
        
        # 스케일 정규화 (클리핑)
        oi_growth_norm = min(abs(oi_growth), 0.5)
        funding_zscore_norm = min(abs(funding_zscore), 3.0)
        oi_accel_norm = min(abs(oi_accel), 0.3)
        vol_accel_norm = min(abs(vol_accel), 0.02)
        
        return min(100, max(0,
            oi_growth_norm * 50 +
            funding_zscore_norm * 10 +
            oi_accel_norm * 50 +
            vol_accel_norm * 500
        ))
    
    df['liq_risk_new'] = df.apply(calc_new_risk, axis=1)
    
    # 비교 출력
    print("\n기존 계산식 (문제 있음):")
    print(f"  Min: {df['liq_risk_old'].min():.1f}%")
    print(f"  Max: {df['liq_risk_old'].max():.1f}%")
    print(f"  Mean: {df['liq_risk_old'].mean():.1f}%")
    print(f"  100% 비율: {(df['liq_risk_old'] >= 100).sum() / len(df) * 100:.1f}%")
    print(f"  70%+ 비율: {(df['liq_risk_old'] >= 70).sum() / len(df) * 100:.1f}%")
    
    print("\n수정된 계산식 (스케일 정규화):")
    print(f"  Min: {df['liq_risk_new'].min():.1f}%")
    print(f"  Max: {df['liq_risk_new'].max():.1f}%")
    print(f"  Mean: {df['liq_risk_new'].mean():.1f}%")
    print(f"  100% 비율: {(df['liq_risk_new'] >= 100).sum() / len(df) * 100:.1f}%")
    print(f"  70%+ 비율: {(df['liq_risk_new'] >= 70).sum() / len(df) * 100:.1f}%")
    
    # 분포 비교
    print("\n청산 리스크 분포 비교:")
    print("-" * 50)
    print(f"{'범위':<15} {'기존':>15} {'수정':>15}")
    print("-" * 50)
    
    ranges = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 100), (100, 101)]
    for low, high in ranges:
        old_pct = ((df['liq_risk_old'] >= low) & (df['liq_risk_old'] < high)).sum() / len(df) * 100
        new_pct = ((df['liq_risk_new'] >= low) & (df['liq_risk_new'] < high)).sum() / len(df) * 100
        label = f"{low}-{high}%" if high <= 100 else "100%"
        print(f"{label:<15} {old_pct:>14.1f}% {new_pct:>14.1f}%")
    
    return df


def main():
    print("=" * 80)
    print("📊 리스크 데이터 검증")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    
    # 1. 테이블 현황 확인
    print("\n[1/4] 테이블 현황 확인")
    print("-" * 80)
    
    tables = [
        ('binance_futures_metrics', 'date'),
        ('bitinfocharts_whale', 'date'),
        ('futures_extended_metrics', 'date'),
        ('whale_daily_stats', 'date'),
        ('whale_weekly_stats', 'date'),
    ]
    
    for table, date_col in tables:
        stats = get_table_stats(conn, table, date_col)
        if stats is None:
            print(f"❌ {table}: 테이블 없음")
        elif stats.get('count', 0) == 0:
            print(f"⚠️ {table}: 테이블 존재, 데이터 없음")
        else:
            print(f"✅ {table}: {stats['count']}건 ({stats['min_date']} ~ {stats['max_date']})")
    
    # 2. 핵심 컬럼 누락 현황 확인
    print("\n[2/4] 핵심 컬럼 누락 현황 확인")
    print("-" * 80)
    # binance_futures_metrics의 sum_open_interest, avg_funding_rate 채워진 비율
    if check_table_exists(conn, "binance_futures_metrics"):
        df_core = pd.read_sql(
            """
            SELECT date, symbol, avg_funding_rate, sum_open_interest
            FROM binance_futures_metrics
            WHERE symbol = 'BTCUSDT'
            """,
            conn,
        )
        total = len(df_core)
        if total > 0:
            oi_nonzero = (df_core["sum_open_interest"] != 0).sum()
            funding_nonnull = df_core["avg_funding_rate"].notna().sum()
            print(
                f"binance_futures_metrics (BTCUSDT): "
                f"행수={total}, "
                f"sum_open_interest≠0 비율={oi_nonzero/total*100:.1f}%, "
                f"avg_funding_rate 유효 비율={funding_nonnull/total*100:.1f}%"
            )
        else:
            print("binance_futures_metrics (BTCUSDT): 데이터 없음")
    else:
        print("binance_futures_metrics: 테이블 없음")

    # futures_extended_metrics, whale_daily_stats 행 수 확인 (비어 있으면 백필 대상)
    for table in ["futures_extended_metrics", "whale_daily_stats"]:
        if check_table_exists(conn, table):
            cnt = pd.read_sql(f"SELECT COUNT(*) AS c FROM {table}", conn)["c"].iloc[0]
            status = "⚠️ 비어 있음 (백필 필요)" if cnt == 0 else "✅ 데이터 존재"
            print(f"{table}: {cnt}행, {status}")
        else:
            print(f"{table}: ❌ 테이블 없음 (생성 및 백필 필요)")

    # 3. 동적 변수 분석
    print("\n[3/4] 동적 변수 분석")
    df = analyze_dynamic_variables(conn)
    
    # 4. 청산 리스크 시뮬레이션
    if df is not None and len(df) > 0:
        print("\n[4/4] 청산 리스크 시뮬레이션")
        simulate_liquidation_risk(df)
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("✅ 검증 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()

