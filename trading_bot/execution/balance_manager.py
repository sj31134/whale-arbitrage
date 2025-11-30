"""
잔고 관리 모듈
"""

from typing import Dict
import logging

logger = logging.getLogger(__name__)


class BalanceManager:
    """잔고 관리 클래스"""
    
    def __init__(self, market_data_collector):
        """
        초기화
        
        Args:
            market_data_collector: MarketDataCollector 인스턴스
        """
        self.market_data = market_data_collector
    
    def get_balance(self, currency: str = "KRW") -> float:
        """
        잔고 조회
        
        Args:
            currency: 통화 코드
        
        Returns:
            잔고
        """
        return self.market_data.get_balance(currency)
    
    def get_all_balances(self) -> Dict[str, float]:
        """
        전체 잔고 조회
        
        Returns:
            {통화코드: 잔고} 딕셔너리
        """
        return self.market_data.get_all_balances()
    
    def calculate_position_size(
        self, 
        capital: float, 
        max_position_ratio: float, 
        current_price: float,
        multiplier: float = 1.0
    ) -> float:
        """
        포지션 크기 계산
        
        Args:
            capital: 사용 가능한 자본금
            max_position_ratio: 최대 포지션 비율 (0-1)
            current_price: 현재가
            multiplier: 추가 배수 (역프일 때 2.0 등)
        
        Returns:
            포지션 크기 (원)
        """
        base_size = capital * max_position_ratio
        position_size = base_size * multiplier
        
        # 최대 포지션 크기 제한 (자본금의 50%)
        max_position = capital * 0.5
        position_size = min(position_size, max_position)
        
        return position_size
    
    def calculate_quantity(self, position_size: float, price: float) -> float:
        """
        주문 수량 계산
        
        Args:
            position_size: 포지션 크기 (원)
            price: 가격
        
        Returns:
            수량
        """
        if price <= 0:
            return 0.0
        
        quantity = position_size / price
        return quantity

