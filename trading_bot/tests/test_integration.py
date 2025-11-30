"""
통합 테스트
전체 플로우 테스트 (실제 API 호출 없이 구조만 테스트)
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from trading_bot.config.settings_manager import SettingsManager
from trading_bot.core.bot_engine import TradingBotEngine


class TestIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.settings = {
            'api': {
                'upbit_access_key': 'test_key',
                'upbit_secret_key': 'test_secret'
            },
            'telegram': {
                'bot_token': '',
                'chat_id': ''
            },
            'trading': {
                'target_coin': 'BTC',
                'initial_capital': 1000000,
                'max_position_size': 0.3,
                'stop_loss_pct': -0.05,
                'take_profit_pct': 0.10
            },
            'strategy': {
                'volatility_window': 5,
                'negative_premium_threshold': -0.01,
                'low_premium_threshold': 0.02
            },
            'risk_management': {
                'max_retries': 3,
                'retry_delay': 5,
                'check_interval': 60
            }
        }
    
    @patch('trading_bot.execution.order_executor.pyupbit.Upbit')
    def test_bot_engine_initialization(self, mock_upbit):
        """봇 엔진 초기화 테스트"""
        mock_upbit.return_value = Mock()
        
        engine = TradingBotEngine(self.settings)
        
        self.assertIsNotNone(engine.data_collector)
        self.assertIsNotNone(engine.strategy)
        self.assertIsNotNone(engine.position_manager)
        self.assertFalse(engine.is_running)
    
    def test_settings_manager_integration(self):
        """설정 관리자 통합 테스트"""
        import tempfile
        import os
        
        temp_dir = tempfile.mkdtemp()
        config_path = Path(temp_dir) / "test_settings.json"
        
        try:
            manager = SettingsManager(config_path)
            
            # 저장
            result = manager.save_settings(self.settings)
            self.assertTrue(result)
            
            # 로드
            loaded = manager.load_settings()
            self.assertEqual(loaded['trading']['target_coin'], 'BTC')
            
        finally:
            if config_path.exists():
                os.remove(config_path)
            os.rmdir(temp_dir)


if __name__ == '__main__':
    unittest.main()

