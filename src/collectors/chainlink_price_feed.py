"""
Chainlink Price Feeds를 통한 가격 조회
온체인 오라클이므로 무료이고 Rate Limit이 없으며 정확도가 높음
"""

import os
from typing import Dict, Optional
from web3 import Web3
from src.utils.logger import logger

# Chainlink Price Feed 컨트랙트 주소 (ETH/USD)
# Ethereum Mainnet
CHAINLINK_ETH_USD_ETHEREUM = os.getenv(
    'CHAINLINK_ETH_USD_ADDRESS_ETHEREUM',
    '0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419'
)

# Polygon Mainnet
CHAINLINK_ETH_USD_POLYGON = os.getenv(
    'CHAINLINK_ETH_USD_ADDRESS_POLYGON',
    '0xF9680D99D6C9589e2a93a78A04A279e509205945'
)

# 주요 토큰/코인 Chainlink 주소
# 추가 토큰 주소는 필요시 확장 가능
CHAINLINK_ADDRESSES = {
    'ethereum': {
        'ETH/USD': CHAINLINK_ETH_USD_ETHEREUM,
        'BTC/USD': '0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c',
    },
    'polygon': {
        'ETH/USD': CHAINLINK_ETH_USD_POLYGON,
        'BTC/USD': '0xc907E116054Ad103354f0D350FCb1f1292b58a5c',
        'MATIC/USD': '0xAB594600376Ec9fD91F8e885dADF0CE036862dE0',
    }
}

# RPC 엔드포인트 (무료 공개 노드 사용)
# 참고: 무료 노드는 Rate Limit이 있을 수 있음
RPC_ENDPOINTS = {
    'ethereum': os.getenv('ETHEREUM_RPC_URL', 'https://eth.llamarpc.com'),  # LlamaNodes 무료
    'polygon': os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com'),  # Polygon 공식 RPC
}

# Chainlink Aggregator V3 ABI (latestRoundData 함수만 필요)
CHAINLINK_AGGREGATOR_V3_ABI = [
    {
        "inputs": [],
        "name": "latestRoundData",
        "outputs": [
            {"name": "roundId", "type": "uint80"},
            {"name": "answer", "type": "int256"},
            {"name": "startedAt", "type": "uint256"},
            {"name": "updatedAt", "type": "uint256"},
            {"name": "answeredInRound", "type": "uint80"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    }
]


class ChainlinkPriceFeed:
    """Chainlink Price Feed를 통한 가격 조회"""
    
    def __init__(self, chain: str = 'ethereum'):
        """
        Chainlink Price Feed 초기화
        
        Parameters:
        -----------
        chain : str
            체인 이름 ('ethereum' 또는 'polygon')
        """
        self.chain = chain.lower()
        
        if self.chain not in RPC_ENDPOINTS:
            raise ValueError(f"지원하지 않는 체인: {chain}")
        
        # Web3 연결 (request_kwargs로 타임아웃 설정)
        rpc_url = RPC_ENDPOINTS[self.chain]
        try:
            self.w3 = Web3(Web3.HTTPProvider(
                rpc_url,
                request_kwargs={'timeout': 10}  # 10초 타임아웃
            ))
            if not self.w3.is_connected():
                raise ConnectionError(f"RPC 연결 실패: {rpc_url}")
            logger.debug(f"✅ Chainlink {self.chain.upper()} RPC 연결 성공")
        except Exception as e:
            logger.warning(f"⚠️ Chainlink RPC 연결 실패: {e}")
            self.w3 = None
    
    def get_eth_price_usd(self) -> Optional[float]:
        """
        ETH/USD 가격 조회
        
        Returns:
        --------
        Optional[float] : ETH/USD 가격, 실패 시 None
        """
        if not self.w3:
            return None
        
        try:
            # Chainlink ETH/USD 주소
            feed_address = CHAINLINK_ADDRESSES.get(self.chain, {}).get('ETH/USD')
            if not feed_address:
                logger.warning(f"⚠️ {self.chain}에서 ETH/USD Feed 주소를 찾을 수 없습니다")
                return None
            
            # 컨트랙트 생성
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(feed_address),
                abi=CHAINLINK_AGGREGATOR_V3_ABI
            )
            
            # latestRoundData 호출
            result = contract.functions.latestRoundData().call()
            
            # result 구조: (roundId, answer, startedAt, updatedAt, answeredInRound)
            answer = result[1]  # answer는 int256
            decimals = contract.functions.decimals().call()
            
            # 가격 계산 (answer를 decimals로 나눔)
            price = float(answer) / (10 ** decimals)
            
            logger.debug(f"💹 Chainlink ETH/USD 가격: ${price:,.2f}")
            return price
            
        except Exception as e:
            logger.warning(f"⚠️ Chainlink ETH 가격 조회 실패: {e}")
            return None
    
    def get_price_by_address(self, token_address: str) -> Optional[float]:
        """
        특정 토큰 주소의 가격 조회
        
        주의: Chainlink는 특정 토큰에 대해서만 Price Feed를 제공
        대부분의 ERC-20 토큰은 지원하지 않음
        
        Parameters:
        -----------
        token_address : str
            토큰 컨트랙트 주소
        
        Returns:
        --------
        Optional[float] : 토큰 가격, 실패 또는 지원하지 않는 토큰인 경우 None
        """
        # Chainlink는 특정 토큰만 지원하므로
        # 여기서는 ETH/BTC 같은 주요 코인만 처리
        # ERC-20 토큰은 다른 소스(Uniswap Pool 등) 사용 필요
        
        logger.debug(f"💹 Chainlink는 특정 토큰만 지원 (ERC-20 토큰은 Uniswap Pool 사용 권장)")
        return None


def get_chainlink_eth_price(chain: str = 'ethereum') -> Optional[float]:
    """
    Chainlink를 통한 ETH 가격 조회 (간편 함수)
    
    Parameters:
    -----------
    chain : str
        체인 이름 ('ethereum' 또는 'polygon')
    
    Returns:
    --------
    Optional[float] : ETH/USD 가격
    """
    try:
        feed = ChainlinkPriceFeed(chain=chain)
        return feed.get_eth_price_usd()
    except Exception as e:
        logger.warning(f"⚠️ Chainlink 초기화 실패: {e}")
        return None
