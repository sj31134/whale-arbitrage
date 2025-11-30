"""
주문 실행 모듈
업비트 API를 통한 매수/매도 주문 실행
"""

import pyupbit
import time
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class OrderExecutor:
    """주문 실행 클래스"""
    
    def __init__(self, access_key: str, secret_key: str):
        """
        초기화
        
        Args:
            access_key: 업비트 Access Key
            secret_key: 업비트 Secret Key
        """
        self.access_key = access_key
        self.secret_key = secret_key
        
        if access_key and secret_key:
            try:
                self.upbit = pyupbit.Upbit(access_key, secret_key)
                logger.info("업비트 API 연결 성공")
            except Exception as e:
                logger.error(f"업비트 API 연결 실패: {e}")
                self.upbit = None
        else:
            self.upbit = None
            logger.warning("업비트 API 키가 설정되지 않았습니다.")
    
    def _retry_on_error(self, func, max_retries: int = 3, delay: int = 5):
        """
        에러 발생 시 재시도 데코레이터
        
        Args:
            func: 실행할 함수
            max_retries: 최대 재시도 횟수
            delay: 재시도 간격 (초)
        
        Returns:
            함수 실행 결과
        """
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"{func.__name__} 실패 (시도 {attempt+1}/{max_retries}): {e}. {delay}초 후 재시도...")
                time.sleep(delay)
    
    def place_buy_order(
        self, 
        market: str, 
        price: Optional[float] = None, 
        quantity: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict:
        """
        매수 주문 실행
        
        Args:
            market: 마켓 코드 (예: KRW-BTC)
            price: 주문 가격 (지정가 주문 시)
            quantity: 주문 수량
            order_type: 주문 유형 ("market" 또는 "limit")
        
        Returns:
            {
                'success': bool,
                'uuid': str,  # 주문 UUID
                'error': str  # 에러 메시지 (실패 시)
            }
        """
        if not self.upbit:
            return {
                'success': False,
                'error': '업비트 API가 초기화되지 않았습니다.'
            }
        
        try:
            if order_type == "market":
                # 시장가 매수
                if quantity:
                    result = self._retry_on_error(
                        lambda: self.upbit.buy_market_order(market, quantity)
                    )
                else:
                    # 원화 잔고로 최대한 매수
                    krw_balance = self.upbit.get_balance("KRW")
                    if krw_balance <= 0:
                        return {
                            'success': False,
                            'error': '원화 잔고가 부족합니다.'
                        }
                    result = self._retry_on_error(
                        lambda: self.upbit.buy_market_order(market, krw_balance)
                    )
            else:
                # 지정가 매수
                if not price or not quantity:
                    return {
                        'success': False,
                        'error': '지정가 주문은 가격과 수량이 필요합니다.'
                    }
                result = self._retry_on_error(
                    lambda: self.upbit.buy_limit_order(market, price, quantity)
                )
            
            if result and 'uuid' in result:
                logger.info(f"매수 주문 성공: {market}, UUID: {result['uuid']}")
                return {
                    'success': True,
                    'uuid': result['uuid']
                }
            else:
                error_msg = result.get('error', {}).get('message', '알 수 없는 오류')
                logger.error(f"매수 주문 실패: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"매수 주문 실행 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def place_sell_order(
        self, 
        market: str, 
        price: Optional[float] = None, 
        quantity: Optional[float] = None,
        order_type: str = "market"
    ) -> Dict:
        """
        매도 주문 실행
        
        Args:
            market: 마켓 코드 (예: KRW-BTC)
            price: 주문 가격 (지정가 주문 시)
            quantity: 주문 수량
            order_type: 주문 유형 ("market" 또는 "limit")
        
        Returns:
            {
                'success': bool,
                'uuid': str,  # 주문 UUID
                'error': str  # 에러 메시지 (실패 시)
            }
        """
        if not self.upbit:
            return {
                'success': False,
                'error': '업비트 API가 초기화되지 않았습니다.'
            }
        
        try:
            # 코인 심볼 추출 (KRW-BTC -> BTC)
            coin_symbol = market.split('-')[1]
            
            if order_type == "market":
                # 시장가 매도
                if quantity:
                    result = self._retry_on_error(
                        lambda: self.upbit.sell_market_order(market, quantity)
                    )
                else:
                    # 보유 수량 전량 매도
                    balance = self.upbit.get_balance(coin_symbol)
                    if balance <= 0:
                        return {
                            'success': False,
                            'error': f'{coin_symbol} 잔고가 없습니다.'
                        }
                    result = self._retry_on_error(
                        lambda: self.upbit.sell_market_order(market, balance)
                    )
            else:
                # 지정가 매도
                if not price or not quantity:
                    return {
                        'success': False,
                        'error': '지정가 주문은 가격과 수량이 필요합니다.'
                    }
                result = self._retry_on_error(
                    lambda: self.upbit.sell_limit_order(market, price, quantity)
                )
            
            if result and 'uuid' in result:
                logger.info(f"매도 주문 성공: {market}, UUID: {result['uuid']}")
                return {
                    'success': True,
                    'uuid': result['uuid']
                }
            else:
                error_msg = result.get('error', {}).get('message', '알 수 없는 오류')
                logger.error(f"매도 주문 실패: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"매도 주문 실행 실패: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_order_status(self, uuid: str) -> Dict:
        """
        주문 상태 조회
        
        Args:
            uuid: 주문 UUID
        
        Returns:
            {
                'state': str,  # 'wait', 'done', 'cancel'
                'side': str,  # 'bid' (매수), 'ask' (매도)
                'price': float,
                'volume': float,
                'executed_volume': float
            }
        """
        if not self.upbit:
            return {
                'state': 'error',
                'error': '업비트 API가 초기화되지 않았습니다.'
            }
        
        try:
            result = self._retry_on_error(
                lambda: self.upbit.get_order(uuid)
            )
            
            if result:
                return {
                    'state': result.get('state', 'unknown'),
                    'side': result.get('side', 'unknown'),
                    'price': float(result.get('price', 0)),
                    'volume': float(result.get('volume', 0)),
                    'executed_volume': float(result.get('executed_volume', 0))
                }
            else:
                return {
                    'state': 'error',
                    'error': '주문 정보를 찾을 수 없습니다.'
                }
                
        except Exception as e:
            logger.error(f"주문 상태 조회 실패: {e}")
            return {
                'state': 'error',
                'error': str(e)
            }
    
    def cancel_order(self, uuid: str) -> bool:
        """
        주문 취소
        
        Args:
            uuid: 주문 UUID
        
        Returns:
            취소 성공 여부
        """
        if not self.upbit:
            logger.warning("업비트 API가 초기화되지 않았습니다.")
            return False
        
        try:
            result = self._retry_on_error(
                lambda: self.upbit.cancel_order(uuid)
            )
            
            if result and 'uuid' in result:
                logger.info(f"주문 취소 성공: {uuid}")
                return True
            else:
                logger.error(f"주문 취소 실패: {result}")
                return False
                
        except Exception as e:
            logger.error(f"주문 취소 실행 실패: {e}")
            return False
    
    def is_connected(self) -> bool:
        """API 연결 상태 확인"""
        return self.upbit is not None

