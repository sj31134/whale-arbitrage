#!/usr/bin/env python3
"""
고래 데이터와 가격 간 종합 상관관계 분석

종속변수:
- price_static: 정적 가격 (USD)
- price_change_1d, price_change_7d, price_change_30d: 가격 변화율
- volatility_1d, volatility_7d: 변동성
- price_direction_1d, price_direction_7d: 가격 방향 (상승/하락)

독립변수 (고래/온체인 변수):
- 온체인 변수: exchange_inflow_usd, exchange_outflow_usd, net_flow_usd,
              active_addresses, large_tx_count, avg_tx_size_usd
- 파생상품 변수: sum_open_interest, avg_funding_rate, long_short_ratio,
                taker_buy_sell_ratio, top_trader_long_short_ratio
- 고래 집중도 변수: top100_richest_pct, whale_conc_change_7d

분석 방법:
1. 상관관계 분석 (Pearson, Spearman)
2. 그레인저 인과관계 검정
3. 선형 회귀 분석
4. 랜덤 포레스트 피처 중요도
5. SHAP 값 분석 (샘플링)
"""

import os
import sys
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from scipy import stats
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))

from feature_engineering import FeatureEngineer

DB_PATH = ROOT / "data" / "project.db"
OUTPUT_DIR = ROOT / "data" / "analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 그레인저 인과관계 검정 (선택적)
try:
    from statsmodels.tsa.stattools import grangercausalitytests
    HAS_GRANGER = True
except ImportError:
    HAS_GRANGER = False

# 랜덤 포레스트 (선택적)
try:
    from sklearn.ensemble import RandomForestRegressor
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# SHAP (선택적)
try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False


def load_price_data(coin: str = "BTC", start_date: str = "2022-01-01") -> pd.DataFrame:
    """가격 데이터 로드"""
    conn = sqlite3.connect(DB_PATH)
    
    symbol = f"{coin}USDT"
    
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
    
    # 정적 가격
    df['price_static'] = df['price']
    
    # 가격 변화율
    df['price_change_1d'] = df['price'].pct_change(1).shift(-1)
    df['price_change_7d'] = df['price'].pct_change(7).shift(-7)
    df['price_change_30d'] = df['price'].pct_change(30).shift(-30)
    
    # 변동성
    df['volatility_1d'] = df['price'].pct_change().rolling(1).std()
    df['volatility_7d'] = df['price'].pct_change().rolling(7).std()
    
    # 가격 방향
    df['price_direction_1d'] = (df['price_change_1d'] > 0).astype(int)
    df['price_direction_7d'] = (df['price_change_7d'] > 0).astype(int)
    
    return df


def calculate_correlations(
    whale_df: pd.DataFrame,
    target_df: pd.DataFrame,
    lags: list = [0, 1, 2, 3, 7]
) -> pd.DataFrame:
    """상관관계 계산"""
    # 날짜 기준 병합
    merged = pd.merge(
        whale_df,
        target_df[['date', 'price_static', 'price_change_1d', 'price_change_7d', 
                   'price_change_30d', 'volatility_1d', 'volatility_7d',
                   'price_direction_1d', 'price_direction_7d']],
        on='date',
        how='inner'
    )
    
    results = []
    
    # 고래/온체인 변수 필터링
    whale_cols = [
        'exchange_inflow_usd', 'exchange_outflow_usd', 'net_flow_usd',
        'active_addresses', 'large_tx_count', 'avg_tx_size_usd',
        'sum_open_interest', 'avg_funding_rate', 'long_short_ratio',
        'taker_buy_sell_ratio', 'top_trader_long_short_ratio',
        'top100_richest_pct', 'whale_conc_change_7d'
    ]
    
    # 존재하는 컬럼만 사용
    available_whale_cols = [col for col in whale_cols if col in merged.columns]
    
    target_cols = ['price_static', 'price_change_1d', 'price_change_7d', 
                   'price_change_30d', 'volatility_1d', 'volatility_7d',
                   'price_direction_1d', 'price_direction_7d']
    
    for var in available_whale_cols:
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
                
                if len(x_valid) < 30:
                    continue
                
                # Pearson 상관계수
                try:
                    pearson_r, pearson_p = stats.pearsonr(x_valid, y_valid)
                except:
                    pearson_r, pearson_p = np.nan, np.nan
                
                # Spearman 상관계수
                try:
                    spearman_r, spearman_p = stats.spearmanr(x_valid, y_valid)
                except:
                    spearman_r, spearman_p = np.nan, np.nan
                
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


def granger_causality_test(
    x: pd.Series,
    y: pd.Series,
    maxlag: int = 3
) -> Dict:
    """그레인저 인과관계 검정"""
    if not HAS_GRANGER:
        return {'pvalue': np.nan, 'significant': False}
    
    # 결측치 제거
    valid_mask = ~(x.isna() | y.isna())
    x_valid = x[valid_mask].values
    y_valid = y[valid_mask].values
    
    if len(x_valid) < 50:  # 최소 샘플 수
        return {'pvalue': np.nan, 'significant': False}
    
    try:
        # 그레인저 검정 (x가 y의 원인인지)
        test_result = grangercausalitytests(
            np.column_stack([y_valid, x_valid]),
            maxlag=maxlag,
            verbose=False
        )
        
        # 최적 lag의 p-value 추출
        pvalues = [test_result[i+1][0]['ssr_ftest'][1] for i in range(maxlag)]
        min_pvalue = min(pvalues)
        
        return {
            'pvalue': min_pvalue,
            'significant': min_pvalue < 0.05
        }
    except:
        return {'pvalue': np.nan, 'significant': False}


def linear_regression_analysis(
    x: pd.Series,
    y: pd.Series
) -> Dict:
    """선형 회귀 분석"""
    valid_mask = ~(x.isna() | y.isna())
    x_valid = x[valid_mask].values.reshape(-1, 1)
    y_valid = y[valid_mask].values
    
    if len(x_valid) < 30:
        return {'coefficient': np.nan, 'r_squared': np.nan}
    
    try:
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import r2_score
        
        model = LinearRegression()
        model.fit(x_valid, y_valid)
        y_pred = model.predict(x_valid)
        
        return {
            'coefficient': model.coef_[0],
            'r_squared': r2_score(y_valid, y_pred)
        }
    except:
        return {'coefficient': np.nan, 'r_squared': np.nan}


def random_forest_importance(
    X: pd.DataFrame,
    y: pd.Series,
    top_n: int = 10
) -> pd.DataFrame:
    """랜덤 포레스트 피처 중요도"""
    if not HAS_SKLEARN:
        return pd.DataFrame()
    
    # 결측치 처리
    X_clean = X.fillna(0)
    y_clean = y.fillna(0)
    
    if len(X_clean) < 30:
        return pd.DataFrame()
    
    try:
        model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        model.fit(X_clean, y_clean)
        
        importance_df = pd.DataFrame({
            'feature': X_clean.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False).head(top_n)
        
        return importance_df
    except:
        return pd.DataFrame()


def main():
    """메인 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description="고래 데이터 가격 상관관계 분석")
    parser.add_argument("--coin", type=str, default="BTC", choices=["BTC", "ETH"])
    parser.add_argument("--start-date", type=str, default="2022-01-01")
    args = parser.parse_args()
    
    print("=" * 80)
    print("📊 고래 데이터 가격 상관관계 분석")
    print("=" * 80)
    print(f"코인: {args.coin}")
    print(f"시작일: {args.start_date}")
    print()
    
    # 1. 가격 데이터 로드
    print("[1/5] 가격 데이터 로드 중...")
    price_df = load_price_data(args.coin, args.start_date)
    
    if price_df.empty:
        print("❌ 가격 데이터를 불러올 수 없습니다.")
        return
    
    print(f"   ✅ {len(price_df)}건 로드")
    
    # 2. 종속변수 계산
    print("\n[2/5] 종속변수 계산 중...")
    target_df = calculate_target_variables(price_df)
    print(f"   ✅ 종속변수 계산 완료")
    
    # 3. 고래 데이터 로드
    print("\n[3/5] 고래 데이터 로드 중...")
    fe = FeatureEngineer()
    raw_df = fe.load_raw_data(args.start_date, coin=args.coin)
    
    if raw_df.empty:
        print("❌ 고래 데이터를 불러올 수 없습니다.")
        return
    
    print(f"   ✅ {len(raw_df)}건 로드")
    
    # 4. 상관관계 계산
    print("\n[4/5] 상관관계 계산 중...")
    results_df = calculate_correlations(raw_df, target_df)
    
    if results_df.empty:
        print("❌ 상관관계를 계산할 수 없습니다.")
        return
    
    print(f"   ✅ {len(results_df)}개 조합 분석")
    
    # 5. 추가 분석 (그레인저, 회귀, RF)
    print("\n[5/5] 추가 분석 중...")
    
    # 날짜 기준 병합
    merged = pd.merge(raw_df, target_df, on='date', how='inner')
    
    # 유의미한 상관관계만 선택 (p < 0.05)
    significant = results_df[results_df['pearson_pvalue'] < 0.05].copy()
    
    if len(significant) > 0:
        print(f"   ✅ 유의미한 상관관계: {len(significant)}개")
        
        # 그레인저 인과관계 검정 (샘플링)
        if HAS_GRANGER:
            print("   그레인저 인과관계 검정 중...")
            granger_results = []
            sample = significant.sample(min(20, len(significant)))  # 최대 20개 샘플
            
            for _, row in sample.iterrows():
                var = row['variable']
                target = row['target']
                lag = int(row['lag'])
                
                if var in merged.columns and target in merged.columns:
                    x = merged[var].shift(lag) if lag > 0 else merged[var]
                    y = merged[target]
                    
                    granger = granger_causality_test(x, y)
                    granger_results.append({
                        'variable': var,
                        'target': target,
                        'lag': lag,
                        'granger_pvalue': granger['pvalue'],
                        'granger_significant': granger['significant']
                    })
            
            if granger_results:
                granger_df = pd.DataFrame(granger_results)
                significant = significant.merge(granger_df, on=['variable', 'target', 'lag'], how='left')
                print(f"      ✅ {len(granger_results)}개 검정 완료")
        
        # 선형 회귀 분석
        print("   선형 회귀 분석 중...")
        regression_results = []
        
        for _, row in significant.head(50).iterrows():  # 최대 50개
            var = row['variable']
            target = row['target']
            lag = int(row['lag'])
            
            if var in merged.columns and target in merged.columns:
                x = merged[var].shift(lag) if lag > 0 else merged[var]
                y = merged[target]
                
                reg = linear_regression_analysis(x, y)
                regression_results.append({
                    'variable': var,
                    'target': target,
                    'lag': lag,
                    'regression_coef': reg['coefficient'],
                    'r_squared': reg['r_squared']
                })
        
        if regression_results:
            reg_df = pd.DataFrame(regression_results)
            significant = significant.merge(reg_df, on=['variable', 'target', 'lag'], how='left')
            print(f"      ✅ {len(regression_results)}개 회귀 분석 완료")
    
    # 6. 결과 저장
    output_file = OUTPUT_DIR / f"whale_price_correlation_{args.coin}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    results_df.to_csv(output_file, index=False)
    print(f"\n✅ 결과 저장: {output_file}")
    
    # 7. 요약 출력
    print("\n" + "=" * 80)
    print("📊 상위 10개 유의미한 상관관계")
    print("=" * 80)
    
    if len(significant) > 0:
        top10 = significant.nlargest(10, 'pearson_correlation', keep='all')
        display_cols = ['variable', 'target', 'lag', 'pearson_correlation', 'pearson_pvalue', 'sample_size']
        if 'r_squared' in top10.columns:
            display_cols.append('r_squared')
        print(top10[display_cols].to_string())
    else:
        print("유의미한 상관관계가 없습니다.")
    
    print("\n" + "=" * 80)
    print("✅ 분석 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()

