#!/usr/bin/env python3
"""
특성 엔지니어링 단위 테스트
"""

import unittest
import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))


class TestDynamicFeatures(unittest.TestCase):
    """동적 변수 테스트"""
    
    def setUp(self):
        """테스트 데이터 생성"""
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        
        self.df = pd.DataFrame({
            'date': dates,
            'volatility_24h': np.random.uniform(0.02, 0.08, 100),
            'sum_open_interest': np.cumsum(np.random.randn(100) * 1000000) + 5000000,
            'avg_funding_rate': np.random.randn(100) * 0.001,
            'long_short_ratio': np.random.uniform(0.8, 1.2, 100)
        })
    
    def test_first_derivative(self):
        """1차 미분 (변화율) 테스트"""
        df = self.df.copy()
        
        # 변동성 변화율
        df['volatility_delta'] = df['volatility_24h'].diff()
        
        # 첫 번째 값은 NaN
        self.assertTrue(pd.isna(df['volatility_delta'].iloc[0]))
        
        # 두 번째 값부터 유효
        expected = df['volatility_24h'].iloc[1] - df['volatility_24h'].iloc[0]
        self.assertAlmostEqual(df['volatility_delta'].iloc[1], expected, places=10)
    
    def test_second_derivative(self):
        """2차 미분 (가속도) 테스트"""
        df = self.df.copy()
        
        df['volatility_delta'] = df['volatility_24h'].diff()
        df['volatility_accel'] = df['volatility_delta'].diff()
        
        # 처음 두 값은 NaN
        self.assertTrue(pd.isna(df['volatility_accel'].iloc[0]))
        self.assertTrue(pd.isna(df['volatility_accel'].iloc[1]))
        
        # 세 번째 값부터 유효
        self.assertFalse(pd.isna(df['volatility_accel'].iloc[2]))
    
    def test_rolling_slope(self):
        """이동평균 기울기 테스트"""
        df = self.df.copy()
        
        window = 5
        
        def calc_slope(series):
            def slope_func(x):
                if len(x) < window:
                    return np.nan
                return np.polyfit(range(len(x)), x, 1)[0]
            return series.rolling(window).apply(slope_func, raw=True)
        
        df['volatility_slope'] = calc_slope(df['volatility_24h'])
        
        # 처음 window-1 개는 NaN
        for i in range(window - 1):
            self.assertTrue(pd.isna(df['volatility_slope'].iloc[i]))
        
        # window 번째부터 유효
        self.assertFalse(pd.isna(df['volatility_slope'].iloc[window - 1]))
    
    def test_stability_measure(self):
        """변화 안정성 (표준편차) 테스트"""
        df = self.df.copy()
        
        df['volatility_delta'] = df['volatility_24h'].diff()
        df['delta_stability'] = df['volatility_delta'].rolling(7).std()
        
        # 안정성은 항상 양수 또는 0
        valid_stability = df['delta_stability'].dropna()
        self.assertTrue(all(valid_stability >= 0))
    
    def test_momentum_calculation(self):
        """모멘텀 계산 테스트"""
        df = self.df.copy()
        
        # 3일 모멘텀
        df['ls_momentum'] = df['long_short_ratio'].diff(3)
        
        # 처음 3개는 NaN
        for i in range(3):
            self.assertTrue(pd.isna(df['ls_momentum'].iloc[i]))
        
        # 4번째부터 유효
        expected = df['long_short_ratio'].iloc[3] - df['long_short_ratio'].iloc[0]
        self.assertAlmostEqual(df['ls_momentum'].iloc[3], expected, places=10)


class TestWeeklyFeatures(unittest.TestCase):
    """주봉 특성 테스트"""
    
    def setUp(self):
        """주봉 테스트 데이터 생성"""
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=52, freq='W')
        
        self.df = pd.DataFrame({
            'date': dates,
            'open': np.random.uniform(40000, 50000, 52),
            'high': np.random.uniform(45000, 55000, 52),
            'low': np.random.uniform(35000, 45000, 52),
            'close': np.random.uniform(40000, 50000, 52),
            'volume': np.random.uniform(1e9, 5e9, 52),
            'rsi': np.random.uniform(30, 70, 52)
        })
    
    def test_weekly_return(self):
        """주간 수익률 테스트"""
        df = self.df.copy()
        
        df['weekly_return'] = df['close'].pct_change()
        
        # 첫 번째는 NaN
        self.assertTrue(pd.isna(df['weekly_return'].iloc[0]))
        
        # 두 번째부터 유효
        expected = (df['close'].iloc[1] - df['close'].iloc[0]) / df['close'].iloc[0]
        self.assertAlmostEqual(df['weekly_return'].iloc[1], expected, places=10)
    
    def test_weekly_volatility(self):
        """주간 변동성 테스트"""
        df = self.df.copy()
        
        df['weekly_volatility'] = (df['high'] - df['low']) / df['close']
        
        # 모든 값이 양수
        self.assertTrue(all(df['weekly_volatility'] > 0))
    
    def test_rsi_zscore(self):
        """RSI Z-Score 테스트"""
        df = self.df.copy()
        
        rsi_mean = df['rsi'].rolling(12).mean()
        rsi_std = df['rsi'].rolling(12).std()
        df['rsi_zscore'] = (df['rsi'] - rsi_mean) / rsi_std
        
        # 유효한 Z-Score는 대부분 -3 ~ 3 범위
        valid_zscore = df['rsi_zscore'].dropna()
        self.assertTrue(all(abs(valid_zscore) < 5))


class TestNaNHandling(unittest.TestCase):
    """NaN 처리 테스트"""
    
    def test_fillna_zero(self):
        """NaN을 0으로 채우기 테스트"""
        df = pd.DataFrame({
            'a': [1, np.nan, 3, np.nan, 5]
        })
        
        df['a'] = df['a'].fillna(0)
        
        self.assertEqual(df['a'].iloc[1], 0)
        self.assertEqual(df['a'].iloc[3], 0)
    
    def test_forward_fill(self):
        """Forward fill 테스트"""
        df = pd.DataFrame({
            'a': [1, np.nan, np.nan, 4, np.nan]
        })
        
        df['a'] = df['a'].ffill()
        
        self.assertEqual(df['a'].iloc[1], 1)
        self.assertEqual(df['a'].iloc[2], 1)
        self.assertEqual(df['a'].iloc[4], 4)


if __name__ == '__main__':
    unittest.main()

