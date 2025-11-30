"""
데이터 수집기 테스트
"""

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from trading_bot.collectors.data_collector import DataCollector


class TestDataCollector(unittest.TestCase):
    """데이터 수집기 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.settings = {
            'api': {},
            'trading': {'target_coin': 'BTC'},
            'strategy': {
                'negative_premium_threshold': -0.01,
                'low_premium_threshold': 0.02
            }
        }
        self.collector = DataCollector(self.settings)
    
    def test_get_current_price(self):
        """현재가 조회 테스트"""
        # 실제 API 호출 없이 구조만 테스트
        # 실제 테스트는 모의투자 환경에서 수행
        price = self.collector.get_current_price("BTC")
        # 가격이 0이거나 양수여야 함
        self.assertGreaterEqual(price, 0)
    
    def test_get_premium_data(self):
        """김치 프리미엄 데이터 조회 테스트"""
        premium_data = self.collector.get_premium_data("BTC")
        
        self.assertIn('premium', premium_data)
        self.assertIn('upbit_price', premium_data)
        self.assertIn('is_negative_premium', premium_data)
        self.assertIsInstance(premium_data['premium'], (int, float))
    
    def test_get_risk_prediction(self):
        """리스크 예측 조회 테스트"""
        prediction = self.collector.get_risk_prediction("BTC")
        
        self.assertIn('high_volatility_prob', prediction)
        self.assertIn('risk_score', prediction)
        self.assertIn('success', prediction)
        self.assertIsInstance(prediction['high_volatility_prob'], (int, float))


if __name__ == '__main__':
    unittest.main()

