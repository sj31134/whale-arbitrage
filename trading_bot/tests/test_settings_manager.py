"""
설정 관리자 테스트
"""

import unittest
import tempfile
import json
from pathlib import Path
import os

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from trading_bot.config.settings_manager import SettingsManager


class TestSettingsManager(unittest.TestCase):
    """설정 관리자 테스트"""
    
    def setUp(self):
        """테스트 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_settings.json"
        self.settings_manager = SettingsManager(self.config_path)
    
    def tearDown(self):
        """테스트 정리"""
        if self.config_path.exists():
            os.remove(self.config_path)
        os.rmdir(self.temp_dir)
    
    def test_load_default_settings(self):
        """기본 설정 로드 테스트"""
        settings = self.settings_manager.load_settings()
        self.assertIsInstance(settings, dict)
        self.assertIn('api', settings)
        self.assertIn('trading', settings)
    
    def test_save_and_load_settings(self):
        """설정 저장 및 로드 테스트"""
        test_settings = {
            'api': {
                'upbit_access_key': 'test_key',
                'upbit_secret_key': 'test_secret'
            },
            'trading': {
                'target_coin': 'BTC',
                'initial_capital': 1000000
            }
        }
        
        # 저장
        result = self.settings_manager.save_settings(test_settings)
        self.assertTrue(result)
        self.assertTrue(self.config_path.exists())
        
        # 로드
        loaded_settings = self.settings_manager.load_settings()
        self.assertEqual(loaded_settings['api']['upbit_access_key'], 'test_key')
        self.assertEqual(loaded_settings['trading']['target_coin'], 'BTC')
    
    def test_validate_settings(self):
        """설정 검증 테스트"""
        # 유효한 설정
        valid_settings = {
            'api': {'upbit_access_key': 'test_key_1234567890'},
            'trading': {
                'initial_capital': 1000000,
                'max_position_size': 0.3,
                'stop_loss_pct': -0.05,
                'take_profit_pct': 0.10
            },
            'strategy': {}
        }
        
        is_valid, error = self.settings_manager.validate_settings(valid_settings)
        self.assertTrue(is_valid)
        self.assertEqual(error, "")
        
        # 잘못된 설정 (음수 자본금)
        invalid_settings = valid_settings.copy()
        invalid_settings['trading']['initial_capital'] = -1000
        
        is_valid, error = self.settings_manager.validate_settings(invalid_settings)
        self.assertFalse(is_valid)
        self.assertIn("자본금", error)


if __name__ == '__main__':
    unittest.main()

