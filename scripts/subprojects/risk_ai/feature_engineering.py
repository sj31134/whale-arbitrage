"""
Project 3: Risk AI Feature Engineering
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"

class FeatureEngineer:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)

    def load_raw_data(self, start_date="2023-01-01"):
        """데이터 로드 및 병합 (Daily)"""
        query = f"""
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
        AND f.date >= '{start_date}'
        ORDER BY f.date
        """
        df = pd.read_sql(query, self.conn)
        df['date'] = pd.to_datetime(df['date'])
        
        # 결측치 처리 (Forward Fill)
        df = df.ffill().dropna()
        
        return df

    def create_features(self, df):
        """파생변수 생성"""
        df = df.copy()
        
        # 1. 고래 집중도 변화율 (7일)
        # top100_richest_pct 데이터가 드물게(일별이 아닐 수 있음) 있을 수 있으므로 주의
        df['whale_conc_change_7d'] = df['top100_richest_pct'].pct_change(7)
        # NULL 처리: 0으로 채움 (변화 없음)
        df['whale_conc_change_7d'] = df['whale_conc_change_7d'].fillna(0)
        
        # 2. 펀딩비 Z-Score (30일)
        df['funding_mean'] = df['avg_funding_rate'].rolling(30).mean()
        df['funding_std'] = df['avg_funding_rate'].rolling(30).std()
        # 분모가 0이 되는 경우 방지
        df['funding_rate_zscore'] = np.where(
            df['funding_std'] != 0,
            (df['avg_funding_rate'] - df['funding_mean']) / df['funding_std'],
            0
        )
        # NULL 처리: 0으로 채움 (평균과 동일)
        df['funding_rate_zscore'] = df['funding_rate_zscore'].fillna(0)
        
        # 3. OI 변화율 (7일)
        df['oi_growth_7d'] = df['sum_open_interest'].pct_change(7)
        # NULL 처리: 0으로 채움 (변화 없음)
        df['oi_growth_7d'] = df['oi_growth_7d'].fillna(0)
        
        # 4. Long/Short Ratio Normalization (0.5가 중립이 되도록)
        # Ratio가 없으면(0.0) 0.5로 가정
        df['long_short_ratio'] = df['long_short_ratio'].replace(0, 1.0) 
        # L/S Ratio = Longs / Shorts -> Long % = Ratio / (1 + Ratio)
        df['long_position_pct'] = df['long_short_ratio'] / (1 + df['long_short_ratio'])
        
        # 5. 변동성 변화 (오늘 변동성 / 7일 평균 변동성)
        vol_rolling_mean = df['volatility_24h'].rolling(7).mean()
        # 분모가 0이면 1.0으로 설정 (변동 없음)
        df['volatility_ratio'] = np.where(
            vol_rolling_mean != 0,
            df['volatility_24h'] / vol_rolling_mean,
            1.0
        )
        # NULL 처리
        df['volatility_ratio'] = df['volatility_ratio'].fillna(1.0)
        
        # 타겟 변수 생성: "다음날" 고변동성 여부
        # volatility_24h 데이터가 이제 정상적으로 수집되므로 원래 방법 사용
        df['next_day_volatility'] = df['volatility_24h'].shift(-1)
        
        # 고변동성 정의: 상위 20% (quantile 0.8) 또는 절대 수치 5% 이상
        # 절대 수치 기준도 함께 고려
        if df['volatility_24h'].max() > 0:
            # 방법 1: 상위 20% 기준
            quantile_threshold = df['volatility_24h'].quantile(0.8)
            # 방법 2: 절대 수치 5% 기준
            absolute_threshold = 0.05
            
            # 두 기준 중 하나라도 만족하면 고변동성
            df['target_high_vol'] = (
                (df['next_day_volatility'] > quantile_threshold) | 
                (df['next_day_volatility'] > absolute_threshold)
            ).astype(int)
        else:
            # volatility 데이터가 없으면 모두 0으로 설정
            df['target_high_vol'] = 0
        
        # 마지막 행의 target은 NULL이므로 0으로 채움
        df['target_high_vol'] = df['target_high_vol'].fillna(0)
        
        # Feature Set
        features = [
            'avg_funding_rate', 'sum_open_interest', 'long_position_pct',
            'whale_conc_change_7d', 'funding_rate_zscore', 'oi_growth_7d',
            'volatility_ratio'
        ]
        
        # 모든 feature가 채워졌는지 확인 후 반환
        # target_high_vol만 제외하고 dropna (target은 마지막 행이 NULL일 수 있음)
        df_clean = df.dropna(subset=features)
        
        return df_clean, features

    def prepare_ml_dataset(self):
        df = self.load_raw_data()
        df, feature_cols = self.create_features(df)
        
        # Train/Test Split (Time Series Split)
        # 2023~2024.09 (Train), 2024.10~Now (Test)
        split_date = "2024-10-01"
        
        train_df = df[df['date'] < split_date]
        test_df = df[df['date'] >= split_date]
        
        return train_df, test_df, feature_cols

