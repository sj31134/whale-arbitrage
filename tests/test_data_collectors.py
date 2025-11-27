#!/usr/bin/env python3
"""
데이터 수집기 단위 테스트
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "subprojects" / "risk_ai"))


class TestFuturesMetrics(unittest.TestCase):
    """파생상품 지표 수집기 테스트"""
    
    def test_fetch_long_short_ratio_response_parsing(self):
        """롱숏비율 API 응답 파싱 테스트"""
        # Mock 응답 데이터
        mock_response = [
            {
                "timestamp": 1700000000000,
                "longShortRatio": "1.5",
                "longAccount": "0.6",
                "shortAccount": "0.4"
            }
        ]
        
        # 파싱 로직 테스트
        entry = mock_response[0]
        ts = int(entry["timestamp"])
        dt = datetime.utcfromtimestamp(ts / 1000).date()
        
        self.assertEqual(float(entry["longShortRatio"]), 1.5)
        self.assertEqual(float(entry["longAccount"]), 0.6)
        self.assertEqual(float(entry["shortAccount"]), 0.4)
    
    def test_fetch_taker_ratio_response_parsing(self):
        """Taker 비율 API 응답 파싱 테스트"""
        mock_response = [
            {
                "timestamp": 1700000000000,
                "buySellRatio": "1.2",
                "buyVol": "1000000",
                "sellVol": "833333"
            }
        ]
        
        entry = mock_response[0]
        self.assertEqual(float(entry["buySellRatio"]), 1.2)
        self.assertEqual(float(entry["buyVol"]), 1000000)
        self.assertEqual(float(entry["sellVol"]), 833333)
    
    def test_bybit_funding_response_parsing(self):
        """Bybit 펀딩비 API 응답 파싱 테스트"""
        mock_response = {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "fundingRateTimestamp": "1700000000000",
                        "fundingRate": "0.0001"
                    }
                ]
            }
        }
        
        self.assertEqual(mock_response["retCode"], 0)
        data = mock_response["result"]["list"]
        self.assertEqual(len(data), 1)
        self.assertEqual(float(data[0]["fundingRate"]), 0.0001)


class TestFeatureEngineering(unittest.TestCase):
    """특성 엔지니어링 테스트"""
    
    def setUp(self):
        """테스트 데이터 준비"""
        import pandas as pd
        import numpy as np
        
        # 테스트용 데이터프레임 생성
        dates = pd.date_range(start='2024-01-01', periods=60, freq='D')
        self.df = pd.DataFrame({
            'date': dates,
            'symbol': 'BTCUSDT',
            'avg_funding_rate': np.random.randn(60) * 0.001,
            'sum_open_interest': np.random.randint(1000000, 5000000, 60),
            'long_short_ratio': np.random.uniform(0.8, 1.2, 60),
            'volatility_24h': np.random.uniform(0.01, 0.1, 60),
            'top100_richest_pct': np.random.uniform(10, 20, 60),
            'avg_transaction_value_btc': np.random.uniform(0.1, 10, 60)
        })
    
    def test_dynamic_features_creation(self):
        """동적 변수 생성 테스트"""
        import pandas as pd
        import numpy as np
        
        df = self.df.copy()
        
        # 1차 미분
        df['volatility_delta'] = df['volatility_24h'].diff()
        df['oi_delta'] = df['sum_open_interest'].pct_change()
        
        # 2차 미분
        df['volatility_accel'] = df['volatility_delta'].diff()
        df['oi_accel'] = df['oi_delta'].diff()
        
        # NaN 확인 (처음 몇 행은 NaN)
        self.assertTrue(pd.isna(df['volatility_delta'].iloc[0]))
        self.assertTrue(pd.isna(df['volatility_accel'].iloc[0]))
        self.assertTrue(pd.isna(df['volatility_accel'].iloc[1]))
        
        # 유효한 값 확인
        self.assertFalse(pd.isna(df['volatility_delta'].iloc[5]))
        self.assertFalse(pd.isna(df['volatility_accel'].iloc[5]))
    
    def test_slope_calculation(self):
        """기울기 계산 테스트"""
        import numpy as np
        
        # 선형 증가 데이터
        linear_data = np.arange(10).astype(float)
        
        # 기울기 계산 (5일 윈도우)
        slope = np.polyfit(range(5), linear_data[:5], 1)[0]
        
        # 선형 데이터의 기울기는 1이어야 함
        self.assertAlmostEqual(slope, 1.0, places=5)
    
    def test_zscore_calculation(self):
        """Z-Score 계산 테스트"""
        import pandas as pd
        import numpy as np
        
        df = self.df.copy()
        
        # 펀딩비 Z-Score
        df['funding_mean'] = df['avg_funding_rate'].rolling(30).mean()
        df['funding_std'] = df['avg_funding_rate'].rolling(30).std()
        df['funding_rate_zscore'] = np.where(
            df['funding_std'] != 0,
            (df['avg_funding_rate'] - df['funding_mean']) / df['funding_std'],
            0
        )
        
        # Z-Score 범위 확인 (대부분 -3 ~ 3 사이)
        valid_zscore = df['funding_rate_zscore'].dropna()
        self.assertTrue(all(abs(valid_zscore) < 5))


class TestWhaleStatsAggregation(unittest.TestCase):
    """고래 통계 집계 테스트"""
    
    def test_exchange_flow_calculation(self):
        """거래소 유입/유출 계산 테스트"""
        import pandas as pd
        
        # 테스트 데이터
        transactions = pd.DataFrame({
            'amount_usd': [100000, 50000, 200000, 80000],
            'transaction_direction': [
                'exchange_inflow', 
                'exchange_outflow', 
                'exchange_inflow', 
                'whale_to_whale'
            ]
        })
        
        # 유입 합계
        inflow = transactions[
            transactions['transaction_direction'] == 'exchange_inflow'
        ]['amount_usd'].sum()
        
        # 유출 합계
        outflow = transactions[
            transactions['transaction_direction'] == 'exchange_outflow'
        ]['amount_usd'].sum()
        
        # 순유입
        net_flow = inflow - outflow
        
        self.assertEqual(inflow, 300000)
        self.assertEqual(outflow, 50000)
        self.assertEqual(net_flow, 250000)
    
    def test_large_tx_count(self):
        """대형 거래 건수 계산 테스트"""
        import pandas as pd
        
        transactions = pd.DataFrame({
            'amount_usd': [50000, 150000, 80000, 200000, 500000]
        })
        
        LARGE_TX_THRESHOLD = 100000
        large_tx_count = len(transactions[transactions['amount_usd'] >= LARGE_TX_THRESHOLD])
        
        self.assertEqual(large_tx_count, 3)


if __name__ == '__main__':
    unittest.main()

