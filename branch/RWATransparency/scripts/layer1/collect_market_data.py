import requests
import pandas as pd
import os
import time
from datetime import datetime

def fetch_coingecko_market_data(ids, vs_currency='usd'):
    """
    Fetch market data (price, volume, market cap) from CoinGecko.
    """
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        'vs_currency': vs_currency,
        'ids': ','.join(ids),
        'order': 'market_cap_desc',
        'per_page': 100,
        'page': 1,
        'sparkline': False
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data: {response.status_code}")
        return []

def main():
    # Load RWA list
    rwa_list_path = os.path.join(os.path.dirname(__file__), '../../data/raw/rwa_list.csv')
    df_rwa = pd.read_csv(rwa_list_path)
    ids = df_rwa['coingecko_id'].tolist()
    
    print(f"Fetching data for {len(ids)} RWA tokens...")
    data = fetch_coingecko_market_data(ids)
    
    if data:
        df_market = pd.DataFrame(data)
        # Keep relevant columns
        cols = ['id', 'symbol', 'name', 'current_price', 'market_cap', 'total_volume', 'price_change_percentage_24h']
        df_market = df_market[cols]
        df_market['timestamp'] = datetime.now().isoformat()
        
        # Save to raw data
        output_path = os.path.join(os.path.dirname(__file__), '../../data/raw/market_data_latest.csv')
        df_market.to_csv(output_path, index=False)
        print(f"Saved latest market data to {output_path}")

if __name__ == "__main__":
    main()
