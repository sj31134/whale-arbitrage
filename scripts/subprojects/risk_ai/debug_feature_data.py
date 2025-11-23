#!/usr/bin/env python3
"""Feature Engineering 데이터 로딩 디버깅"""

import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"

conn = sqlite3.connect(DB_PATH)

# 1. 각 테이블 데이터 확인
print("=== 테이블별 데이터 확인 ===")
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM binance_futures_metrics WHERE symbol='BTCUSDT'")
result = cursor.fetchone()
print(f"binance_futures_metrics (BTCUSDT): {result[0]}건, {result[1]} ~ {result[2]}")

cursor.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM bitinfocharts_whale WHERE coin='BTC'")
result = cursor.fetchone()
print(f"bitinfocharts_whale (BTC): {result[0]}건, {result[1]} ~ {result[2]}")

# 2. JOIN 결과 확인 (전체)
query = """
SELECT 
    f.date,
    f.symbol,
    f.avg_funding_rate,
    f.sum_open_interest,
    f.long_short_ratio,
    f.volatility_24h,
    b.top100_richest_pct,
    b.avg_transaction_value_btc
FROM binance_futures_metrics f
LEFT JOIN bitinfocharts_whale b ON f.date = b.date AND b.coin = 'BTC'
WHERE f.symbol = 'BTCUSDT'
AND f.date >= '2023-01-01'
ORDER BY f.date
"""

df = pd.read_sql(query, conn)
df['date'] = pd.to_datetime(df['date'])
print(f"\n=== JOIN 결과 (전체) ===")
print(f"총 {len(df)}건")

# 3. Forward Fill 후 확인
df_ffill = df.ffill()
print(f"\n=== Forward Fill 후 NULL 개수 ===")
print(df_ffill.isnull().sum())

# 4. Feature Engineering 시뮬레이션
import numpy as np
df_feat = df_ffill.copy()

# Feature 생성
df_feat['whale_conc_change_7d'] = df_feat['top100_richest_pct'].pct_change(7)
df_feat['funding_mean'] = df_feat['avg_funding_rate'].rolling(30).mean()
df_feat['funding_std'] = df_feat['avg_funding_rate'].rolling(30).std()
df_feat['funding_rate_zscore'] = np.where(
    df_feat['funding_std'] != 0,
    (df_feat['avg_funding_rate'] - df_feat['funding_mean']) / df_feat['funding_std'],
    0
)
df_feat['oi_growth_7d'] = df_feat['sum_open_interest'].pct_change(7)
df_feat['long_short_ratio'] = df_feat['long_short_ratio'].replace(0, 1.0)
df_feat['long_position_pct'] = df_feat['long_short_ratio'] / (1 + df_feat['long_short_ratio'])
df_feat['volatility_ratio'] = df_feat['volatility_24h'] / df_feat['volatility_24h'].rolling(7).mean()
df_feat['next_day_volatility'] = df_feat['volatility_24h'].shift(-1)
threshold = df_feat['volatility_24h'].quantile(0.8)
df_feat['target_high_vol'] = (df_feat['next_day_volatility'] > threshold).astype(int)

features = [
    'avg_funding_rate', 'sum_open_interest', 'long_position_pct',
    'whale_conc_change_7d', 'funding_rate_zscore', 'oi_growth_7d',
    'volatility_ratio'
]

print(f"\n=== Feature 생성 후 NULL 개수 ===")
print(df_feat[features + ['target_high_vol']].isnull().sum())

# 5. Dropna 후 확인
df_clean = df_feat.dropna()
print(f"\n=== Dropna 후 행 수 ===")
print(f"원본: {len(df)}건")
print(f"Feature 생성 후: {len(df_feat)}건")
print(f"Dropna 후: {len(df_clean)}건")

conn.close()

