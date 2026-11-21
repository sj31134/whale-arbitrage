"""
Alternative Robust Analysis: 검정력 보완

문제점:
- 클러스터(자산) 수가 18개로 너무 적음
- Cameron & Miller (2015): "클러스터 수가 50개 미만이면 신뢰할 수 없음"

보완 방안:
1. 시간 클러스터링 (날짜 기준)
2. 부트스트랩 신뢰구간
3. 비모수적 접근 (Spearman/Kendall 상관)
4. 그룹 비교 (High-TDT vs Low-TDT)
5. 자산별 시계열 분석
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
from scipy import stats
from scipy.stats import spearmanr, kendalltau, mannwhitneyu, ttest_ind
import os
import warnings
warnings.filterwarnings('ignore')


def bootstrap_confidence_interval(df, y_var, x_var, n_bootstrap=1000, alpha=0.05):
    """
    부트스트랩을 통한 계수 신뢰구간 추정.
    클러스터 수가 적을 때 유용한 비모수적 방법.
    """
    df_clean = df.dropna(subset=[y_var, x_var])
    
    coefficients = []
    for _ in range(n_bootstrap):
        # 리샘플링 (replacement)
        sample = df_clean.sample(n=len(df_clean), replace=True)
        
        X = sample[[x_var]]
        X = sm.add_constant(X)
        y = sample[y_var]
        
        try:
            model = OLS(y, X).fit()
            coefficients.append(model.params[x_var])
        except:
            continue
    
    if not coefficients:
        return None, None, None
    
    coefficients = np.array(coefficients)
    lower = np.percentile(coefficients, alpha/2 * 100)
    upper = np.percentile(coefficients, (1 - alpha/2) * 100)
    mean_coef = np.mean(coefficients)
    
    # 0이 신뢰구간에 포함되지 않으면 유의
    significant = (lower > 0) or (upper < 0)
    
    return mean_coef, (lower, upper), significant


def nonparametric_correlation(df, y_var, x_var):
    """
    비모수적 상관 분석 (Spearman, Kendall).
    정규성 가정이 필요 없어 소표본에 강건.
    """
    df_clean = df.dropna(subset=[y_var, x_var])
    
    # 자산별 평균으로 축약 (cross-sectional)
    df_agg = df_clean.groupby('symbol').agg({
        y_var: 'mean',
        x_var: 'first'  # TDT는 시간 불변
    }).reset_index()
    
    spearman_r, spearman_p = spearmanr(df_agg[x_var], df_agg[y_var])
    kendall_tau, kendall_p = kendalltau(df_agg[x_var], df_agg[y_var])
    
    return {
        'spearman_r': spearman_r,
        'spearman_p': spearman_p,
        'kendall_tau': kendall_tau,
        'kendall_p': kendall_p,
        'n_assets': len(df_agg)
    }


def group_comparison_test(df, y_var, x_var, threshold=50):
    """
    그룹 비교 검정: High-TDT vs Low-TDT.
    Mann-Whitney U (비모수), t-test (모수).
    """
    df_clean = df.dropna(subset=[y_var, x_var])
    
    # TDT 기준 그룹 분리
    high_tdt = df_clean[df_clean[x_var] >= threshold][y_var]
    low_tdt = df_clean[df_clean[x_var] < threshold][y_var]
    
    if len(high_tdt) < 10 or len(low_tdt) < 10:
        return None
    
    # Mann-Whitney U test (비모수)
    u_stat, u_pvalue = mannwhitneyu(high_tdt, low_tdt, alternative='two-sided')
    
    # t-test (모수)
    t_stat, t_pvalue = ttest_ind(high_tdt, low_tdt, equal_var=False)
    
    return {
        'high_tdt_mean': high_tdt.mean(),
        'low_tdt_mean': low_tdt.mean(),
        'difference': high_tdt.mean() - low_tdt.mean(),
        'mann_whitney_p': u_pvalue,
        'ttest_p': t_pvalue,
        'n_high': len(high_tdt),
        'n_low': len(low_tdt)
    }


def time_cluster_regression(df, y_var, x_vars):
    """
    시간(날짜) 기준 클러스터링.
    클러스터 수: 자산 18개 → 날짜 180개로 증가.
    """
    df_clean = df.dropna(subset=[y_var] + x_vars)
    
    X = df_clean[x_vars].copy()
    X = sm.add_constant(X)
    y = df_clean[y_var]
    
    # 날짜 기준 클러스터링
    groups = df_clean['date']
    model = OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': groups})
    
    return model


def cross_sectional_regression(df, y_var, x_var):
    """
    횡단면 회귀: 자산별 평균값으로 분석.
    각 자산이 하나의 관측치 → 단순 OLS 가능.
    """
    df_clean = df.dropna(subset=[y_var, x_var, 'market_cap'])
    
    # 자산별 집계
    df_agg = df_clean.groupby('symbol').agg({
        y_var: 'mean',
        x_var: 'first',
        'market_cap': 'mean'
    }).reset_index()
    
    df_agg['market_cap_log'] = np.log(df_agg['market_cap'] + 1)
    
    X = df_agg[[x_var, 'market_cap_log']]
    X = sm.add_constant(X)
    y = df_agg[y_var]
    
    model = OLS(y, X).fit()
    
    return model, df_agg


def main():
    base_path = os.path.dirname(__file__)
    panel_path = os.path.join(base_path, '../../data/processed/final_panel_data.csv')
    output_path = os.path.join(base_path, '../../data/processed/alternative_analysis_results.csv')
    
    print("=" * 70)
    print("Alternative Robust Analysis")
    print("(Overcoming small cluster problem)")
    print("=" * 70)
    
    df = pd.read_csv(panel_path)
    df['market_cap_log'] = np.log(df['market_cap'] + 1)
    
    # 거래량 0 제외
    df = df[df['volume'] > 0]
    print(f"\nLoaded {len(df)} observations (after removing zero-volume)")
    
    results = []
    
    # ============================================
    # 1. 부트스트랩 신뢰구간
    # ============================================
    print("\n" + "=" * 70)
    print("[Method 1] Bootstrap Confidence Interval (n=1000)")
    print("=" * 70)
    
    for y_var, y_name in [('volatility_7d', 'Volatility'), ('daily_return', 'Return')]:
        coef, ci, sig = bootstrap_confidence_interval(df, y_var, 'tdt_score', n_bootstrap=1000)
        if coef is not None:
            print(f"\n{y_name}:")
            print(f"  Coefficient: {coef:.6f}")
            print(f"  95% CI: [{ci[0]:.6f}, {ci[1]:.6f}]")
            print(f"  Significant (0 not in CI): {sig}")
            results.append({
                'Method': 'Bootstrap',
                'Y_Variable': y_name,
                'Coefficient': coef,
                'CI_Lower': ci[0],
                'CI_Upper': ci[1],
                'Significant': sig
            })
    
    # ============================================
    # 2. 비모수적 상관 분석
    # ============================================
    print("\n" + "=" * 70)
    print("[Method 2] Nonparametric Correlation (Cross-sectional)")
    print("=" * 70)
    
    for y_var, y_name in [('volatility_7d', 'Volatility'), ('illiquidity', 'Illiquidity')]:
        corr = nonparametric_correlation(df, y_var, 'tdt_score')
        if corr:
            print(f"\n{y_name} vs TDT (n={corr['n_assets']} assets):")
            print(f"  Spearman ρ: {corr['spearman_r']:.4f}, p={corr['spearman_p']:.4f}")
            print(f"  Kendall τ: {corr['kendall_tau']:.4f}, p={corr['kendall_p']:.4f}")
            results.append({
                'Method': 'Spearman',
                'Y_Variable': y_name,
                'Coefficient': corr['spearman_r'],
                'p_value': corr['spearman_p'],
                'n_assets': corr['n_assets']
            })
            results.append({
                'Method': 'Kendall',
                'Y_Variable': y_name,
                'Coefficient': corr['kendall_tau'],
                'p_value': corr['kendall_p'],
                'n_assets': corr['n_assets']
            })
    
    # ============================================
    # 3. 그룹 비교 (High vs Low TDT)
    # ============================================
    print("\n" + "=" * 70)
    print("[Method 3] Group Comparison (High-TDT vs Low-TDT)")
    print("=" * 70)
    
    for y_var, y_name in [('volatility_7d', 'Volatility'), ('daily_return', 'Return')]:
        comp = group_comparison_test(df, y_var, 'tdt_score', threshold=50)
        if comp:
            print(f"\n{y_name}:")
            print(f"  High-TDT mean: {comp['high_tdt_mean']:.6f} (n={comp['n_high']})")
            print(f"  Low-TDT mean: {comp['low_tdt_mean']:.6f} (n={comp['n_low']})")
            print(f"  Difference: {comp['difference']:.6f}")
            print(f"  Mann-Whitney p: {comp['mann_whitney_p']:.4f}")
            print(f"  t-test p: {comp['ttest_p']:.4f}")
            results.append({
                'Method': 'Group_Comparison',
                'Y_Variable': y_name,
                'High_TDT_Mean': comp['high_tdt_mean'],
                'Low_TDT_Mean': comp['low_tdt_mean'],
                'Difference': comp['difference'],
                'Mann_Whitney_p': comp['mann_whitney_p'],
                't_test_p': comp['ttest_p']
            })
    
    # ============================================
    # 4. 시간 클러스터 회귀
    # ============================================
    print("\n" + "=" * 70)
    print("[Method 4] Time-Clustered Regression (cluster by date)")
    print("=" * 70)
    
    model_time = time_cluster_regression(
        df, 
        'volatility_7d', 
        ['tdt_score', 'market_cap_log']
    )
    
    if model_time:
        print(f"\nClusters: {df['date'].nunique()} dates")
        print(model_time.summary().tables[1])
        results.append({
            'Method': 'Time_Cluster',
            'Y_Variable': 'Volatility',
            'Variable': 'tdt_score',
            'Coefficient': model_time.params['tdt_score'],
            't_stat': model_time.tvalues['tdt_score'],
            'p_value': model_time.pvalues['tdt_score']
        })
    
    # ============================================
    # 5. 횡단면 회귀 (자산별 평균)
    # ============================================
    print("\n" + "=" * 70)
    print("[Method 5] Cross-Sectional Regression (asset-level means)")
    print("=" * 70)
    
    model_cs, df_agg = cross_sectional_regression(df, 'volatility_7d', 'tdt_score')
    
    if model_cs:
        print(f"\nN = {len(df_agg)} assets")
        print(model_cs.summary())
        results.append({
            'Method': 'Cross_Section',
            'Y_Variable': 'Volatility',
            'Variable': 'tdt_score',
            'Coefficient': model_cs.params['tdt_score'],
            't_stat': model_cs.tvalues['tdt_score'],
            'p_value': model_cs.pvalues['tdt_score'],
            'R_squared': model_cs.rsquared
        })
    
    # ============================================
    # 결과 저장
    # ============================================
    df_results = pd.DataFrame(results)
    df_results.to_csv(output_path, index=False)
    
    print("\n" + "=" * 70)
    print("SUMMARY OF ALTERNATIVE ANALYSES")
    print("=" * 70)
    
    # 유의한 결과 하이라이트
    print("\n[Significant Results]")
    for _, row in df_results.iterrows():
        p_col = None
        for col in ['p_value', 'Mann_Whitney_p', 't_test_p']:
            if col in row and pd.notna(row.get(col)):
                p_col = col
                break
        
        if p_col and row[p_col] < 0.05:
            print(f"  ✅ {row['Method']} - {row.get('Y_Variable', '')}: p={row[p_col]:.4f}")
        elif 'Significant' in row and row['Significant']:
            print(f"  ✅ {row['Method']} - {row.get('Y_Variable', '')}: Significant")
    
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
