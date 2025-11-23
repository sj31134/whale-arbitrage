"""
Uniswap V3 Pool을 통한 ERC-20 토큰 가격 조회
체인에서 직접 가격을 계산하므로 무료이고 Rate Limit이 없음
"""

import os
from typing import Optional, Dict
from web3 import Web3
from decimal import Decimal
from src.utils.logger import logger

# Uniswap V3 Factory 컨트랙트 주소
UNISWAP_V3_FACTORY_ADDRESSES = {
    'ethereum': '0x1F98431c8aD98523631AE4a59f267346ea31F984',
    'polygon': '0x1F98431c8aD98523631AE4a59f267346ea31F984',  # 동일한 주소
}

# WETH 주소 (ETH를 래핑한 ERC-20 토큰)
WETH_ADDRESSES = {
    'ethereum': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
    'polygon': '0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619',  # WETH on Polygon (실제로는 WMATIC를 사용)
}

# WMATIC 주소 (Polygon)
WMATIC_ADDRESS = '0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270'

# Uniswap V3 Pool ABI (필요한 함수만)
UNISWAP_V3_POOL_ABI = [
    {
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "slot0",
        "outputs": [
            {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
            {"internalType": "int24", "name": "tick", "type": "int24"},
            {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
            {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
            {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
            {"internalType": "bool", "name": "unlocked", "type": "bool"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "liquidity",
        "outputs": [{"internalType": "uint128", "name": "", "type": "uint128"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ERC-20 ABI (decimals, symbol 함수)
ERC20_ABI = [
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "symbol",
        "outputs": [{"internalType": "string", "name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Fee Tier (0.05%가 가장 유동성이 높음)
POOL_FEE = 3000  # 0.3% (가장 일반적인 유동성 풀)

# RPC 엔드포인트 (chainlink_price_feed.py와 동일)
RPC_ENDPOINTS = {
    'ethereum': os.getenv('ETHEREUM_RPC_URL', 'https://eth.llamarpc.com'),
    'polygon': os.getenv('POLYGON_RPC_URL', 'https://polygon-rpc.com'),
}


def get_pool_address(w3: Web3, factory_address: str, token0: str, token1: str, fee: int) -> Optional[str]:
    """
    Uniswap V3 Factory를 통해 Pool 주소 조회
    
    Parameters:
    -----------
    w3 : Web3
        Web3 인스턴스
    factory_address : str
        Factory 컨트랙트 주소
    token0 : str
        첫 번째 토큰 주소
    token1 : str
        두 번째 토큰 주소
    fee : int
        Pool Fee (3000 = 0.3%)
    
    Returns:
    --------
    Optional[str] : Pool 주소, 없으면 None
    """
    # Factory의 getPool 함수 사용
    factory_abi = [
        {
            "inputs": [
                {"internalType": "address", "name": "tokenA", "type": "address"},
                {"internalType": "address", "name": "tokenB", "type": "address"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"}
            ],
            "name": "getPool",
            "outputs": [{"internalType": "address", "name": "pool", "type": "address"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    
    try:
        factory = w3.eth.contract(
            address=Web3.to_checksum_address(factory_address),
            abi=factory_abi
        )
        pool_address = factory.functions.getPool(
            Web3.to_checksum_address(token0),
            Web3.to_checksum_address(token1),
            fee
        ).call()
        
        # Zero address면 Pool이 존재하지 않음
        if pool_address == '0x0000000000000000000000000000000000000000':
            return None
        return pool_address
    except Exception as e:
        logger.debug(f"⚠️ Pool 주소 조회 실패: {e}")
        return None


def calculate_price_from_sqrt_price(sqrt_price_x96: int, token0_decimals: int, token1_decimals: int) -> float:
    """
    sqrtPriceX96에서 실제 가격 계산
    
    Parameters:
    -----------
    sqrt_price_x96 : int
        Uniswap V3 Pool의 sqrtPriceX96 값
    token0_decimals : int
        token0의 decimals
    token1_decimals : int
        token1의 decimals
    
    Returns:
    --------
    float : token1/token0 가격 비율
    """
    # sqrtPriceX96을 실제 가격으로 변환
    # price = (sqrtPriceX96 / 2^96)^2
    Q96 = 2 ** 96
    sqrt_price = sqrt_price_x96 / Q96
    price = sqrt_price ** 2
    
    # decimals 차이 고려
    price_adjusted = price * (10 ** token0_decimals) / (10 ** token1_decimals)
    
    return float(price_adjusted)


class UniswapPriceFeed:
    """Uniswap V3 Pool을 통한 토큰 가격 조회"""
    
    def __init__(self, chain: str = 'ethereum'):
        """
        Uniswap Price Feed 초기화
        
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
            logger.debug(f"✅ Uniswap {self.chain.upper()} RPC 연결 성공")
        except Exception as e:
            logger.warning(f"⚠️ Uniswap RPC 연결 실패: {e}")
            self.w3 = None
    
    def get_token_price_usd(self, token_address: str, eth_price_usd: float) -> Optional[float]:
        """
        ERC-20 토큰의 USD 가격 조회
        
        Parameters:
        -----------
        token_address : str
            토큰 컨트랙트 주소
        eth_price_usd : float
            현재 ETH/USD 가격 (Chainlink에서 조회)
        
        Returns:
        --------
        Optional[float] : 토큰 USD 가격, 실패 시 None
        """
        if not self.w3:
            return None
        
        try:
            token_address = Web3.to_checksum_address(token_address)
            
            # WETH/WMATIC 주소 결정
            if self.chain == 'ethereum':
                wrapped_native = Web3.to_checksum_address(WETH_ADDRESSES['ethereum'])
            else:
                wrapped_native = Web3.to_checksum_address(WMATIC_ADDRESS)
            
            # Pool 주소 조회 (token/WETH 또는 WETH/token)
            factory_address = UNISWAP_V3_FACTORY_ADDRESSES[self.chain]
            
            # token0 < token1 순서로 정렬 필요
            if token_address.lower() < wrapped_native.lower():
                token0, token1 = token_address, wrapped_native
                is_inverted = True  # 가격이 반전됨
            else:
                token0, token1 = wrapped_native, token_address
                is_inverted = False
            
            pool_address = get_pool_address(
                self.w3, factory_address, token0, token1, POOL_FEE
            )
            
            if not pool_address:
                logger.debug(f"⚠️ {token_address[:10]}... Uniswap V3 Pool을 찾을 수 없음")
                return None
            
            # Pool 컨트랙트
            pool = self.w3.eth.contract(
                address=Web3.to_checksum_address(pool_address),
                abi=UNISWAP_V3_POOL_ABI
            )
            
            # 유동성 확인
            liquidity = pool.functions.liquidity().call()
            if liquidity == 0:
                logger.debug(f"⚠️ Pool 유동성이 0입니다: {pool_address[:10]}...")
                return None
            
            # slot0에서 sqrtPriceX96 조회
            slot0 = pool.functions.slot0().call()
            sqrt_price_x96 = slot0[0]
            
            # token decimals 조회
            erc20 = self.w3.eth.contract(address=token0, abi=ERC20_ABI)
            token0_decimals = erc20.functions.decimals().call()
            
            erc20 = self.w3.eth.contract(address=token1, abi=ERC20_ABI)
            token1_decimals = erc20.functions.decimals().call()
            
            # 실제 token0과 token1 확인 (Pool의 실제 순서)
            actual_token0 = pool.functions.token0().call()
            actual_token1 = pool.functions.token1().call()
            
            # Pool의 실제 token0, token1 decimals 조회
            erc20_token0 = self.w3.eth.contract(address=actual_token0, abi=ERC20_ABI)
            actual_token0_decimals = erc20_token0.functions.decimals().call()
            
            erc20_token1 = self.w3.eth.contract(address=actual_token1, abi=ERC20_ABI)
            actual_token1_decimals = erc20_token1.functions.decimals().call()
            
            # sqrtPriceX96을 실제 가격으로 변환
            # sqrtPriceX96 = sqrt(token1/token0) * 2^96
            Q96 = 2 ** 96
            sqrt_price = float(sqrt_price_x96) / Q96
            raw_price = sqrt_price ** 2
            
            # decimals 조정: raw_price는 실제 수량 비율이므로 decimals 차이 고려
            # price_ratio = (token1_amount / 10^token1_decimals) / (token0_amount / 10^token0_decimals)
            # = (token1_amount / token0_amount) * (10^token0_decimals / 10^token1_decimals)
            price_ratio = raw_price * (10 ** actual_token0_decimals) / (10 ** actual_token1_decimals)
            
            # price_ratio는 token1/token0 비율 (decimals 적용된 실제 가격)
            # 우리가 원하는 것: token_price_in_eth (token/WETH)
            
            # 케이스 1: WETH가 token0, 우리 토큰이 token1
            if actual_token0.lower() == wrapped_native.lower() and actual_token1.lower() == token_address.lower():
                # price_ratio = token/WETH이므로 그대로 사용
                token_price_in_eth = price_ratio
            
            # 케이스 2: 우리 토큰이 token0, WETH가 token1
            elif actual_token0.lower() == token_address.lower() and actual_token1.lower() == wrapped_native.lower():
                # price_ratio = WETH/token이므로 반전 필요
                token_price_in_eth = 1 / price_ratio
            
            else:
                # 예상치 못한 케이스
                logger.debug(f"⚠️ 예상치 못한 Pool 구조: token0={actual_token0[:10]}..., token1={actual_token1[:10]}...")
                return None
            
            if token_price_in_eth <= 0:
                logger.debug(f"⚠️ 가격 계산 실패: token_price_in_eth={token_price_in_eth}")
                return None
            
            # USD 가격으로 변환
            token_price_usd = token_price_in_eth * eth_price_usd
            
            logger.debug(f"💹 {token_address[:10]}... 가격: ${token_price_usd:,.4f} (Uniswap V3)")
            return token_price_usd
            
        except Exception as e:
            logger.debug(f"⚠️ Uniswap 가격 조회 실패 ({token_address[:10]}...): {e}")
            return None


def get_uniswap_token_price(token_address: str, chain: str = 'ethereum', eth_price_usd: float = None) -> Optional[float]:
    """
    Uniswap를 통한 토큰 가격 조회 (간편 함수)
    
    Parameters:
    -----------
    token_address : str
        토큰 컨트랙트 주소
    chain : str
        체인 이름
    eth_price_usd : float
        ETH/USD 가격 (없으면 Chainlink로 조회)
    
    Returns:
    --------
    Optional[float] : 토큰 USD 가격
    """
    try:
        from src.collectors.chainlink_price_feed import get_chainlink_eth_price
        
        if eth_price_usd is None:
            eth_price_usd = get_chainlink_eth_price(chain=chain) or 3500.0
        
        feed = UniswapPriceFeed(chain=chain)
        return feed.get_token_price_usd(token_address, eth_price_usd)
    except Exception as e:
        logger.debug(f"⚠️ Uniswap 초기화 실패: {e}")
        return None
