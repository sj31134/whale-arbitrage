"""
시장 데이터 수집 모듈
업비트 API를 통한 실시간 가격 및 잔고 조회
"""

import pyupbit
from typing import Dict, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class MarketDataCollector:
    """시장 데이터 수집 클래스"""
    
    def __init__(self, access_key: str, secret_key: str):
        """
        초기화
        
        Args:
            access_key: 업비트 Access Key
            secret_key: 업비트 Secret Key
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self._upbit = None
        
        if access_key and secret_key:
            try:
                self._upbit = pyupbit.Upbit(access_key, secret_key)
                logger.info("업비트 API 연결 성공")
            except Exception as e:
                logger.error(f"업비트 API 연결 실패: {e}")
    
    def get_current_price(self, market: str = "KRW-BTC") -> float:
        """
        현재가 조회 (공개 API)
        
        Args:
            market: 마켓 코드 (예: KRW-BTC)
        
        Returns:
            현재가 (원)
        """
        try:
            price = pyupbit.get_current_price(market)
            if price:
                return float(price)
            return 0.0
        except Exception as e:
            logger.error(f"현재가 조회 실패: {e}")
            return 0.0
    
    def get_balance(self, currency: str = "KRW") -> float:
        """
        잔고 조회
        
        Args:
            currency: 통화 코드 (KRW, BTC, ETH 등)
        
        Returns:
            잔고
        """
        if not self._upbit:
            logger.warning("업비트 API가 초기화되지 않았습니다.")
            return 0.0
        
        try:
            if currency == "KRW":
                balance = self._upbit.get_balance("KRW")
            else:
                balance = self._upbit.get_balance(currency)
            
            return float(balance) if balance else 0.0
            
        except Exception as e:
            logger.error(f"잔고 조회 실패: {e}")
            return 0.0
    
    def get_all_balances(self) -> Dict[str, float]:
        """
        전체 잔고 조회
        
        Returns:
            {통화코드: 잔고} 딕셔너리
        """
        if not self._upbit:
            logger.warning("업비트 API가 초기화되지 않았습니다.")
            return {}
        
        try:
            balances = self._upbit.get_balances()
            result = {}
            
            for balance in balances:
                currency = balance.get('currency', '')
                balance_amount = float(balance.get('balance', 0))
                if balance_amount > 0:
                    result[currency] = balance_amount
            
            return result
            
        except Exception as e:
            logger.error(f"전체 잔고 조회 실패: {e}")
            return {}
    
    def get_orderbook(self, market: str = "KRW-BTC", limit: int = 5) -> Dict:
        """
        오더북 조회 (공개 API)
        
        Args:
            market: 마켓 코드
            limit: 조회할 호가 개수
        
        Returns:
            {
                'bids': [(가격, 수량), ...],
                'asks': [(가격, 수량), ...]
            }
        """
        try:
            orderbook = pyupbit.get_orderbook(market)
            
            if orderbook:
                bids = orderbook.get('orderbook_units', [])[:limit]
                asks = orderbook.get('orderbook_units', [])[:limit]
                
                return {
                    'bids': [(float(bid['bid_price']), float(bid['bid_size'])) for bid in bids],
                    'asks': [(float(ask['ask_price']), float(ask['ask_size'])) for ask in asks]
                }
            
            return {'bids': [], 'asks': []}
            
        except Exception as e:
            logger.error(f"오더북 조회 실패: {e}")
            return {'bids': [], 'asks': []}
    
    def is_api_connected(self) -> bool:
        """API 연결 상태 확인"""
        return self._upbit is not None

