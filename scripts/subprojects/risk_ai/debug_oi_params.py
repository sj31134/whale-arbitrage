#!/usr/bin/env python3
"""
Binance Futures Open Interest API 파라미터 디버깅 스크립트
"""
import requests
import time
from datetime import datetime, timedelta

OI_ENDPOINT = "https://fapi.binance.com/futures/data/openInterestHist"

def test_params(symbol, period, limit, days_ago=1):
    print(f"Testing: symbol={symbol}, period={period}, limit={limit}, days_ago={days_ago}")
    
    end_time = int(time.time() * 1000)
    start_time = end_time - (days_ago * 24 * 60 * 60 * 1000)
    
    params = {
        "symbol": symbol,
        "period": period,
        "limit": limit,
        "startTime": start_time,
        "endTime": end_time
    }
    
    try:
        response = requests.get(OI_ENDPOINT, params=params, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Returned {len(data)} records.")
            if data:
                print(f"First: {data[0]}")
                print(f"Last: {data[-1]}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {e}")
    print("-" * 40)

def main():
    # Case 1: 1h period, 1 day range, limit 500 (Standard)
    test_params("BTCUSDT", "1h", 500, days_ago=1)
    
    # Case 2: 1h period, 30 days range (Likely fail if too many data points for 500 limit, but API might truncate)
    test_params("BTCUSDT", "1h", 500, days_ago=30)
    
    # Case 3: 1d period, 30 days range
    test_params("BTCUSDT", "1d", 500, days_ago=30)
    
    # Case 5: 60 days ago
    test_params("BTCUSDT", "1h", 500, days_ago=60)
    test_params("BTCUSDT", "1d", 500, days_ago=60)

if __name__ == "__main__":
    main()

