"""
1inch Price API를 통한 DEX 집계 가격 조회
여러 DEX의 가격을 집계하여 정확한 가격 제공
무료 API (Rate Limit 있음)
"""

import os
import time
import requests
from typing import Optional, Dict
from src.utils.logger import logger

# 1inch Spot Price API 엔드포인트
# 참고: https://1inch.dev/spot-price-api/
# 형식: https://api.1inch.dev/spot-price/v1.0/{chain}/{token_address}
ONEINCH_API_BASE = {
    'ethereum': 'https://api.1inch.dev/spot-price/v1.0/1',  # ChainID: 1
    'polygon': 'https://api.1inch.dev/spot-price/v1.0/137',  # ChainID: 137
}

# 주요 토큰 주소 (대부분의 거래소에서 사용하는 공통 주소)
COMMON_TOKENS = {
    'ethereum': {
        'ETH': '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeeE',  # Native ETH
        'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
        'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
        'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'WBTC': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
        'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
    },
    'polygon': {
        'MATIC': '0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeeE',  # Native MATIC
        'WMATIC': '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270',
        'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
        'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
        'WETH': '0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619',
    }
}

# Rate Limit 관리
_last_request_time = 0
_min_request_interval = 0.5  # 최소 0.5초 간격 (초당 최대 2회 요청)


class OneInchPriceFeed:
    """1inch Price API를 통한 토큰 가격 조회"""
    
    def __init__(self, chain: str = 'ethereum', api_key: Optional[str] = None):
        """
        1inch Price Feed 초기화
        
        Parameters:
        -----------
        chain : str
            체인 이름 ('ethereum' 또는 'polygon')
        api_key : Optional[str]
            1inch API 키 (없으면 공개 API 사용, Rate Limit 낮음)
        """
        self.chain = chain.lower()
        
        if self.chain not in ONEINCH_API_BASE:
            raise ValueError(f"지원하지 않는 체인: {chain}")
        
        self.base_url = ONEINCH_API_BASE[self.chain]
        self.api_key = api_key or os.getenv('ONEINCH_API_KEY')
        
        # Rate Limit 관리
        self._last_request_time = 0
        self._min_interval = 0.5 if not self.api_key else 0.2  # API 키 있으면 더 빠르게
    
    def _wait_for_rate_limit(self):
        """Rate Limit을 위해 대기"""
        global _last_request_time
        current_time = time.time()
        elapsed = current_time - _last_request_time
        
        if elapsed < self._min_interval:
            sleep_time = self._min_interval - elapsed
            time.sleep(sleep_time)
        
        _last_request_time = time.time()
    
    def get_token_price_usd(self, token_address: str) -> Optional[float]:
        """
        ERC-20 토큰의 USD 가격 조회
        
        1inch Spot Price API는 네이티브 통화(ETH/MATIC) 기준 가격을 제공하므로,
        ETH/MATIC 가격과 곱해서 USD 가격으로 변환 필요
        
        Parameters:
        -----------
        token_address : str
            토큰 컨트랙트 주소
        
        Returns:
        --------
        Optional[float] : 토큰 USD 가격, 실패 시 None
        """
        try:
            # Rate Limit 대기
            self._wait_for_rate_limit()
            
            # 1inch Spot Price API 호출
            # 형식: https://api.1inch.dev/spot-price/v1.0/{chain}/{token_address}
            url = f"{self.base_url}/{token_address.lower()}"
            
            headers = {
                'accept': 'application/json'
            }
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # 1inch Spot Price API 응답 구조 확인 필요
                # 일반적으로: { "price": "1234.56", "currency": "USD" } 또는 { "price": "0.5", "currency": "ETH" }
                if 'price' in data and 'currency' in data:
                    price = float(data['price'])
                    currency = data['currency'].upper()
                    
                    # USD로 직접 제공되는 경우
                    if currency == 'USD':
                        logger.debug(f"💹 {token_address[:10]}... 가격 (1inch): ${price:,.4f}")
                        return price
                    
                    # ETH/MATIC 기준인 경우 Chainlink로 변환 필요
                    # 참고: 1inch는 보통 USD를 직접 제공하지만, 확인 필요
                    logger.debug(f"💹 {token_address[:10]}... 가격 (1inch): {price} {currency} (USD 변환 필요)")
                    return None  # USD 변환이 필요하면 None 반환 (Chainlink로 대체)
                
                else:
                    logger.debug(f"⚠️ 1inch 응답 구조 확인 필요: {data}")
                    return None
            
            elif response.status_code == 429:
                # Rate Limit 초과
                logger.warning(f"⚠️ 1inch Rate Limit 초과, 잠시 대기 후 재시도")
                time.sleep(2)
                return None
            
            elif response.status_code == 401:
                # API 키 없음 또는 잘못됨
                logger.debug(f"⚠️ 1inch API 키 필요 또는 잘못됨 (무료 플랜 사용 권장)")
                return None
            
            else:
                logger.debug(f"⚠️ 1inch API 오류: {response.status_code}, {response.text[:100]}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.debug(f"⚠️ 1inch 네트워크 오류: {e}")
            return None
        except Exception as e:
            logger.debug(f"⚠️ 1inch 가격 조회 실패 ({token_address[:10]}...): {e}")
            return None
    
    def get_multiple_token_prices(self, token_addresses: list) -> Dict[str, float]:
        """
        여러 토큰의 가격을 배치로 조회
        
        Parameters:
        -----------
        token_addresses : list
            토큰 주소 리스트
        
        Returns:
        --------
        Dict[str, float] : {token_address: price} 형태의 딕셔너리
        """
        prices = {}
        
        for token_address in token_addresses:
            price = self.get_token_price_usd(token_address)
            if price and price > 0:
                prices[token_address.lower()] = price
        
        return prices


def get_oneinch_token_price(token_address: str, chain: str = 'ethereum') -> Optional[float]:
    """
    1inch를 통한 토큰 가격 조회 (간편 함수)
    
    Parameters:
    -----------
    token_address : str
        토큰 컨트랙트 주소
    chain : str
        체인 이름
    
    Returns:
    --------
    Optional[float] : 토큰 USD 가격
    """
    try:
        feed = OneInchPriceFeed(chain=chain)
        return feed.get_token_price_usd(token_address)
    except Exception as e:
        logger.debug(f"⚠️ 1inch 초기화 실패: {e}")
        return None
