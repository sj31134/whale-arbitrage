"""
Panel Regression Analysis for RWA Transparency Digital Twin

가설 검정:
H1: TDT ↑ → Illiquidity ↓ (정보품질-유동성 가설)
H2: TDT ↑ → Volatility ↓ (정보품질-리스크 가설)
H3: Shock 발생 시, TDT 낮은 자산이 더 취약 (거시충격 증폭 가설)
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
import os
import warnings
warnings.filterwarnings('ignore')

def run_baseline_regression(df: pd.DataFrame, y_var: str, x_var: str = 'tdt_score'):
    """
    베이스라인 회귀: Y = β·TDT + γ·Controls + ε
    """
    # 결측치 제거
    df_clean = df.dropna(subset=[y_var, x_var])
    
    if len(df_clean) < 10:
        return None
    
    # 독립변수 설정
    X = df_clean[[x_var, 'market_cap']].copy()
    X['market_cap_log'] = np.log(X['market_cap'] + 1)
    X = X.drop('market_cap', axis=1)
    X = sm.add_constant(X)
    
    y = df_clean[y_var]
    
    model = OLS(y, X).fit(cov_type='HC1')  # 이분산 강건 표준오차
    return model

def run_interaction_regression(df: pd.DataFrame, y_var: str = 'daily_return'):
    """
    상호작용 회귀 (H3): Y = β·TDT + θ·Shock + λ·TDT×Shock + ε
    """
    df_clean = df.dropna(subset=[y_var, 'tdt_score', 'macro_shock'])
    
    if len(df_clean) < 10:
        return None
    
    # 상호작용항 생성
    df_clean = df_clean.copy()
    df_clean['tdt_shock'] = df_clean['tdt_score'] * df_clean['macro_shock']
    df_clean['market_cap_log'] = np.log(df_clean['market_cap'] + 1)
    
    X = df_clean[['tdt_score', 'macro_shock', 'tdt_shock', 'market_cap_log']]
    X = sm.add_constant(X)
    
    y = df_clean[y_var]
    
    model = OLS(y, X).fit(cov_type='HC1')
    return model

def run_component_analysis(df: pd.DataFrame, y_var: str):
    """
    TDT 구성요소별 분석 (RQ3): 어떤 요소가 리스크 프리미엄을 가장 잘 설명하는가?
    """
    components = ['latency_score', 'completeness_score', 'consistency_score']
    df_clean = df.dropna(subset=[y_var] + components)
    
    if len(df_clean) < 10:
        return None
    
    df_clean = df_clean.copy()
    df_clean['market_cap_log'] = np.log(df_clean['market_cap'] + 1)
    
    X = df_clean[components + ['market_cap_log']]
    X = sm.add_constant(X)
    
    y = df_clean[y_var]
    
    model = OLS(y, X).fit(cov_type='HC1')
    return model

def format_regression_table(models: dict, output_path: str):
    """
    회귀 결과를 표로 정리하여 저장.
    """
    results = []
    
    for name, model in models.items():
        if model is None:
            continue
        
        for var in model.params.index:
            results.append({
                'Model': name,
                'Variable': var,
                'Coefficient': round(model.params[var], 6),
                'Std.Error': round(model.bse[var], 6),
                't-stat': round(model.tvalues[var], 3),
                'p-value': round(model.pvalues[var], 4),
                'Significance': '***' if model.pvalues[var] < 0.01 else ('**' if model.pvalues[var] < 0.05 else ('*' if model.pvalues[var] < 0.1 else ''))
            })
    
    df_results = pd.DataFrame(results)
    df_results.to_csv(output_path, index=False)
    return df_results

def main():
    base_path = os.path.dirname(__file__)
    panel_data_path = os.path.join(base_path, '../../data/processed/panel_data.csv')
    output_path = os.path.join(base_path, '../../data/processed/regression_results.csv')
    
    print("=" * 60)
    print("RWA Transparency Digital Twin: Panel Regression Analysis")
    print("=" * 60)
    
    df = pd.read_csv(panel_data_path)
    print(f"\nLoaded panel data: {len(df)} observations")
    
    models = {}
    
    # === H1: 정보품질-유동성 가설 ===
    print("\n[H1] TDT → Illiquidity")
    model_h1 = run_baseline_regression(df, 'illiquidity', 'tdt_score')
    if model_h1:
        print(model_h1.summary().tables[1])
        models['H1_Illiquidity'] = model_h1
    
    # === H2: 정보품질-리스크 가설 ===
    print("\n[H2] TDT → Volatility")
    model_h2 = run_baseline_regression(df, 'volatility', 'tdt_score')
    if model_h2:
        print(model_h2.summary().tables[1])
        models['H2_Volatility'] = model_h2
    
    # === H3: 거시충격 증폭 가설 ===
    print("\n[H3] TDT × Shock → Return (Interaction)")
    model_h3 = run_interaction_regression(df, 'daily_return')
    if model_h3:
        print(model_h3.summary().tables[1])
        models['H3_Shock_Interaction'] = model_h3
    
    # === RQ3: 구성요소 분석 ===
    print("\n[RQ3] Component Analysis: Latency vs Completeness vs Consistency → Volatility")
    model_rq3 = run_component_analysis(df, 'volatility')
    if model_rq3:
        print(model_rq3.summary().tables[1])
        models['RQ3_Components'] = model_rq3
    
    # === 결과 저장 ===
    df_results = format_regression_table(models, output_path)
    print(f"\n\nRegression results saved to: {output_path}")
    print("\n=== Summary Table ===")
    print(df_results.to_string(index=False))
    
    # === 해석 ===
    print("\n" + "=" * 60)
    print("Interpretation Guide:")
    print("=" * 60)
    print("- H1: tdt_score 계수가 음수(-)면 → TDT 높을수록 Illiquidity 낮음 (지지)")
    print("- H2: tdt_score 계수가 음수(-)면 → TDT 높을수록 Volatility 낮음 (지지)")
    print("- H3: tdt_shock 계수가 양수(+)면 → TDT 높을수록 충격 완화 (지지)")
    print("- RQ3: 가장 큰 |t-stat|을 가진 구성요소가 설명력 최대")


if __name__ == "__main__":
    main()
