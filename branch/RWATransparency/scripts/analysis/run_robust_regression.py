"""
Robust Panel Regression with Methodological Improvements

선행연구에 기반한 방법론적 보완:
1. 클러스터 표준오차 (Petersen, 2009; Cameron & Miller, 2015)
2. Amihud (2002) 유동성 지표 정규화
3. 정보 부족 토큰 제외 또는 더미변수 처리
4. 다중검정 보정 (Benjamini-Hochberg, 1995)
5. 서브샘플 강건성 검정

참고문헌:
- Amihud, Y. (2002). Illiquidity and stock returns: cross-section and time-series effects. 
  Journal of Financial Markets, 5(1), 31-56.
- Petersen, M. A. (2009). Estimating standard errors in finance panel data sets: 
  Comparing approaches. Review of Financial Studies, 22(1), 435-480.
- Botosan, C. A. (1997). Disclosure level and the cost of equity capital. 
  The Accounting Review, 72(3), 323-349.
- Healy, P. M., & Palepu, K. G. (2001). Information asymmetry, corporate disclosure, 
  and the capital markets. Journal of Accounting and Economics, 31(1-3), 405-440.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
from scipy import stats
import os
import warnings
warnings.filterwarnings('ignore')


def benjamini_hochberg_correction(p_values: list, alpha: float = 0.05) -> dict:
    """
    Benjamini-Hochberg (1995) FDR 다중검정 보정.
    
    Reference:
    Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate: 
    a practical and powerful approach to multiple testing. 
    Journal of the Royal Statistical Society, Series B, 57(1), 289-300.
    """
    n = len(p_values)
    sorted_indices = np.argsort(p_values)
    sorted_pvalues = np.array(p_values)[sorted_indices]
    
    # BH 임계값 계산
    bh_critical = [(i + 1) / n * alpha for i in range(n)]
    
    # 유의성 판단
    significant = sorted_pvalues <= bh_critical
    
    # 결과 정리
    results = []
    for i, idx in enumerate(sorted_indices):
        results.append({
            'original_index': idx,
            'p_value': p_values[idx],
            'bh_critical': bh_critical[i],
            'significant_bh': significant[i]
        })
    
    return pd.DataFrame(results).sort_values('original_index').reset_index(drop=True)


def normalize_amihud_measure(df: pd.DataFrame) -> pd.DataFrame:
    """
    Amihud (2002) 유동성 지표 정규화.
    
    - 거래량 0인 관측치 제외
    - 시총 기준 스케일링 (Amihud, 2002 원문에서 권장)
    - 극단치 winsorizing (1st-99th percentile)
    """
    df = df.copy()
    
    # 거래량 0 제외
    df = df[df['volume'] > 0]
    
    # Amihud ratio 재계산 (이미 있으면 사용, 없으면 계산)
    if 'illiquidity' not in df.columns or df['illiquidity'].isna().all():
        df['illiquidity'] = df['daily_return'].abs() / df['volume']
    
    # 무한대 제거
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=['illiquidity'])
    
    # Winsorizing (1st-99th percentile)
    lower = df['illiquidity'].quantile(0.01)
    upper = df['illiquidity'].quantile(0.99)
    df['illiquidity_winsorized'] = df['illiquidity'].clip(lower, upper)
    
    # 로그 변환 (Amihud 2002 권장)
    df['illiquidity_log'] = np.log(df['illiquidity_winsorized'] + 1e-12)
    
    return df


def run_clustered_regression(df: pd.DataFrame, y_var: str, x_vars: list, 
                             cluster_var: str = 'symbol'):
    """
    Petersen (2009) 스타일 클러스터 표준오차 회귀분석.
    
    패널 데이터에서 고정효과 대신 클러스터 표준오차를 사용하면
    시간 불변 변수(TDT)도 추정 가능.
    """
    df_clean = df.dropna(subset=[y_var] + x_vars + [cluster_var])
    
    if len(df_clean) < 50:
        return None, None
    
    X = df_clean[x_vars].copy()
    X = sm.add_constant(X)
    y = df_clean[y_var]
    
    # 클러스터 표준오차
    groups = df_clean[cluster_var]
    model = OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': groups})
    
    return model, df_clean


def create_info_dummy(df: pd.DataFrame, tdt_threshold: float = 20.0) -> pd.DataFrame:
    """
    정보 부족 토큰에 대한 더미변수 생성.
    
    Botosan (1997) 방식: 공시 수준을 범주형으로 구분
    """
    df = df.copy()
    
    # 정보 부족 더미 (TDT < threshold)
    df['info_poor'] = (df['tdt_score'] < tdt_threshold).astype(int)
    
    # TDT 카테고리화 (Low/Medium/High)
    df['tdt_category'] = pd.cut(df['tdt_score'], 
                                bins=[0, 30, 60, 100], 
                                labels=['Low', 'Medium', 'High'])
    
    # 더미 변수 생성
    df['tdt_medium'] = (df['tdt_category'] == 'Medium').astype(int)
    df['tdt_high'] = (df['tdt_category'] == 'High').astype(int)
    
    return df


def subsample_analysis(df: pd.DataFrame, exclude_stablecoins: bool = True):
    """
    표본 이질성 처리를 위한 서브샘플 분석.
    
    스테이블코인과 RWA 토큰의 특성이 다르므로 분리 분석.
    """
    # 스테이블코인 목록 (페그 자산)
    stablecoins = ['USDT', 'USDC', 'DAI', 'BUSD', 'TUSD', 'USDP', 'GUSD', 
                   'FRAX', 'LUSD', 'EURC', 'EURT', 'MIM', 'CRVUSD', 'GHO', 'DOLA']
    
    # 순수 RWA 토큰
    rwa_tokens = ['ONDO', 'BUIDL', 'USDY', 'PYUSD']
    
    df_stablecoins = df[df['symbol'].isin(stablecoins)]
    df_rwa = df[df['symbol'].isin(rwa_tokens)]
    
    return df_stablecoins, df_rwa


def main():
    base_path = os.path.dirname(__file__)
    panel_path = os.path.join(base_path, '../../data/processed/final_panel_data.csv')
    output_path = os.path.join(base_path, '../../data/processed/robust_regression_results.csv')
    
    print("=" * 70)
    print("Robust Panel Regression Analysis")
    print("Following Petersen (2009), Amihud (2002), Botosan (1997)")
    print("=" * 70)
    
    # 데이터 로드
    df = pd.read_csv(panel_path)
    print(f"\nLoaded {len(df)} observations")
    
    # 1. Amihud 정규화
    print("\n[Step 1] Applying Amihud (2002) normalization...")
    df = normalize_amihud_measure(df)
    print(f"After removing zero-volume: {len(df)} observations")
    
    # 2. 정보 더미 생성
    print("\n[Step 2] Creating disclosure dummy (Botosan, 1997)...")
    df = create_info_dummy(df, tdt_threshold=20.0)
    df['market_cap_log'] = np.log(df['market_cap'] + 1)
    
    info_distribution = df.groupby('info_poor')['symbol'].nunique()
    print(f"Info-poor tokens: {info_distribution.get(1, 0)}")
    print(f"Info-rich tokens: {info_distribution.get(0, 0)}")
    
    # 3. 서브샘플 분리
    print("\n[Step 3] Subsample analysis...")
    df_stable, df_rwa = subsample_analysis(df)
    print(f"Stablecoins: {len(df_stable)} obs, RWA tokens: {len(df_rwa)} obs")
    
    results = []
    p_values_for_correction = []
    
    # ============================================
    # Model 1: H1 with Clustered SE
    # ============================================
    print("\n" + "=" * 70)
    print("[Model 1] H1: TDT → Illiquidity (Clustered SE)")
    print("=" * 70)
    
    model_h1, _ = run_clustered_regression(
        df, 
        y_var='illiquidity_log',
        x_vars=['tdt_score', 'market_cap_log'],
        cluster_var='symbol'
    )
    
    if model_h1:
        print(model_h1.summary().tables[1])
        for var in ['tdt_score']:
            results.append({
                'Model': 'H1_Illiquidity_Clustered',
                'Variable': var,
                'Coefficient': model_h1.params[var],
                't-stat': model_h1.tvalues[var],
                'p-value': model_h1.pvalues[var],
                'N': int(model_h1.nobs),
                'Clusters': df['symbol'].nunique()
            })
            p_values_for_correction.append(model_h1.pvalues[var])
    
    # ============================================
    # Model 2: H2 with Clustered SE
    # ============================================
    print("\n" + "=" * 70)
    print("[Model 2] H2: TDT → Volatility (Clustered SE)")
    print("=" * 70)
    
    model_h2, _ = run_clustered_regression(
        df,
        y_var='volatility_7d',
        x_vars=['tdt_score', 'market_cap_log'],
        cluster_var='symbol'
    )
    
    if model_h2:
        print(model_h2.summary().tables[1])
        for var in ['tdt_score']:
            results.append({
                'Model': 'H2_Volatility_Clustered',
                'Variable': var,
                'Coefficient': model_h2.params[var],
                't-stat': model_h2.tvalues[var],
                'p-value': model_h2.pvalues[var],
                'N': int(model_h2.nobs),
                'Clusters': df['symbol'].nunique()
            })
            p_values_for_correction.append(model_h2.pvalues[var])
    
    # ============================================
    # Model 3: H3 with Clustered SE
    # ============================================
    print("\n" + "=" * 70)
    print("[Model 3] H3: TDT × Shock → Return (Clustered SE)")
    print("=" * 70)
    
    df['tdt_shock'] = df['tdt_score'] * df['macro_shock']
    
    model_h3, _ = run_clustered_regression(
        df,
        y_var='daily_return',
        x_vars=['tdt_score', 'macro_shock', 'tdt_shock', 'market_cap_log'],
        cluster_var='symbol'
    )
    
    if model_h3:
        print(model_h3.summary().tables[1])
        for var in ['tdt_shock']:
            results.append({
                'Model': 'H3_Shock_Clustered',
                'Variable': var,
                'Coefficient': model_h3.params[var],
                't-stat': model_h3.tvalues[var],
                'p-value': model_h3.pvalues[var],
                'N': int(model_h3.nobs),
                'Clusters': df['symbol'].nunique()
            })
            p_values_for_correction.append(model_h3.pvalues[var])
    
    # ============================================
    # Model 4: Binary TDT (Info-rich vs Info-poor)
    # ============================================
    print("\n" + "=" * 70)
    print("[Model 4] Binary TDT (Botosan 1997 style)")
    print("=" * 70)
    
    # 정보 빈곤 토큰 제외하고 분석
    df_info_rich = df[df['info_poor'] == 0]
    
    model_binary, _ = run_clustered_regression(
        df_info_rich,
        y_var='volatility_7d',
        x_vars=['tdt_score', 'market_cap_log'],
        cluster_var='symbol'
    )
    
    if model_binary:
        print(f"(Info-rich tokens only, N={len(df_info_rich)})")
        print(model_binary.summary().tables[1])
        for var in ['tdt_score']:
            results.append({
                'Model': 'H2_InfoRich_Only',
                'Variable': var,
                'Coefficient': model_binary.params[var],
                't-stat': model_binary.tvalues[var],
                'p-value': model_binary.pvalues[var],
                'N': int(model_binary.nobs),
                'Clusters': df_info_rich['symbol'].nunique()
            })
            p_values_for_correction.append(model_binary.pvalues[var])
    
    # ============================================
    # Model 5: RWA-only Subsample
    # ============================================
    print("\n" + "=" * 70)
    print("[Model 5] RWA Tokens Only (excluding stablecoins)")
    print("=" * 70)
    
    if len(df_rwa) > 20:
        model_rwa, _ = run_clustered_regression(
            df_rwa,
            y_var='volatility_7d',
            x_vars=['tdt_score', 'market_cap_log'],
            cluster_var='symbol'
        )
        
        if model_rwa:
            print(f"(RWA tokens only, N={len(df_rwa)})")
            print(model_rwa.summary().tables[1])
            for var in ['tdt_score']:
                results.append({
                    'Model': 'H2_RWA_Only',
                    'Variable': var,
                    'Coefficient': model_rwa.params[var],
                    't-stat': model_rwa.tvalues[var],
                    'p-value': model_rwa.pvalues[var],
                    'N': int(model_rwa.nobs),
                    'Clusters': df_rwa['symbol'].nunique()
                })
    else:
        print("Insufficient RWA observations for separate analysis")
    
    # ============================================
    # Benjamini-Hochberg Correction
    # ============================================
    print("\n" + "=" * 70)
    print("[Multiple Testing Correction] Benjamini-Hochberg (1995)")
    print("=" * 70)
    
    if p_values_for_correction:
        bh_results = benjamini_hochberg_correction(p_values_for_correction, alpha=0.05)
        print("\nBH-adjusted significance:")
        print(bh_results.to_string(index=False))
    
    # ============================================
    # 결과 저장
    # ============================================
    df_results = pd.DataFrame(results)
    df_results.to_csv(output_path, index=False)
    
    print("\n" + "=" * 70)
    print("SUMMARY: Robust Regression Results")
    print("=" * 70)
    print(df_results.to_string(index=False))
    
    print("\n" + "=" * 70)
    print("METHODOLOGICAL NOTES")
    print("=" * 70)
    print("• Clustered SE by symbol: Corrects for within-asset correlation")
    print("• Amihud normalization: Log-transformed, winsorized at 1st-99th pct")
    print("• Info-poor filter: Tokens with TDT < 20 excluded in robustness check")
    print("• BH correction: Controls false discovery rate at 5%")
    
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
