"""
김치 프리미엄 필터
역프 또는 낮은 김프일 때만 매수 허용하는 전역 필터
"""

from typing import Dict
import logging

logger = logging.getLogger(__name__)


class PremiumFilter:
    """김치 프리미엄 필터 클래스"""
    
    def __init__(self, settings: Dict, data_collector):
        """
        초기화
        
        Args:
            settings: 설정 딕셔너리
            data_collector: 데이터 수집기 인스턴스
        """
        self.settings = settings
        self.data_collector = data_collector
    
    def should_allow_buy(self, coin: str = "BTC") -> bool:
        """
        전역 매수 필터: 역프 또는 낮은 김프일 때만 매수 허용
        
        Args:
            coin: 코인 심볼
        
        Returns:
            매수 허용 여부
        """
        try:
            premium_data = self.data_collector.get_premium_data(coin)
            return premium_data['is_negative_premium'] or premium_data['is_low_premium']
        except Exception as e:
            logger.error(f"프리미엄 필터 확인 실패: {e}")
            return False
    
    def get_position_size_multiplier(self, coin: str = "BTC") -> float:
        """
        역프 상태일 때 포지션 크기 배수 반환
        
        Args:
            coin: 코인 심볼
        
        Returns:
            포지션 크기 배수 (기본 1.0, 역프일 때 2.0)
        """
        try:
            premium_data = self.data_collector.get_premium_data(coin)
            if premium_data['is_negative_premium']:
                return 2.0  # 역프일 때 2배
            return 1.0
        except Exception as e:
            logger.error(f"포지션 크기 배수 계산 실패: {e}")
            return 1.0
    
    def get_premium_info(self, coin: str = "BTC") -> Dict:
        """
        프리미엄 정보 조회
        
        Args:
            coin: 코인 심볼
        
        Returns:
            프리미엄 정보 딕셔너리
        """
        try:
            return self.data_collector.get_premium_data(coin)
        except Exception as e:
            logger.error(f"프리미엄 정보 조회 실패: {e}")
            return {
                'premium': 0.0,
                'upbit_price': 0.0,
                'binance_price_krw': 0.0,
                'is_negative_premium': False,
                'is_low_premium': False
            }

