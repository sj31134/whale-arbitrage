"""
Layer 1: 실제 가격/거래량 시계열 수집 (CoinGecko Historical API)

시뮬레이션이 아닌 실제 시장 데이터를 수집합니다.
"""

import requests
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime, timedelta

# CoinGecko API 설정
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

# API Rate Limit 대응 (무료 tier: 10-30 calls/minute)
RATE_LIMIT_DELAY = 6  # seconds between calls


def fetch_historical_prices(coin_id: str, days: int = 180, vs_currency: str = 'usd') -> pd.DataFrame:
    """
    CoinGecko에서 특정 코인의 과거 가격/거래량 시계열 수집.
    
    Args:
        coin_id: CoinGecko 코인 ID (예: 'ondo-finance')
        days: 수집할 과거 일수
        vs_currency: 기준 통화
    
    Returns:
        DataFrame with columns: [date, price, volume, market_cap]
    """
    url = f"{COINGECKO_BASE_URL}/coins/{coin_id}/market_chart"
    params = {
        'vs_currency': vs_currency,
        'days': days,
        'interval': 'daily'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 429:
            print(f"Rate limited. Waiting 60 seconds...")
            time.sleep(60)
            response = requests.get(url, params=params, timeout=30)
        
        if response.status_code != 200:
            print(f"Error fetching {coin_id}: {response.status_code}")
            return pd.DataFrame()
        
        data = response.json()
        
        # 타임스탬프를 날짜로 변환
        prices = data.get('prices', [])
        volumes = data.get('total_volumes', [])
        market_caps = data.get('market_caps', [])
        
        if not prices:
            return pd.DataFrame()
        
        df = pd.DataFrame({
            'timestamp': [p[0] for p in prices],
            'price': [p[1] for p in prices],
            'volume': [v[1] for v in volumes] if volumes else [0] * len(prices),
            'market_cap': [m[1] for m in market_caps] if market_caps else [0] * len(prices)
        })
        
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.strftime('%Y-%m-%d')
        df['coin_id'] = coin_id
        
        return df[['date', 'coin_id', 'price', 'volume', 'market_cap']]
        
    except Exception as e:
        print(f"Exception fetching {coin_id}: {e}")
        return pd.DataFrame()


def fetch_all_historical_data(rwa_list_path: str, output_path: str, days: int = 180):
    """
    RWA 리스트의 모든 토큰에 대해 과거 데이터 수집.
    """
    df_rwa = pd.read_csv(rwa_list_path)
    
    all_data = []
    total = len(df_rwa)
    
    print(f"Fetching historical data for {total} tokens ({days} days each)...")
    print("This may take several minutes due to API rate limits.\n")
    
    for idx, row in df_rwa.iterrows():
        coin_id = row['coingecko_id']
        symbol = row['symbol']
        
        print(f"[{idx+1}/{total}] Fetching {symbol} ({coin_id})...")
        
        df_hist = fetch_historical_prices(coin_id, days=days)
        
        if not df_hist.empty:
            df_hist['symbol'] = symbol
            all_data.append(df_hist)
            print(f"  ✓ Got {len(df_hist)} days of data")
        else:
            print(f"  ✗ No data available")
        
        # Rate limiting
        if idx < total - 1:
            time.sleep(RATE_LIMIT_DELAY)
    
    if all_data:
        df_all = pd.concat(all_data, ignore_index=True)
        df_all.to_csv(output_path, index=False)
        print(f"\n✅ Saved {len(df_all)} total observations to {output_path}")
        return df_all
    else:
        print("\n❌ No data collected")
        return pd.DataFrame()


def calculate_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    수익률, 변동성, 유동성 지표 계산.
    """
    df = df.copy()
    df = df.sort_values(['symbol', 'date'])
    
    result_dfs = []
    
    for symbol in df['symbol'].unique():
        df_coin = df[df['symbol'] == symbol].copy()
        
        # 일별 수익률
        df_coin['daily_return'] = df_coin['price'].pct_change()
        
        # Amihud Illiquidity: |return| / volume
        df_coin['illiquidity'] = df_coin['daily_return'].abs() / df_coin['volume'].replace(0, np.nan)
        
        # 7일 롤링 변동성
        df_coin['volatility_7d'] = df_coin['daily_return'].rolling(window=7, min_periods=3).std()
        
        # 급락 이벤트 (2% 이상 하락)
        df_coin['tail_event'] = (df_coin['daily_return'] < -0.02).astype(int)
        
        result_dfs.append(df_coin)
    
    return pd.concat(result_dfs, ignore_index=True)


def main():
    base_path = os.path.dirname(__file__)
    rwa_list_path = os.path.join(base_path, '../../data/raw/rwa_list.csv')
    historical_output = os.path.join(base_path, '../../data/raw/historical_prices.csv')
    panel_output = os.path.join(base_path, '../../data/processed/real_panel_data.csv')
    
    print("=" * 60)
    print("Layer 1: Real Historical Data Collection")
    print("=" * 60)
    
    # 과거 데이터 수집
    df_historical = fetch_all_historical_data(rwa_list_path, historical_output, days=180)
    
    if not df_historical.empty:
        # 파생 지표 계산
        print("\nCalculating derived metrics...")
        df_panel = calculate_derived_metrics(df_historical)
        df_panel.to_csv(panel_output, index=False)
        print(f"✅ Panel data saved to {panel_output}")
        
        # 요약 통계
        print("\n=== Summary Statistics ===")
        print(f"Total observations: {len(df_panel)}")
        print(f"Tokens: {df_panel['symbol'].nunique()}")
        print(f"Date range: {df_panel['date'].min()} ~ {df_panel['date'].max()}")
        print(f"\nSample:")
        print(df_panel.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
