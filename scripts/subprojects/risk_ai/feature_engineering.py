"""
Project 3: Risk AI Feature Engineering

확장된 기능:
- 기존 정적 변수
- 동적 변수 (1차 미분: 변화율, 2차 미분: 가속도, 기울기)
- 확장 지표 통합 (롱숏비율, Taker비율, 거래소 유입/유출)
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "project.db"

# 동적 변수 계산용 윈도우 크기
SLOPE_WINDOW = 5  # 기울기 계산용 윈도우
STABILITY_WINDOW = 7  # 안정성 계산용 윈도우
MOMENTUM_WINDOW = 3  # 모멘텀 계산용 윈도우

class FeatureEngineer:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)

    def load_raw_data(self, start_date="2023-01-01", coin="BTC"):
        """데이터 로드 및 병합 (Daily) - 확장 지표 포함"""
        symbol = f"{coin}USDT"
        coin_symbol = coin
        
        # 기본 지표 + 확장 지표 조인
        query = f"""
        SELECT 
            f.date,
            f.symbol,
            f.avg_funding_rate,
            f.sum_open_interest,
            f.long_short_ratio,
            f.volatility_24h,
            b.top100_richest_pct,
            b.avg_transaction_value_btc,
            e.long_short_ratio as ext_long_short_ratio,
            e.long_account_pct,
            e.short_account_pct,
            e.taker_buy_sell_ratio,
            e.taker_buy_vol,
            e.taker_sell_vol,
            e.top_trader_long_short_ratio,
            e.bybit_funding_rate,
            e.bybit_oi,
            w.exchange_inflow_usd,
            w.exchange_outflow_usd,
            w.net_flow_usd,
            w.active_addresses,
            w.large_tx_count
        FROM binance_futures_metrics f
        LEFT JOIN bitinfocharts_whale b ON f.date = b.date AND b.coin = '{coin_symbol}'
        LEFT JOIN futures_extended_metrics e ON f.date = e.date AND f.symbol = e.symbol
        LEFT JOIN whale_daily_stats w ON f.date = w.date AND w.coin_symbol = '{coin_symbol}'
        WHERE f.symbol = '{symbol}'
        AND f.date >= '{start_date}'
        ORDER BY f.date
        """
        df = pd.read_sql(query, self.conn)
        df['date'] = pd.to_datetime(df['date'])
        
        # 결측치 처리 (Forward Fill)
        df = df.ffill().fillna(0)
        
        return df

    def create_features(self, df, include_dynamic=True):
        """
        파생변수 생성 (정적 + 동적 변수)
        
        Args:
            df: 원본 데이터프레임
            include_dynamic: 동적 변수 포함 여부 (기본값: True)
        
        Returns:
            df_clean: 정제된 데이터프레임
            features: 특성 목록
        """
        df = df.copy()
        
        # 숫자 컬럼을 명시적으로 float로 변환
        numeric_columns = [
            'avg_funding_rate', 'sum_open_interest', 'long_short_ratio',
            'volatility_24h', 'top100_richest_pct', 'avg_transaction_value_btc',
            'ext_long_short_ratio', 'long_account_pct', 'short_account_pct',
            'taker_buy_sell_ratio', 'taker_buy_vol', 'taker_sell_vol',
            'top_trader_long_short_ratio', 'bybit_funding_rate', 'bybit_oi',
            'exchange_inflow_usd', 'exchange_outflow_usd', 'net_flow_usd',
            'active_addresses', 'large_tx_count'
        ]
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # ============================================
        # 정적 변수 (기존)
        # ============================================
        
        # 1. 고래 집중도 변화율 (7일) - 무한대 값 처리
        whale_pct_change = df['top100_richest_pct'].pct_change(7)
        df['whale_conc_change_7d'] = whale_pct_change.replace([np.inf, -np.inf], 0).fillna(0)
        # 무한대 값을 클리핑 (-1 ~ 1)
        df['whale_conc_change_7d'] = df['whale_conc_change_7d'].clip(-1, 1)
        
        # 2. 펀딩비 Z-Score (30일)
        df['funding_mean'] = df['avg_funding_rate'].rolling(30).mean()
        df['funding_std'] = df['avg_funding_rate'].rolling(30).std()
        df['funding_rate_zscore'] = np.where(
            df['funding_std'] != 0,
            (df['avg_funding_rate'] - df['funding_mean']) / df['funding_std'],
            0
        )
        df['funding_rate_zscore'] = df['funding_rate_zscore'].fillna(0)
        
        # 3. OI 변화율 (7일) - 무한대 값 처리
        oi_pct_change = df['sum_open_interest'].pct_change(7)
        df['oi_growth_7d'] = oi_pct_change.replace([np.inf, -np.inf], 0).fillna(0)
        # 무한대 값을 클리핑 (-1 ~ 1)
        df['oi_growth_7d'] = df['oi_growth_7d'].clip(-1, 1)
        
        # 4. Long/Short Ratio Normalization
        df['long_short_ratio'] = df['long_short_ratio'].replace(0, 1.0)
        df['long_position_pct'] = df['long_short_ratio'] / (1 + df['long_short_ratio'])
        
        # 5. 변동성 비율
        vol_rolling_mean = df['volatility_24h'].rolling(7).mean()
        df['volatility_ratio'] = np.where(
            vol_rolling_mean != 0,
            df['volatility_24h'] / vol_rolling_mean,
            1.0
        )
        df['volatility_ratio'] = df['volatility_ratio'].fillna(1.0)
        
        # ============================================
        # 동적 변수 (신규 추가)
        # ============================================
        
        if include_dynamic:
            # --- 1차 미분 (변화율) ---
            df['volatility_delta'] = df['volatility_24h'].diff().fillna(0)
            # OI 변화율 - 무한대 값 처리
            oi_pct = df['sum_open_interest'].pct_change()
            df['oi_delta'] = oi_pct.replace([np.inf, -np.inf], 0).fillna(0).clip(-1, 1)
            df['funding_delta'] = df['avg_funding_rate'].diff().fillna(0)
            
            # Taker 비율 변화율
            if 'taker_buy_sell_ratio' in df.columns:
                df['taker_ratio_delta'] = df['taker_buy_sell_ratio'].diff().fillna(0)
            else:
                df['taker_ratio_delta'] = 0
            
            # 거래소 순유입 변화율
            if 'net_flow_usd' in df.columns:
                df['net_flow_delta'] = df['net_flow_usd'].diff().fillna(0)
            else:
                df['net_flow_delta'] = 0
            
            # --- 2차 미분 (가속도) ---
            df['volatility_accel'] = df['volatility_delta'].diff().fillna(0)
            df['oi_accel'] = df['oi_delta'].diff().fillna(0).replace([np.inf, -np.inf], 0).clip(-1, 1)
            df['funding_accel'] = df['funding_delta'].diff().fillna(0)
            
            # --- 이동평균 기울기 (5일) ---
            def calc_slope(series, window=SLOPE_WINDOW):
                """선형 회귀 기울기 계산"""
                def slope_func(x):
                    if len(x) < window:
                        return 0
                    try:
                        return np.polyfit(range(len(x)), x, 1)[0]
                    except:
                        return 0
                return series.rolling(window).apply(slope_func, raw=True).fillna(0)
            
            df['volatility_slope'] = calc_slope(df['volatility_24h'])
            df['oi_slope'] = calc_slope(df['sum_open_interest'])
            df['funding_slope'] = calc_slope(df['avg_funding_rate'])
            
            # --- 변화 안정성 (7일 표준편차) ---
            df['volatility_delta_stability'] = df['volatility_delta'].rolling(STABILITY_WINDOW).std().fillna(0)
            df['oi_delta_stability'] = df['oi_delta'].rolling(STABILITY_WINDOW).std().fillna(0)
            
            # --- 모멘텀 지표 ---
            df['long_short_momentum'] = df['long_short_ratio'].diff(MOMENTUM_WINDOW).fillna(0)
            
            # 확장 롱숏 비율 사용 (있으면)
            if 'ext_long_short_ratio' in df.columns:
                df['ext_ls_momentum'] = df['ext_long_short_ratio'].diff(MOMENTUM_WINDOW).fillna(0)
            else:
                df['ext_ls_momentum'] = 0
            
            # --- 복합 동적 지표 ---
            # 변동성 가속도 * OI 가속도 (동시 급변 감지)
            df['vol_oi_accel_product'] = (df['volatility_accel'] * df['oi_accel']).replace([np.inf, -np.inf], 0).fillna(0).clip(-1, 1)
            
            # 펀딩비 기울기 * Taker 비율 변화 (시장 편향 가속)
            df['funding_taker_momentum'] = df['funding_slope'] * df['taker_ratio_delta']
        
        # ============================================
        # 타겟 변수 생성
        # ============================================
        
        df['next_day_volatility'] = df['volatility_24h'].shift(-1)
        
        if df['volatility_24h'].max() > 0:
            quantile_threshold = df['volatility_24h'].quantile(0.8)
            absolute_threshold = 0.05
            
            df['target_high_vol'] = (
                (df['next_day_volatility'] > quantile_threshold) | 
                (df['next_day_volatility'] > absolute_threshold)
            ).astype(int)
        else:
            df['target_high_vol'] = 0
        
        df['target_high_vol'] = df['target_high_vol'].fillna(0)
        
        # ============================================
        # Feature Set 정의
        # ============================================
        
        # 기본 정적 특성
        static_features = [
            'avg_funding_rate', 'sum_open_interest', 'long_position_pct',
            'whale_conc_change_7d', 'funding_rate_zscore', 'oi_growth_7d',
            'volatility_ratio'
        ]
        
        # 동적 특성
        dynamic_features = [
            # 1차 미분
            'volatility_delta', 'oi_delta', 'funding_delta', 
            'taker_ratio_delta', 'net_flow_delta',
            # 2차 미분
            'volatility_accel', 'oi_accel', 'funding_accel',
            # 기울기
            'volatility_slope', 'oi_slope', 'funding_slope',
            # 안정성
            'volatility_delta_stability', 'oi_delta_stability',
            # 모멘텀
            'long_short_momentum', 'ext_ls_momentum',
            # 복합
            'vol_oi_accel_product', 'funding_taker_momentum'
        ]
        
        # 확장 지표 특성 (있으면 추가)
        extended_features = []
        if 'taker_buy_sell_ratio' in df.columns and df['taker_buy_sell_ratio'].sum() > 0:
            extended_features.extend(['taker_buy_sell_ratio', 'long_account_pct', 'short_account_pct'])
        if 'net_flow_usd' in df.columns and df['net_flow_usd'].sum() != 0:
            extended_features.extend(['net_flow_usd', 'active_addresses', 'large_tx_count'])
        
        # 최종 특성 목록
        if include_dynamic:
            features = static_features + dynamic_features + extended_features
        else:
            features = static_features + extended_features
        
        # 실제 존재하는 특성만 필터링
        features = [f for f in features if f in df.columns]
        
        # 정제
        df_clean = df.dropna(subset=static_features)
        
        for feature in features:
            if feature in df_clean.columns:
                df_clean[feature] = pd.to_numeric(df_clean[feature], errors='coerce').fillna(0.0).astype(float)
        
        return df_clean, features
    
    def create_static_features_only(self, df):
        """정적 변수만 생성 (기존 호환성 유지)"""
        return self.create_features(df, include_dynamic=False)

    def load_weekly_data(self, start_date="2023-01-01"):
        """주봉 데이터 로드"""
        query = f"""
        SELECT 
            w.date,
            w.symbol,
            w.open,
            w.high,
            w.low,
            w.close,
            w.volume,
            w.quote_volume,
            w.atr,
            w.rsi,
            w.upper_shadow_ratio,
            w.lower_shadow_ratio,
            w.weekly_range_pct,
            w.body_size_pct,
            w.volatility_ratio,
            b.top100_richest_pct
        FROM binance_spot_weekly w
        LEFT JOIN bitinfocharts_whale b ON w.date = b.date AND b.coin = 'BTC'
        WHERE w.symbol = 'BTCUSDT'
        AND w.date >= '{start_date}'
        ORDER BY w.date
        """
        df = pd.read_sql(query, self.conn)
        df['date'] = pd.to_datetime(df['date'])
        df = df.ffill().fillna(0)
        return df
    
    def create_weekly_features(self, df, include_dynamic=True):
        """
        주봉 특성 생성 (정적 + 동적)
        
        Args:
            df: 주봉 데이터프레임
            include_dynamic: 동적 변수 포함 여부
        
        Returns:
            df_clean: 정제된 데이터프레임
            features: 특성 목록
        """
        df = df.copy()
        
        # 숫자 컬럼 변환
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'quote_volume',
                       'atr', 'rsi', 'upper_shadow_ratio', 'lower_shadow_ratio',
                       'weekly_range_pct', 'body_size_pct', 'volatility_ratio',
                       'top100_richest_pct']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # ============================================
        # 주봉 정적 변수
        # ============================================
        
        # 주간 수익률
        df['weekly_return'] = df['close'].pct_change().fillna(0)
        
        # 주간 변동성 (High-Low / Close)
        df['weekly_volatility'] = np.where(
            df['close'] != 0,
            (df['high'] - df['low']) / df['close'],
            0
        )
        
        # 고래 집중도 변화 (4주)
        df['whale_conc_change_4w'] = df['top100_richest_pct'].pct_change(4).fillna(0)
        
        # RSI Z-Score (12주)
        rsi_mean = df['rsi'].rolling(12).mean()
        rsi_std = df['rsi'].rolling(12).std()
        df['rsi_zscore'] = np.where(
            rsi_std != 0,
            (df['rsi'] - rsi_mean) / rsi_std,
            0
        )
        df['rsi_zscore'] = df['rsi_zscore'].fillna(0)
        
        # 거래량 Z-Score (12주)
        vol_mean = df['volume'].rolling(12).mean()
        vol_std = df['volume'].rolling(12).std()
        df['volume_zscore'] = np.where(
            vol_std != 0,
            (df['volume'] - vol_mean) / vol_std,
            0
        )
        df['volume_zscore'] = df['volume_zscore'].fillna(0)
        
        # ============================================
        # 주봉 동적 변수
        # ============================================
        
        if include_dynamic:
            # --- 1차 미분 ---
            df['volatility_delta_w'] = df['weekly_volatility'].diff().fillna(0)
            df['volume_delta_w'] = df['volume'].pct_change().fillna(0)
            df['rsi_delta'] = df['rsi'].diff().fillna(0)
            
            # --- 2차 미분 ---
            df['volatility_accel_w'] = df['volatility_delta_w'].diff().fillna(0)
            df['volume_accel_w'] = df['volume_delta_w'].diff().fillna(0)
            df['rsi_accel'] = df['rsi_delta'].diff().fillna(0)
            
            # --- 4주 기울기 ---
            def calc_slope_w(series, window=4):
                def slope_func(x):
                    if len(x) < window:
                        return 0
                    try:
                        return np.polyfit(range(len(x)), x, 1)[0]
                    except:
                        return 0
                return series.rolling(window).apply(slope_func, raw=True).fillna(0)
            
            df['volatility_slope_w'] = calc_slope_w(df['weekly_volatility'])
            df['rsi_slope'] = calc_slope_w(df['rsi'])
            df['volume_slope_w'] = calc_slope_w(df['volume'])
            
            # --- 변화 안정성 (8주) ---
            df['volatility_stability_w'] = df['volatility_delta_w'].rolling(8).std().fillna(0)
            df['volume_stability_w'] = df['volume_delta_w'].rolling(8).std().fillna(0)
            
            # --- 복합 지표 ---
            # RSI 극단값 + 변동성 가속 (반전 신호)
            df['rsi_vol_reversal'] = np.abs(df['rsi'] - 50) * df['volatility_accel_w']
            
            # 거래량 급증 + 고래 활동 (큰 움직임 신호)
            df['volume_whale_signal'] = df['volume_zscore'] * df['whale_conc_change_4w']
        
        # ============================================
        # 타겟 변수 (다음 주 고변동성)
        # ============================================
        
        df['next_week_volatility'] = df['weekly_volatility'].shift(-1)
        
        if df['weekly_volatility'].max() > 0:
            quantile_threshold = df['weekly_volatility'].quantile(0.8)
            df['target_high_vol_w'] = (df['next_week_volatility'] > quantile_threshold).astype(int)
        else:
            df['target_high_vol_w'] = 0
        
        df['target_high_vol_w'] = df['target_high_vol_w'].fillna(0)
        
        # ============================================
        # Feature Set
        # ============================================
        
        static_features_w = [
            'weekly_return', 'weekly_volatility', 'whale_conc_change_4w',
            'rsi_zscore', 'volume_zscore', 'upper_shadow_ratio', 
            'lower_shadow_ratio', 'body_size_pct'
        ]
        
        dynamic_features_w = [
            'volatility_delta_w', 'volume_delta_w', 'rsi_delta',
            'volatility_accel_w', 'volume_accel_w', 'rsi_accel',
            'volatility_slope_w', 'rsi_slope', 'volume_slope_w',
            'volatility_stability_w', 'volume_stability_w',
            'rsi_vol_reversal', 'volume_whale_signal'
        ]
        
        if include_dynamic:
            features = static_features_w + dynamic_features_w
        else:
            features = static_features_w
        
        features = [f for f in features if f in df.columns]
        
        df_clean = df.dropna(subset=[f for f in static_features_w if f in df.columns])
        
        for feature in features:
            if feature in df_clean.columns:
                df_clean[feature] = pd.to_numeric(df_clean[feature], errors='coerce').fillna(0.0).astype(float)
        
        return df_clean, features
    
    def prepare_ml_dataset(self, include_dynamic=True):
        """일봉 ML 데이터셋 준비"""
        df = self.load_raw_data()
        df, feature_cols = self.create_features(df, include_dynamic=include_dynamic)
        
        # Train/Test Split (Time Series Split)
        split_date = "2024-10-01"
        
        train_df = df[df['date'] < split_date]
        test_df = df[df['date'] >= split_date]
        
        return train_df, test_df, feature_cols
    
    def prepare_weekly_ml_dataset(self, include_dynamic=True):
        """주봉 ML 데이터셋 준비"""
        df = self.load_weekly_data()
        df, feature_cols = self.create_weekly_features(df, include_dynamic=include_dynamic)
        
        # Train/Test Split
        split_date = "2024-10-01"
        
        train_df = df[df['date'] < split_date]
        test_df = df[df['date'] >= split_date]
        
        return train_df, test_df, feature_cols

