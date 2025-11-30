#!/usr/bin/env python3
"""
동적 변수와 가격 변화 간 상관관계 분석

종속변수:
- price_change_1d: 1일 후 가격 변화율
- price_change_7d: 7일 후 가격 변화율
- volatility_change_1d: 1일 후 변동성 변화율
- price_direction_1d: 1일 후 가격 방향 (상승/하락, binary)

독립변수 (동적 변수):
- volatility_delta, volatility_accel, volatility_slope
- oi_delta, oi_accel, oi_slope
- funding_delta, funding_accel
- taker_ratio_delta, net_flow_delta
- 기타 모든 동적 변수
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from scipy import stats

# FDR 보정 (선택적)
try:
    from statsmodels.stats.multitest import multipletests
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

ROOT = Path(__file__).resolve().parent.parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))

from feature_engineering import FeatureEngineer

DB_PATH = ROOT / "data" / "project.db"
OUTPUT_DIR = ROOT / "data" / "analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_price_data(coin: str = "BTC", start_date: str = "2022-01-01") -> pd.DataFrame:
    """가격 데이터 로드"""
    conn = sqlite3.connect(DB_PATH)
    
    symbol = f"{coin}USDT"
    
    # binance_spot_daily에서 가격 데이터 로드
    query = f"""
    SELECT 
        date,
        close as price
    FROM binance_spot_daily
    WHERE symbol = '{symbol}'
    AND date >= '{start_date}'
    ORDER BY date
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    if len(df) == 0:
        return pd.DataFrame()
    
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    return df


def calculate_target_variables(price_df: pd.DataFrame) -> pd.DataFrame:
    """종속변수 계산"""
    df = price_df.copy()
    
    # 가격 변화율
    df['price_change_1d'] = df['price'].pct_change(1).shift(-1)  # 다음날 변화율
    df['price_change_7d'] = df['price'].pct_change(7).shift(-7)  # 7일 후 변화율
    
    # 변동성 (20일 롤링 표준편차)
    df['volatility'] = df['price'].pct_change().rolling(20).std()
    df['volatility_change_1d'] = df['volatility'].diff(1).shift(-1)  # 다음날 변동성 변화
    
    # 가격 방향 (1일 후 상승=1, 하락=0)
    df['price_direction_1d'] = (df['price_change_1d'] > 0).astype(int)
    
    return df


def calculate_correlations(
    dynamic_df: pd.DataFrame,
    target_df: pd.DataFrame,
    lags: list = [0, 1, 2, 3, 7]
) -> pd.DataFrame:
    """상관관계 계산"""
    # 날짜 기준 병합
    merged = pd.merge(
        dynamic_df[['date'] + [col for col in dynamic_df.columns if any(x in col for x in ['delta', 'accel', 'slope', 'momentum', 'stability'])]],
        target_df[['date', 'price_change_1d', 'price_change_7d', 'volatility_change_1d', 'price_direction_1d']],
        on='date',
        how='inner'
    )
    
    results = []
    
    # 동적 변수 필터링
    dynamic_cols = [col for col in merged.columns if any(x in col for x in ['delta', 'accel', 'slope', 'momentum', 'stability'])]
    target_cols = ['price_change_1d', 'price_change_7d', 'volatility_change_1d', 'price_direction_1d']
    
    for var in dynamic_cols:
        for target in target_cols:
            for lag in lags:
                if lag == 0:
                    x = merged[var]
                    y = merged[target]
                else:
                    x = merged[var].shift(lag)
                    y = merged[target]
                
                # 유효한 데이터만 사용
                valid_mask = ~(x.isna() | y.isna())
                x_valid = x[valid_mask]
                y_valid = y[valid_mask]
                
                if len(x_valid) < 30:  # 최소 30개 샘플 필요
                    continue
                
                # Pearson 상관계수
                pearson_r, pearson_p = stats.pearsonr(x_valid, y_valid)
                
                # Spearman 상관계수
                spearman_r, spearman_p = stats.spearmanr(x_valid, y_valid)
                
                results.append({
                    'variable': var,
                    'target': target,
                    'lag': lag,
                    'pearson_correlation': pearson_r,
                    'pearson_pvalue': pearson_p,
                    'spearman_correlation': spearman_r,
                    'spearman_pvalue': spearman_p,
                    'sample_size': len(x_valid)
                })
    
    return pd.DataFrame(results)


def apply_fdr_correction(results_df: pd.DataFrame) -> pd.DataFrame:
    """False Discovery Rate (FDR) 보정"""
    df = results_df.copy()
    
    if not HAS_STATSMODELS:
        print("   ⚠️ statsmodels가 없어 FDR 보정을 건너뜁니다.")
        return df
    
    # p-value가 유효한 행만 필터링
    valid_mask = df['pearson_pvalue'].notna()
    
    if valid_mask.sum() == 0:
        return df
    
    # FDR 보정 (Benjamini-Hochberg)
    pvalues = df.loc[valid_mask, 'pearson_pvalue'].values
    _, pvalues_corrected, _, _ = multipletests(pvalues, method='fdr_bh')
    
    df.loc[valid_mask, 'pearson_pvalue_fdr'] = pvalues_corrected
    
    # Spearman도 동일하게
    pvalues_spearman = df.loc[valid_mask, 'spearman_pvalue'].values
    _, pvalues_spearman_corrected, _, _ = multipletests(pvalues_spearman, method='fdr_bh')
    
    df.loc[valid_mask, 'spearman_pvalue_fdr'] = pvalues_spearman_corrected
    
    return df


def main():
    """메인 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description="동적 변수 상관관계 분석")
    parser.add_argument("--coin", type=str, default="BTC", choices=["BTC", "ETH"])
    parser.add_argument("--start-date", type=str, default="2022-01-01")
    args = parser.parse_args()
    
    print("=" * 80)
    print("📊 동적 변수 상관관계 분석")
    print("=" * 80)
    print(f"코인: {args.coin}")
    print(f"시작일: {args.start_date}")
    print()
    
    # 1. 가격 데이터 로드
    print("[1/4] 가격 데이터 로드 중...")
    price_df = load_price_data(args.coin, args.start_date)
    
    if price_df.empty:
        print("❌ 가격 데이터를 불러올 수 없습니다.")
        return
    
    print(f"   ✅ {len(price_df)}건 로드 ({price_df['date'].min()} ~ {price_df['date'].max()})")
    
    # 2. 종속변수 계산
    print("\n[2/4] 종속변수 계산 중...")
    target_df = calculate_target_variables(price_df)
    print(f"   ✅ 종속변수 계산 완료")
    
    # 3. 동적 변수 포함 피처 생성
    print("\n[3/4] 동적 변수 포함 피처 생성 중...")
    fe = FeatureEngineer()
    raw_df = fe.load_raw_data(args.start_date, coin=args.coin)
    
    if raw_df.empty:
        print("❌ 원본 데이터를 불러올 수 없습니다.")
        return
    
    dynamic_df, features = fe.create_features(raw_df, include_dynamic=True)
    print(f"   ✅ {len(features)}개 피처 생성 (동적 변수 포함)")
    
    # 4. 상관관계 계산
    print("\n[4/4] 상관관계 계산 중...")
    results_df = calculate_correlations(dynamic_df, target_df)
    
    if results_df.empty:
        print("❌ 상관관계를 계산할 수 없습니다.")
        return
    
    # FDR 보정
    results_df = apply_fdr_correction(results_df)
    
    # 유의미한 결과만 필터링 (p < 0.05)
    significant = results_df[
        (results_df['pearson_pvalue'] < 0.05) | 
        (results_df.get('pearson_pvalue_fdr', 1) < 0.05)
    ]
    
    print(f"   ✅ 총 {len(results_df)}개 조합 분석")
    print(f"   ✅ 유의미한 상관관계: {len(significant)}개 (p < 0.05)")
    
    # 5. 결과 저장
    output_file = OUTPUT_DIR / f"dynamic_correlation_{args.coin}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    results_df.to_csv(output_file, index=False)
    print(f"\n✅ 결과 저장: {output_file}")
    
    # 6. 요약 출력
    print("\n" + "=" * 80)
    print("📊 상위 10개 유의미한 상관관계")
    print("=" * 80)
    
    top10 = significant.nlargest(10, 'pearson_correlation', keep='all')
    if len(top10) > 0:
        print(top10[['variable', 'target', 'lag', 'pearson_correlation', 'pearson_pvalue', 'sample_size']].to_string())
    else:
        print("유의미한 상관관계가 없습니다.")
    
    print("\n" + "=" * 80)
    print("✅ 분석 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()

