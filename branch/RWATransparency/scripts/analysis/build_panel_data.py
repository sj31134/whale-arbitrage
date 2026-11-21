"""
Panel Data Builder for RWA Analysis

일자별-자산별 패널 데이터를 구축합니다.
종속변수(Y): Illiquidity, Volatility, Tail Risk
설명변수(X): TDT Score (및 구성요소)
통제변수: 시총, BTC 변동성, 거시 지표 등
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def calculate_amihud_illiquidity(returns: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Amihud Illiquidity 지표 계산.
    Amihud = |Return| / Volume (일별)
    """
    # Volume이 0인 경우 NaN 처리
    illiquidity = returns.abs() / volume.replace(0, np.nan)
    return illiquidity

def calculate_rolling_volatility(returns: pd.Series, window: int = 7) -> pd.Series:
    """
    롤링 변동성 계산 (최근 N일 수익률 표준편차).
    """
    return returns.rolling(window=window, min_periods=3).std()

def calculate_tail_risk_event(returns: pd.Series, threshold: float = -0.02) -> pd.Series:
    """
    급락 이벤트 이진 변수 생성.
    threshold 이하(-2%)로 하락하면 1, 아니면 0.
    """
    return (returns < threshold).astype(int)

def generate_synthetic_daily_data(tdt_scores_path: str, days: int = 90):
    """
    분석용 합성 일별 패널 데이터 생성.
    실제 구현 시 CoinGecko historical API로 대체.
    """
    df_tdt = pd.read_csv(tdt_scores_path)
    
    panel_rows = []
    base_date = datetime.now() - timedelta(days=days)
    
    for _, asset_row in df_tdt.iterrows():
        symbol = asset_row['symbol']
        mcap = asset_row['market_cap']
        tdt = asset_row['tdt_equal']
        latency = asset_row['latency_score']
        completeness = asset_row['completeness_score']
        consistency = asset_row['consistency_score']
        
        # 일별 시계열 생성 (시뮬레이션)
        np.random.seed(hash(symbol) % 2**32)
        
        for d in range(days):
            date = base_date + timedelta(days=d)
            
            # 가격 시뮬레이션 (TDT 높을수록 변동성 낮음)
            base_vol = 0.03 * (1 - tdt / 200)  # TDT 높을수록 변동성 감소
            daily_return = np.random.normal(0.0005, base_vol)
            
            # 거래량 시뮬레이션 (TDT 높을수록 유동성 좋음)
            base_volume = mcap * 0.01 * (1 + tdt / 100)
            daily_volume = base_volume * np.random.uniform(0.5, 1.5)
            
            # 거시 충격 시뮬레이션 (더 빈번하고 강한 충격)
            # 다양한 충격 유형: 주기적 충격 + 랜덤 충격
            periodic_shock = 1 if d % 15 == 7 else 0  # 2주마다 충격
            random_shock = 1 if np.random.random() < 0.08 else 0  # 8% 확률 랜덤 충격
            shock = max(periodic_shock, random_shock)
            
            if shock:
                # TDT 낮을수록 충격에 더 민감 (더 강한 효과)
                shock_sensitivity = (100 - tdt) / 100  # 0~1 범위 (TDT 낮을수록 1에 가까움)
                shock_impact = 0.04 * shock_sensitivity  # 최대 4% 하락
                daily_return -= shock_impact
            
            panel_rows.append({
                'date': date.strftime('%Y-%m-%d'),
                'symbol': symbol,
                'market_cap': mcap,
                'daily_return': round(daily_return, 6),
                'volume': round(daily_volume, 2),
                'tdt_score': tdt,
                'latency_score': latency,
                'completeness_score': completeness,
                'consistency_score': consistency,
                'macro_shock': shock
            })
    
    df_panel = pd.DataFrame(panel_rows)
    
    # 파생 변수 계산
    for symbol in df_panel['symbol'].unique():
        mask = df_panel['symbol'] == symbol
        returns = df_panel.loc[mask, 'daily_return']
        volume = df_panel.loc[mask, 'volume']
        
        df_panel.loc[mask, 'illiquidity'] = calculate_amihud_illiquidity(returns, volume)
        df_panel.loc[mask, 'volatility'] = calculate_rolling_volatility(returns)
        df_panel.loc[mask, 'tail_event'] = calculate_tail_risk_event(returns)
    
    return df_panel


def main():
    base_path = os.path.dirname(__file__)
    tdt_scores_path = os.path.join(base_path, '../../data/processed/tdt_scores.csv')
    output_path = os.path.join(base_path, '../../data/processed/panel_data.csv')
    
    print("=== Building Panel Data ===")
    df_panel = generate_synthetic_daily_data(tdt_scores_path, days=180)
    
    df_panel.to_csv(output_path, index=False)
    print(f"Panel data generated: {len(df_panel)} observations")
    print(f"Assets: {df_panel['symbol'].unique()}")
    print(f"Date range: {df_panel['date'].min()} ~ {df_panel['date'].max()}")
    print(f"\nSample data:")
    print(df_panel.head(10).to_string(index=False))
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
