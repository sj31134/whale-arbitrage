"""
Panel Regression Analysis with REAL Data

순환 논리가 제거된 실제 데이터 기반 분석:
- Y 변수: 실제 시장 가격/거래량에서 도출
- X 변수 (TDT): 공시 정보에서 독립적으로 도출
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
import os
import warnings
warnings.filterwarnings('ignore')


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    분석용 데이터 전처리.
    """
    df = df.copy()
    
    # 결측치 처리
    df = df.dropna(subset=['daily_return', 'tdt_score'])
    
    # 무한대 값 제거
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=['illiquidity', 'volatility_7d'], how='all')
    
    # 시총 로그 변환
    df['market_cap_log'] = np.log(df['market_cap'] + 1)
    
    return df


def run_h1_illiquidity_regression(df: pd.DataFrame):
    """
    H1: TDT → Illiquidity (실제 데이터)
    """
    df_clean = df.dropna(subset=['illiquidity', 'tdt_score', 'market_cap_log'])
    
    # 극단치 제거 (상위 1%)
    q99 = df_clean['illiquidity'].quantile(0.99)
    df_clean = df_clean[df_clean['illiquidity'] < q99]
    
    if len(df_clean) < 50:
        print("⚠️ Insufficient data for H1")
        return None
    
    X = df_clean[['tdt_score', 'market_cap_log']]
    X = sm.add_constant(X)
    y = df_clean['illiquidity']
    
    model = OLS(y, X).fit(cov_type='HC1')
    return model


def run_h2_volatility_regression(df: pd.DataFrame):
    """
    H2: TDT → Volatility (실제 데이터)
    """
    df_clean = df.dropna(subset=['volatility_7d', 'tdt_score', 'market_cap_log'])
    
    if len(df_clean) < 50:
        print("⚠️ Insufficient data for H2")
        return None
    
    X = df_clean[['tdt_score', 'market_cap_log']]
    X = sm.add_constant(X)
    y = df_clean['volatility_7d']
    
    model = OLS(y, X).fit(cov_type='HC1')
    return model


def run_h3_shock_interaction(df: pd.DataFrame):
    """
    H3: TDT × Shock → Return (실제 데이터)
    """
    df_clean = df.dropna(subset=['daily_return', 'tdt_score', 'macro_shock', 'market_cap_log'])
    
    if len(df_clean) < 50:
        print("⚠️ Insufficient data for H3")
        return None
    
    # 상호작용항 생성
    df_clean = df_clean.copy()
    df_clean['tdt_shock'] = df_clean['tdt_score'] * df_clean['macro_shock']
    
    X = df_clean[['tdt_score', 'macro_shock', 'tdt_shock', 'market_cap_log']]
    X = sm.add_constant(X)
    y = df_clean['daily_return']
    
    model = OLS(y, X).fit(cov_type='HC1')
    return model


def run_component_analysis(df: pd.DataFrame):
    """
    RQ3: TDT 구성요소별 분석 (실제 데이터)
    """
    components = ['latency_score', 'completeness_score', 'consistency_score']
    df_clean = df.dropna(subset=['volatility_7d'] + components + ['market_cap_log'])
    
    if len(df_clean) < 50:
        print("⚠️ Insufficient data for RQ3")
        return None
    
    X = df_clean[components + ['market_cap_log']]
    X = sm.add_constant(X)
    y = df_clean['volatility_7d']
    
    model = OLS(y, X).fit(cov_type='HC1')
    return model


def main():
    base_path = os.path.dirname(__file__)
    panel_path = os.path.join(base_path, '../../data/processed/final_panel_data.csv')
    output_path = os.path.join(base_path, '../../data/processed/real_regression_results.csv')
    
    print("=" * 60)
    print("Panel Regression Analysis with REAL DATA")
    print("(No circular logic - TDT from disclosure, Y from market)")
    print("=" * 60)
    
    # 데이터 로드
    df = pd.read_csv(panel_path)
    print(f"\nLoaded {len(df)} observations from real market data")
    print(f"Tokens: {df['symbol'].nunique()}")
    print(f"TDT range: {df['tdt_score'].min():.1f} ~ {df['tdt_score'].max():.1f}")
    
    df = prepare_data(df)
    print(f"After cleaning: {len(df)} observations")
    
    # 기술 통계
    print("\n=== Descriptive Statistics ===")
    print(df[['daily_return', 'volatility_7d', 'illiquidity', 'tdt_score']].describe().round(6))
    
    results = []
    
    # H1: 유동성
    print("\n" + "=" * 60)
    print("[H1] TDT → Illiquidity (REAL DATA)")
    print("=" * 60)
    model_h1 = run_h1_illiquidity_regression(df)
    if model_h1:
        print(model_h1.summary().tables[1])
        for var in model_h1.params.index:
            results.append({
                'Model': 'H1_Illiquidity_REAL',
                'Variable': var,
                'Coefficient': model_h1.params[var],
                't-stat': model_h1.tvalues[var],
                'p-value': model_h1.pvalues[var],
                'N': int(model_h1.nobs)
            })
    
    # H2: 변동성
    print("\n" + "=" * 60)
    print("[H2] TDT → Volatility (REAL DATA)")
    print("=" * 60)
    model_h2 = run_h2_volatility_regression(df)
    if model_h2:
        print(model_h2.summary().tables[1])
        for var in model_h2.params.index:
            results.append({
                'Model': 'H2_Volatility_REAL',
                'Variable': var,
                'Coefficient': model_h2.params[var],
                't-stat': model_h2.tvalues[var],
                'p-value': model_h2.pvalues[var],
                'N': int(model_h2.nobs)
            })
    
    # H3: 충격 상호작용
    print("\n" + "=" * 60)
    print("[H3] TDT × Shock → Return (REAL DATA)")
    print("=" * 60)
    model_h3 = run_h3_shock_interaction(df)
    if model_h3:
        print(model_h3.summary().tables[1])
        for var in model_h3.params.index:
            results.append({
                'Model': 'H3_Shock_REAL',
                'Variable': var,
                'Coefficient': model_h3.params[var],
                't-stat': model_h3.tvalues[var],
                'p-value': model_h3.pvalues[var],
                'N': int(model_h3.nobs)
            })
    
    # RQ3: 구성요소 분석
    print("\n" + "=" * 60)
    print("[RQ3] Component Analysis (REAL DATA)")
    print("=" * 60)
    model_rq3 = run_component_analysis(df)
    if model_rq3:
        print(model_rq3.summary().tables[1])
        for var in model_rq3.params.index:
            results.append({
                'Model': 'RQ3_Components_REAL',
                'Variable': var,
                'Coefficient': model_rq3.params[var],
                't-stat': model_rq3.tvalues[var],
                'p-value': model_rq3.pvalues[var],
                'N': int(model_rq3.nobs)
            })
    
    # 결과 저장
    df_results = pd.DataFrame(results)
    df_results.to_csv(output_path, index=False)
    
    print("\n" + "=" * 60)
    print("SUMMARY: Real Data Regression Results")
    print("=" * 60)
    print(df_results.to_string(index=False))
    
    print("\n" + "=" * 60)
    print("INTERPRETATION")
    print("=" * 60)
    print("• These results are from REAL market data (CoinGecko historical)")
    print("• TDT scores derived independently from disclosure information")
    print("• NO circular logic: Y variables computed from actual prices")
    print("• Statistical significance should be interpreted conservatively")
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
