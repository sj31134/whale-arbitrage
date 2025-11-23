# src/collectors/block_explorer_collector.py

import requests
import os
import time
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from src.utils.logger import logger

# Chainlink Price Feed (무료 온체인 가격)
try:
    from src.collectors.chainlink_price_feed import get_chainlink_eth_price
    CHAINLINK_AVAILABLE = True
except ImportError:
    CHAINLINK_AVAILABLE = False
    logger.warning("⚠️ Chainlink 모듈을 로드할 수 없습니다. web3 패키지가 설치되어 있는지 확인하세요.")

# Uniswap Price Feed (ERC-20 토큰 가격)
try:
    from src.collectors.uniswap_price_feed import get_uniswap_token_price
    UNISWAP_AVAILABLE = True
except ImportError:
    UNISWAP_AVAILABLE = False
    logger.warning("⚠️ Uniswap 모듈을 로드할 수 없습니다. web3 패키지가 설치되어 있는지 확인하세요.")

# 1inch Price Feed (DEX 집계 가격)
try:
    from src.collectors.oneinch_price_feed import get_oneinch_token_price
    ONEINCH_AVAILABLE = True
except ImportError:
    ONEINCH_AVAILABLE = False
    logger.debug("⚠️ 1inch 모듈을 로드할 수 없습니다 (선택적 기능).")

# 4byte.directory 함수 시그니처 디코더 (선택적 기능)
try:
    from src.utils.function_decoder import decode_input_data, extract_method_id
    FUNCTION_DECODER_AVAILABLE = True
except ImportError:
    FUNCTION_DECODER_AVAILABLE = False
    logger.debug("⚠️ Function Decoder 모듈을 로드할 수 없습니다 (선택적 기능).")

# 재시도 로직 유틸리티
try:
    from src.utils.retry_handler import retry_on_http_error, retry_with_backoff
    RETRY_HANDLER_AVAILABLE = True
except ImportError:
    RETRY_HANDLER_AVAILABLE = False
    logger.debug("⚠️ Retry Handler 모듈을 로드할 수 없습니다 (기본 재시도 로직 사용).")

# 환경변수 로드
load_dotenv('config/.env')

class BlockExplorerCollector:
    """멀티체인 블록 탐색기 API를 통한 거래 데이터 수집"""
    
    # 체인별 설정 매핑
    # Etherscan API V2는 하나의 API 키로 모든 체인을 지원 (unified multichain)
    # 참고: https://docs.etherscan.io/v2-migration
    CHAIN_CONFIG = {
        'ethereum': {
            'base_url': 'https://api.etherscan.io/api',
            'base_url_v2': 'https://api.etherscan.io/v2/api',
            'chainid': 1,
            'native_coin': 'ETH',
            'api_key_env': 'ETHERSCAN_API_KEY'  # 모든 체인에서 동일한 키 사용
        },
        'polygon': {
            'base_url': 'https://api.etherscan.io/v2/api',  # Etherscan API V2 사용
            'base_url_v2': 'https://api.etherscan.io/v2/api',  # Etherscan API V2 사용
            'chainid': 137,  # Polygon ChainID
            'native_coin': 'MATIC',
            'api_key_env': 'ETHERSCAN_API_KEY'  # Etherscan API 키 사용 (별도 Polygonscan 키 불필요)
        }
    }
    
    def __init__(self, chain: str = 'ethereum'):
        """
        블록 탐색기 수집기 초기화
        
        Parameters:
        -----------
        chain : str
            체인 이름 ('ethereum' 또는 'polygon', 기본값: 'ethereum')
        """
        self.chain = chain.lower()
        
        if self.chain not in self.CHAIN_CONFIG:
            raise ValueError(f"❌ 지원하지 않는 체인: {chain}. 지원 체인: {list(self.CHAIN_CONFIG.keys())}")
        
        # 체인별 설정 로드
        config = self.CHAIN_CONFIG[self.chain]
        self.api_key = os.getenv(config['api_key_env'])
        
        if not self.api_key:
            raise ValueError(f"❌ {config['api_key_env']}가 설정되지 않았습니다")
        
        # URL 설정
        self.base_url = config['base_url']
        self.base_url_v1 = config['base_url']
        self.base_url_v2 = config['base_url_v2']
        
        # ChainID 설정
        self.chainid = config['chainid']
        
        # 네이티브 코인 심볼
        self.native_coin = config['native_coin']
        
        # 설정값
        self.min_whale_eth = float(os.getenv('MIN_WHALE_AMOUNT_ETH', 10))
        self.min_whale_usd = float(os.getenv('MIN_WHALE_AMOUNT_USD', 50000))
        self.api_delay = float(os.getenv('API_DELAY_SECONDS', 0.5))  # Rate limit 방지
        
        # 가격 캐시 (API 호출 최소화)
        self._eth_price_cache = None
        self._token_price_cache = {}
        self._last_price_fetch_time = 0
        self._last_token_price_fetch_time = 0
        self._price_cache_duration = 300  # 5분 캐시 유지 (무료 API rate limit 방지)
        
        logger.info(f"✅ {self.chain.upper()} 수집기 초기화 완료 (ChainID: {self.chainid})")
        logger.info(f"   - 네이티브 코인: {self.native_coin}")
        logger.info(f"   - 고래 기준 ({self.native_coin}): {self.min_whale_eth}")
        logger.info(f"   - 고래 기준 (USD): ${self.min_whale_usd:,.0f}")
        logger.info(f"   - 가격 캐시: {self._price_cache_duration}초")
    
    def _make_api_request(self, params: Dict[str, Any], description: str = "API 요청") -> Optional[Dict]:
        """
        API 요청을 재시도 로직과 함께 수행 (표준화된 재시도 데코레이터 사용)
        
        Parameters:
        -----------
        params : Dict[str, Any]
            API 요청 파라미터
        description : str
            요청 설명 (로깅용)
        
        Returns:
        --------
        Optional[Dict] : API 응답 데이터, 실패 시 None
        """
        max_retries = int(os.getenv('POLYGON_RETRY_MAX_ATTEMPTS', 5))
        base_delay = float(os.getenv('POLYGON_RETRY_BACKOFF_BASE', 2.0))
        
        # 재시도 데코레이터가 사용 가능하면 사용, 아니면 직접 구현
        if RETRY_HANDLER_AVAILABLE:
            @retry_on_http_error(
                max_attempts=max_retries,
                base_delay=base_delay,
                max_delay=60.0,
                retry_status_codes=(500, 502, 503, 504)
            )
            def _request():
                response = requests.get(self.base_url_v2, params=params, timeout=30)
                response.raise_for_status()
                return response.json()
            
            try:
                return _request()
            except requests.exceptions.HTTPError as e:
                logger.error(f"❌ {description} 최종 실패: {e}")
                return None
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ {description} 네트워크 오류: {e}")
                return None
            except Exception as e:
                logger.error(f"❌ {description} 예상치 못한 오류: {e}")
                return None
        else:
            # Fallback: 기본 재시도 로직 (기존 방식)
            for attempt in range(1, max_retries + 1):
                try:
                    response = requests.get(self.base_url_v2, params=params, timeout=30)
                    response.raise_for_status()
                    return response.json()
                    
                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code if hasattr(e, 'response') else None
                    
                    if status_code in (500, 502, 503, 504) and attempt < max_retries:
                        delay = min(base_delay * (2.0 ** (attempt - 1)), 60.0)
                        logger.warning(f"⚠️ {description} HTTP {status_code} 에러 (시도 {attempt}/{max_retries})")
                        logger.info(f"   {delay:.1f}초 후 재시도...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"❌ {description} 실패: {e}")
                        return None
                        
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries:
                        delay = min(base_delay * (2.0 ** (attempt - 1)), 60.0)
                        logger.warning(f"⚠️ {description} 네트워크 에러 (시도 {attempt}/{max_retries}): {e}")
                        logger.info(f"   {delay:.1f}초 후 재시도...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"❌ {description} 실패: {e}")
                        return None
            
            return None
    
    def get_wallet_transactions(self, 
                               address: str, 
                               page: int = 1, 
                               offset: int = 10000) -> List[Dict[str, Any]]:
        """
        특정 지갑의 거래 이력 조회 (재시도 로직 포함)
        
        Parameters:
        -----------
        address : str
            이더리움 지갑 주소 (0x로 시작)
        page : int
            페이지 번호
        offset : int
            페이지당 결과 수 (최대 10,000)
        
        Returns:
        --------
        List[Dict] : 거래 데이터 리스트
        """
        # V2 API 파라미터 (chainid 필수)
        params = {
            'chainid': self.chainid,  # V2 API 필수 파라미터
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': 0,
            'endblock': 99999999,
            'page': page,
            'offset': offset,
            'sort': 'desc',
            'apikey': self.api_key
        }
        
        try:
            logger.info(f"🔍 {address[:10]}... 거래 조회 중... (ChainID: {self.chainid})")
            
            # 재시도 로직 포함 API 요청
            data = self._make_api_request(params, f"{self.chain.upper()} 거래 조회")
            
            if data is None:
                return []
            
            if data.get('status') == '1':
                transactions = data.get('result', [])
                if not isinstance(transactions, list):
                    transactions = []
                    
                logger.info(f"✅ {len(transactions)}건 조회 완료")
                
                # 거래 파싱
                parsed_transactions = self._parse_transactions(transactions)
                return parsed_transactions
            
            elif data.get('status') == '0':
                error_msg = data.get('message', 'No transactions found')
                result_msg = data.get('result', '')
                
                # 에러 메시지 분석
                logger.warning(f"⚠️ {self.chain.upper()} 블록 탐색기 API 오류: {error_msg}")
                
                # 특정 에러 처리
                if isinstance(result_msg, str):
                    if 'missing chainid' in result_msg.lower() or 'chainid' in result_msg.lower():
                        logger.error("❌ chainid 파라미터가 누락되었습니다.")
                    elif 'rate limit' in result_msg.lower() or 'max rate limit' in result_msg.lower():
                        logger.error("❌ API Rate Limit에 도달했습니다. 잠시 후 다시 시도하세요.")
                    elif 'invalid api key' in result_msg.lower() or 'api key' in result_msg.lower():
                        logger.error("❌ API 키가 유효하지 않습니다. config/.env 파일을 확인하세요.")
                    elif 'no transactions found' in result_msg.lower() or result_msg == '[]':
                        logger.info("ℹ️ 해당 주소에 거래 내역이 없습니다.")
                
                return []
            
            else:
                error_msg = data.get('message', 'Unknown error')
                logger.error(f"❌ API Error: {error_msg}")
                return []
        
        except Exception as e:
            logger.error(f"❌ 거래 조회 중 예상치 못한 오류: {e}")
            return []
    
    def _parse_transactions(self, transactions: List[Dict]) -> List[Dict[str, Any]]:
        """
        Etherscan 거래 데이터 파싱 및 정제
        
        Parameters:
        -----------
        transactions : List[Dict]
            Etherscan API 응답
        
        Returns:
        --------
        List[Dict] : 정제된 거래 데이터
        """
        parsed = []
        # ETH 가격은 한 번만 조회 (성능 최적화)
        eth_to_usd_rate = self._get_eth_to_usd_rate()
        
        for tx in transactions:
            try:
                # 필수 필드 존재 확인
                required_fields = ['value', 'gasUsed', 'gasPrice', 'hash', 'blockNumber', 
                                 'timeStamp', 'from', 'txreceipt_status']
                missing_fields = [field for field in required_fields if field not in tx or tx[field] is None]
                
                if missing_fields:
                    logger.warning(f"⚠️ 필수 필드 누락: {missing_fields}, 거래 스킵")
                    continue
                
                # Wei를 ETH로 변환 (1 ETH = 10^18 Wei)
                amount_eth = float(tx['value']) / 10**18
                
                # 가스비 계산
                gas_used = float(tx['gasUsed'])
                gas_price = float(tx['gasPrice'])
                gas_fee_eth = (gas_used * gas_price) / 10**18
                
                # USD 가치 계산
                amount_usd = amount_eth * eth_to_usd_rate
                gas_fee_usd = gas_fee_eth * eth_to_usd_rate
                
                # 고래 판정
                is_whale = amount_eth >= self.min_whale_eth or amount_usd >= self.min_whale_usd
                
                if not is_whale:
                    continue  # 고래가 아니면 스킵
                
                # 고래 분류
                whale_category = self._classify_whale(amount_usd)
                
                # 타임스탬프 처리 (문자열 또는 숫자 모두 지원)
                try:
                    timestamp = int(tx['timeStamp'])
                    block_timestamp = datetime.fromtimestamp(timestamp)
                except (ValueError, TypeError, OSError) as e:
                    logger.warning(f"⚠️ 타임스탬프 파싱 실패: {tx.get('timeStamp')}, {e}")
                    continue
                
                # datetime을 ISO 형식 문자열로 변환 (Supabase JSON 직렬화 호환)
                block_timestamp_str = block_timestamp.isoformat()
                
                # input_data 처리 및 함수 시그니처 디코딩 (선택적)
                input_data_str = str(tx.get('input', ''))
                method_id = None
                function_name = None
                
                if FUNCTION_DECODER_AVAILABLE and input_data_str and len(input_data_str) > 10:
                    try:
                        method_id = extract_method_id(input_data_str)
                        if method_id:
                            # 함수 시그니처 디코딩 (선택적, 느릴 수 있으므로 로깅만)
                            decoded = decode_input_data(input_data_str)
                            if decoded:
                                function_name = decoded.get('function_name')
                                if function_name:
                                    logger.debug(f"🔍 {tx['hash'][:10]}... 함수: {function_name}")
                    except Exception as e:
                        logger.debug(f"⚠️ 함수 시그니처 디코딩 실패: {e}")
                
                parsed_tx = {
                    'tx_hash': str(tx['hash']),
                    'block_number': int(tx['blockNumber']),
                    'block_timestamp': block_timestamp_str,  # ISO 형식 문자열로 저장
                    'from_address': str(tx['from']).lower(),
                    'to_address': str(tx['to']).lower() if tx.get('to') else None,
                    'coin_symbol': self.native_coin,  # ETH 또는 MATIC
                    'chain': self.chain,  # 체인 정보 추가
                    'amount': amount_eth,
                    'amount_usd': amount_usd,
                    'gas_used': int(gas_used),
                    'gas_price': int(gas_price),
                    'gas_fee_eth': gas_fee_eth,
                    'gas_fee_usd': gas_fee_usd,
                    'transaction_status': 'SUCCESS' if str(tx['txreceipt_status']) == '1' else 'FAILED',
                    'is_whale': is_whale,
                    'whale_category': whale_category,
                    'contract_address': str(tx['contractAddress']).lower() if tx.get('contractAddress') else None,
                    'input_data': input_data_str,
                    'is_contract_to_contract': bool(str(tx.get('isError', '1')) == '0' and input_data_str not in [None, '', '0x']),
                    'has_method_id': len(input_data_str) > 10,
                    # 함수 디코딩 정보 (선택적, 나중에 배치 작업으로도 처리 가능)
                    'method_id': method_id,
                    'function_name': function_name,
                }
                
                parsed.append(parsed_tx)
            
            except Exception as e:
                logger.warning(f"⚠️ 거래 파싱 오류: {e}")
                continue
        
        return parsed
    
    def _get_eth_to_usd_rate(self, use_cache: bool = True) -> float:
        """
        현재 ETH/USD 환율 조회
        
        우선순위:
        1. Chainlink Price Feed (무료, Rate Limit 없음, 정확)
        2. 캐시된 가격 (5분 유효)
        3. 기본값 ($3500)
        
        Parameters:
        -----------
        use_cache : bool
            캐시 사용 여부 (기본값: True)
        
        Returns:
        --------
        float : ETH/USD 환율
        """
        current_time = time.time()
        
        # 캐시 확인 (5분 유효)
        if use_cache and self._eth_price_cache is not None:
            if current_time - self._last_price_fetch_time < self._price_cache_duration:
                logger.debug(f"💹 ETH 가격 (캐시): ${self._eth_price_cache:,.2f}")
                return self._eth_price_cache
        
        # Chainlink Price Feed 시도 (무료 온체인 가격)
        if CHAINLINK_AVAILABLE:
            try:
                chainlink_price = get_chainlink_eth_price(chain=self.chain)
                if chainlink_price and chainlink_price > 0:
                    # 캐시 저장
                    self._eth_price_cache = chainlink_price
                    self._last_price_fetch_time = time.time()
                    logger.info(f"💹 ETH 가격 (Chainlink): ${chainlink_price:,.2f}")
                    return chainlink_price
            except Exception as e:
                logger.debug(f"⚠️ Chainlink 가격 조회 실패 (무시하고 기본값 사용): {e}")
        
        # 기본값 사용 (Chainlink 실패 또는 사용 불가 시)
        default_rate = 3500.0
        
        # 캐시 저장
        self._eth_price_cache = default_rate
        self._last_price_fetch_time = time.time()
        
        logger.debug(f"💹 ETH 가격 (기본값): ${default_rate:,.2f}")
        return default_rate
    
    def _get_token_prices_batch(self, token_addresses: List[str]) -> Dict[str, float]:
        """
        여러 토큰의 가격을 배치로 조회 (현재는 제거됨)
        
        CoinGecko는 무료 한도가 너무 낮아 항상 실패하므로 제외됨.
        나중에 Chainlink, Uniswap Pool 등 다른 소스로 교체 예정.
        
        Parameters:
        -----------
        token_addresses : List[str]
            토큰 컨트랙트 주소 리스트
        
        Returns:
        --------
        Dict[str, float] : {token_address: price} 형태의 딕셔너리 (현재는 모두 0.0)
        """
        # 모든 토큰 가격을 0으로 반환 (나중에 배치 업데이트 작업으로 보완)
        logger.debug(f"💹 토큰 가격 조회 스킵 (나중에 Chainlink 등으로 업데이트 예정)")
        return {addr.lower(): 0.0 for addr in token_addresses}
    
    def _get_token_price_usd(self, token_address: str, token_symbol: str) -> Optional[float]:
        """
        ERC-20 토큰의 USD 가격 조회
        
        Fallback 전략 패턴 (우선순위):
        1. Uniswap V3 Pool (무료, Rate Limit 없음, 가장 빠름)
        2. 1inch Price API (무료, Rate Limit 있음, DEX 집계 가격)
        3. None 반환 (나중에 배치 업데이트 예정)
        
        Parameters:
        -----------
        token_address : str
            토큰 컨트랙트 주소 (0x로 시작)
        token_symbol : str
            토큰 심볼 (예: USDT, USDC)
        
        Returns:
        --------
        Optional[float] : 토큰의 USD 가격, 실패 시 None
        """
        # 1순위: Uniswap V3 Pool 시도
        if UNISWAP_AVAILABLE:
            try:
                # ETH 가격 조회 (Chainlink 또는 캐시)
                eth_price = self._get_eth_to_usd_rate()
                
                # Uniswap으로 토큰 가격 조회
                token_price = get_uniswap_token_price(
                    token_address=token_address,
                    chain=self.chain,
                    eth_price_usd=eth_price
                )
                
                if token_price and token_price > 0:
                    logger.debug(f"💹 {token_symbol} 가격 (Uniswap): ${token_price:,.4f}")
                    return token_price
            except Exception as e:
                logger.debug(f"⚠️ Uniswap 토큰 가격 조회 실패 ({token_symbol}): {e}")
        
        # 2순위: 1inch Price API 시도
        if ONEINCH_AVAILABLE:
            try:
                token_price = get_oneinch_token_price(
                    token_address=token_address,
                    chain=self.chain
                )
                
                if token_price and token_price > 0:
                    logger.debug(f"💹 {token_symbol} 가격 (1inch): ${token_price:,.4f}")
                    return token_price
            except Exception as e:
                logger.debug(f"⚠️ 1inch 토큰 가격 조회 실패 ({token_symbol}): {e}")
        
        # 모든 방법 실패 시 None 반환 (나중에 배치 업데이트 작업으로 보완)
        logger.debug(f"💹 {token_symbol} 가격 조회 실패 (나중에 업데이트 예정)")
        return None
    
    def _classify_whale(self, amount_usd: float) -> str:
        """고래 규모 분류"""
        if amount_usd >= 10_000_000:
            return 'MEGA_WHALE'  # $10M 이상
        elif amount_usd >= 5_000_000:
            return 'LARGE_WHALE'  # $5M-10M
        else:
            return 'WHALE'  # $1M-5M
    
    def get_wallet_token_transactions(self, 
                                      address: str, 
                                      page: int = 1, 
                                      offset: int = 10000) -> List[Dict[str, Any]]:
        """
        특정 지갑의 ERC-20 토큰 거래 이력 조회 (재시도 로직 포함)
        
        Parameters:
        -----------
        address : str
            이더리움 지갑 주소 (0x로 시작)
        page : int
            페이지 번호
        offset : int
            페이지당 결과 수 (최대 10,000)
        
        Returns:
        --------
        List[Dict] : 토큰 거래 데이터 리스트
        """
        # V2 API 파라미터 (chainid 필수)
        params = {
            'chainid': self.chainid,  # V2 API 필수 파라미터
            'module': 'account',
            'action': 'tokentx',
            'address': address,
            'startblock': 0,
            'endblock': 99999999,
            'page': page,
            'offset': offset,
            'sort': 'desc',
            'apikey': self.api_key
        }
        
        try:
            logger.info(f"🔍 {address[:10]}... ERC-20 토큰 거래 조회 중... (ChainID: {self.chainid})")
            
            # 재시도 로직 포함 API 요청
            data = self._make_api_request(params, f"{self.chain.upper()} 토큰 거래 조회")
            
            if data is None:
                return []
            
            if data.get('status') == '1':
                transactions = data.get('result', [])
                if not isinstance(transactions, list):
                    transactions = []
                    
                logger.info(f"✅ {len(transactions)}건의 토큰 거래 조회 완료")
                
                # 토큰 거래 파싱
                parsed_transactions = self._parse_token_transactions(transactions)
                return parsed_transactions
            
            elif data.get('status') == '0':
                error_msg = data.get('message', 'No transactions found')
                result_msg = data.get('result', '')
                
                # 에러 메시지 분석
                if isinstance(result_msg, str):
                    if 'no transactions found' in result_msg.lower() or result_msg == '[]':
                        logger.info(f"ℹ️ {address[:10]}...에 토큰 거래 내역이 없습니다.")
                
                return []
            
            else:
                error_msg = data.get('message', 'Unknown error')
                logger.warning(f"⚠️ 토큰 거래 조회 오류: {error_msg}")
                return []
        
        except Exception as e:
            logger.error(f"❌ 토큰 거래 조회 중 예상치 못한 오류: {e}")
            return []
    
    def _parse_token_transactions(self, transactions: List[Dict]) -> List[Dict[str, Any]]:
        """
        Etherscan ERC-20 토큰 거래 데이터 파싱 및 정제
        
        Parameters:
        -----------
        transactions : List[Dict]
            Etherscan API 응답 (tokentx)
        
        Returns:
        --------
        List[Dict] : 정제된 토큰 거래 데이터
        """
        parsed = []
        
        if not transactions:
            return parsed
        
        # ETH 가격은 한 번만 조회 (전체 거래에서 재사용)
        eth_to_usd_rate = self._get_eth_to_usd_rate()
        
        # 1단계: 모든 고유 토큰 주소 수집
        unique_token_addresses = set()
        for tx in transactions:
            if 'contractAddress' in tx and tx['contractAddress']:
                unique_token_addresses.add(str(tx['contractAddress']).lower())
        
        # 2단계: 토큰 가격 조회
        # Uniswap V3 Pool을 통한 실시간 가격 조회 (무료)
        token_prices = {}
        
        if unique_token_addresses:
            logger.info(f"💹 {len(unique_token_addresses)}개 고유 토큰 발견 (Uniswap V3 Pool 가격 조회 시도)")
            
            # 각 토큰에 대해 Uniswap 가격 조회 시도
            # 참고: 많은 토큰의 경우 Pool이 없을 수 있으므로 None 허용
            for token_address in unique_token_addresses:
                token_price = self._get_token_price_usd(
                    token_address=token_address,
                    token_symbol='UNKNOWN'  # 심볼은 나중에 알 수 있음
                )
                if token_price and token_price > 0:
                    token_prices[token_address.lower()] = token_price
            
            # 가격 조회 성공률 로깅
            success_count = len(token_prices)
            if success_count > 0:
                logger.info(f"✅ {success_count}/{len(unique_token_addresses)}개 토큰 가격 조회 성공")
            else:
                logger.info(f"⚠️ 토큰 가격 조회 실패 (나중에 배치 업데이트 예정)")
        
        # 3단계: 거래 파싱 (가격은 이미 조회됨)
        for tx in transactions:
            try:
                # 필수 필드 존재 확인
                required_fields = ['value', 'gasUsed', 'gasPrice', 'hash', 'blockNumber', 
                                 'timeStamp', 'from', 'to', 'tokenName', 'tokenSymbol', 
                                 'tokenDecimal', 'contractAddress']
                missing_fields = [field for field in required_fields if field not in tx or tx[field] is None]
                
                if missing_fields:
                    logger.warning(f"⚠️ 필수 필드 누락: {missing_fields}, 토큰 거래 스킵")
                    continue
                
                # 토큰 정보 추출
                token_name = str(tx['tokenName'])
                token_symbol = str(tx['tokenSymbol']).upper()
                token_decimal = int(tx['tokenDecimal'])
                contract_address = str(tx['contractAddress']).lower()
                
                # 토큰 수량 계산 (tokenDecimal 사용)
                # value는 이미 정수 형태의 토큰 수량 (decimal 적용 전)
                token_amount = float(tx['value']) / (10 ** token_decimal)
                
                # 토큰 USD 가격 조회 (Uniswap에서 조회한 가격 사용, 없으면 None)
                token_price_usd = token_prices.get(contract_address)
                
                # USD 가치 계산 (가격이 0이면 NULL로 저장)
                amount_usd = token_amount * token_price_usd if token_price_usd > 0 else None
                
                # 가스비 계산 (ETH 기준)
                gas_used = float(tx['gasUsed'])
                gas_price = float(tx['gasPrice'])
                gas_fee_eth = (gas_used * gas_price) / 10**18
                
                # ETH 가격은 이미 조회됨
                gas_fee_usd = gas_fee_eth * eth_to_usd_rate
                
                # 고래 판정: 가격이 없어도 토큰 수량 정보는 저장
                # amount_usd가 None이거나 0이면 일단 저장하고 나중에 가격 업데이트
                # 현재는 amount_usd가 None이거나 0이면 whale_category를 NULL로 설정
                is_whale = True  # 가격 조회 실패해도 일단 저장
                
                # 고래 분류 (가격이 있을 때만)
                if amount_usd and amount_usd > 0:
                    whale_category = self._classify_whale(amount_usd)
                else:
                    whale_category = None  # 가격 없음, 나중에 업데이트 예정
                
                # 타임스탬프 처리
                try:
                    timestamp = int(tx['timeStamp'])
                    block_timestamp = datetime.fromtimestamp(timestamp)
                except (ValueError, TypeError, OSError) as e:
                    logger.warning(f"⚠️ 타임스탬프 파싱 실패: {tx.get('timeStamp')}, {e}")
                    continue
                
                # datetime을 ISO 형식 문자열로 변환 (Supabase JSON 직렬화 호환)
                block_timestamp_str = block_timestamp.isoformat()
                
                # input_data 처리 및 함수 시그니처 디코딩 (선택적)
                input_data_str = str(tx.get('input', ''))
                method_id = None
                function_name = None
                
                if FUNCTION_DECODER_AVAILABLE and input_data_str and len(input_data_str) > 10:
                    try:
                        method_id = extract_method_id(input_data_str)
                        if method_id:
                            decoded = decode_input_data(input_data_str)
                            if decoded:
                                function_name = decoded.get('function_name')
                    except Exception as e:
                        logger.debug(f"⚠️ 함수 시그니처 디코딩 실패: {e}")
                
                parsed_tx = {
                    'tx_hash': str(tx['hash']),
                    'block_number': int(tx['blockNumber']),
                    'block_timestamp': block_timestamp_str,
                    'from_address': str(tx['from']).lower(),
                    'to_address': str(tx['to']).lower() if tx.get('to') else None,
                    'coin_symbol': token_symbol,  # 토큰 심볼 저장
                    'chain': self.chain,  # 체인 정보 추가
                    'token_name': token_name,
                    'contract_address': contract_address,
                    'amount': token_amount,  # 토큰 수량 (decimal 적용됨)
                    'amount_usd': amount_usd,
                    'gas_used': int(gas_used),
                    'gas_price': int(gas_price),
                    'gas_fee_eth': gas_fee_eth,
                    'gas_fee_usd': gas_fee_usd,
                    'transaction_status': 'SUCCESS' if str(tx.get('txreceipt_status', '1')) == '1' else 'FAILED',
                    'is_whale': is_whale,
                    'whale_category': whale_category,
                    'input_data': input_data_str,
                    'is_contract_to_contract': bool(str(tx.get('isError', '0')) == '0' and input_data_str not in [None, '', '0x']),
                    'has_method_id': len(input_data_str) > 10,
                    # 함수 디코딩 정보 (선택적)
                    'method_id': method_id,
                    'function_name': function_name,
                }
                
                parsed.append(parsed_tx)
            
            except Exception as e:
                logger.warning(f"⚠️ 토큰 거래 파싱 오류: {e}")
                continue
        
        return parsed
    
    def collect_from_addresses(self, addresses: List[str]) -> List[Dict[str, Any]]:
        """
        여러 지갑에서 ETH 거래 수집
        
        Parameters:
        -----------
        addresses : List[str]
            지갑 주소 리스트
        
        Returns:
        --------
        List[Dict] : 모든 거래 데이터
        """
        all_transactions = []
        
        for i, address in enumerate(addresses, 1):
            logger.info(f"\n📋 [{i}/{len(addresses)}] {address[:10]}... 처리 중...")
            
            transactions = self.get_wallet_transactions(address)
            all_transactions.extend(transactions)
            
            # API 속도 제한 대응
            if i < len(addresses):
                time.sleep(self.api_delay)
        
        logger.info(f"\n✅ 총 {len(all_transactions)}건의 고래 거래 수집 완료")
        return all_transactions
    
    def collect_token_transactions_from_addresses(self, addresses: List[str]) -> List[Dict[str, Any]]:
        """
        여러 지갑에서 ERC-20 토큰 거래 수집
        
        Parameters:
        -----------
        addresses : List[str]
            지갑 주소 리스트
        
        Returns:
        --------
        List[Dict] : 모든 토큰 거래 데이터
        """
        all_transactions = []
        
        for i, address in enumerate(addresses, 1):
            logger.info(f"\n📋 [{i}/{len(addresses)}] {address[:10]}... 토큰 거래 처리 중...")
            
            transactions = self.get_wallet_token_transactions(address)
            all_transactions.extend(transactions)
            
            # API 속도 제한 대응
            if i < len(addresses):
                time.sleep(self.api_delay)
        
        logger.info(f"\n✅ 총 {len(all_transactions)}건의 고래 토큰 거래 수집 완료")
        return all_transactions
    
    def get_wallet_internal_transactions(self, 
                                         address: str, 
                                         page: int = 1, 
                                         offset: int = 10000) -> List[Dict[str, Any]]:
        """
        특정 지갑의 내부 거래(Internal Transactions) 조회 (재시도 로직 포함)
        스마트 컨트랙트 호출로 인한 내부 거래를 수집합니다.
        
        Parameters:
        -----------
        address : str
            이더리움 지갑 주소 (0x로 시작)
        page : int
            페이지 번호
        offset : int
            페이지당 결과 수 (최대 10,000)
        
        Returns:
        --------
        List[Dict] : 내부 거래 데이터 리스트
        """
        # V2 API 파라미터 (chainid 필수)
        params = {
            'chainid': self.chainid,  # V2 API 필수 파라미터
            'module': 'account',
            'action': 'txlistinternal',
            'address': address,
            'startblock': 0,
            'endblock': 99999999,
            'page': page,
            'offset': offset,
            'sort': 'desc',
            'apikey': self.api_key
        }
        
        try:
            logger.info(f"🔍 {address[:10]}... 내부 거래 조회 중... (ChainID: {self.chainid})")
            
            # 재시도 로직 포함 API 요청
            data = self._make_api_request(params, f"{self.chain.upper()} 내부 거래 조회")
            
            if data is None:
                return []
            
            if data.get('status') == '1':
                transactions = data.get('result', [])
                if not isinstance(transactions, list):
                    transactions = []
                    
                logger.info(f"✅ {len(transactions)}건의 내부 거래 조회 완료")
                
                # 내부 거래 파싱
                parsed_transactions = self._parse_internal_transactions(transactions)
                return parsed_transactions
            
            elif data.get('status') == '0':
                error_msg = data.get('message', 'No transactions found')
                result_msg = data.get('result', '')
                
                # 에러 메시지 분석
                if isinstance(result_msg, str):
                    if 'no transactions found' in result_msg.lower() or result_msg == '[]':
                        logger.info(f"ℹ️ {address[:10]}...에 내부 거래 내역이 없습니다.")
                
                return []
            
            else:
                error_msg = data.get('message', 'Unknown error')
                logger.warning(f"⚠️ 내부 거래 조회 오류: {error_msg}")
                return []
        
        except Exception as e:
            logger.error(f"❌ 내부 거래 조회 중 예상치 못한 오류: {e}")
            return []
    
    def _parse_internal_transactions(self, transactions: List[Dict]) -> List[Dict[str, Any]]:
        """
        Etherscan 내부 거래 데이터 파싱 및 정제
        type=call이고 isError=0인 성공적인 거래만 필터링
        
        Parameters:
        -----------
        transactions : List[Dict]
            Etherscan API 응답 (txlistinternal)
        
        Returns:
        --------
        List[Dict] : 정제된 내부 거래 데이터
        """
        parsed = []
        
        if not transactions:
            return parsed
        
        # ETH 가격 조회 (USD 계산용)
        eth_to_usd_rate = self._get_eth_to_usd_rate()
        
        for tx in transactions:
            try:
                # 필수 필드 존재 확인
                required_fields = ['value', 'from', 'to', 'hash', 'blockNumber', 
                                 'timeStamp', 'type', 'isError']
                missing_fields = [field for field in required_fields if field not in tx or tx[field] is None]
                
                if missing_fields:
                    logger.warning(f"⚠️ 필수 필드 누락: {missing_fields}, 내부 거래 스킵")
                    continue
                
                # type=call이고 isError=0인 거래만 필터링
                tx_type = str(tx.get('type', '')).lower()
                is_error = str(tx.get('isError', '1'))
                
                if tx_type != 'call' or is_error != '0':
                    continue  # call 타입이 아니거나 에러가 있는 거래는 스킵
                
                # Wei를 ETH로 변환 (1 ETH = 10^18 Wei)
                value_eth = float(tx['value']) / 10**18
                
                # USD 가치 계산
                value_usd = value_eth * eth_to_usd_rate
                
                # 타임스탬프 처리
                try:
                    timestamp = int(tx['timeStamp'])
                    block_timestamp = datetime.fromtimestamp(timestamp)
                except (ValueError, TypeError, OSError) as e:
                    logger.warning(f"⚠️ 타임스탬프 파싱 실패: {tx.get('timeStamp')}, {e}")
                    continue
                
                # datetime을 ISO 형식 문자열로 변환
                block_timestamp_str = block_timestamp.isoformat()
                
                parsed_tx = {
                    'tx_hash': str(tx['hash']),
                    'block_number': int(tx['blockNumber']),
                    'block_timestamp': block_timestamp_str,
                    'from_address': str(tx['from']).lower(),
                    'to_address': str(tx['to']).lower() if tx.get('to') else None,
                    'contract_address': str(tx['contractAddress']).lower() if tx.get('contractAddress') else None,
                    'chain': self.chain,  # 체인 정보 추가
                    'value_eth': value_eth,
                    'value_usd': value_usd,
                    'transaction_type': tx_type.upper(),  # CALL, CREATE, SUICIDE 등
                    'is_error': is_error == '0',
                    'trace_id': str(tx.get('traceId', '')),  # 내부 거래 추적 ID
                    'input_data': str(tx.get('input', '')),
                    'gas': int(tx['gas']) if tx.get('gas') else None,
                    'gas_used': int(tx['gasUsed']) if tx.get('gasUsed') else None,
                }
                
                parsed.append(parsed_tx)
            
            except Exception as e:
                logger.warning(f"⚠️ 내부 거래 파싱 오류: {e}")
                continue
        
        return parsed
    
    def collect_internal_transactions_from_addresses(self, addresses: List[str]) -> List[Dict[str, Any]]:
        """
        여러 지갑에서 내부 거래 수집
        
        Parameters:
        -----------
        addresses : List[str]
            지갑 주소 리스트
        
        Returns:
        --------
        List[Dict] : 모든 내부 거래 데이터
        """
        all_transactions = []
        
        for i, address in enumerate(addresses, 1):
            logger.info(f"\n📋 [{i}/{len(addresses)}] {address[:10]}... 내부 거래 처리 중...")
            
            transactions = self.get_wallet_internal_transactions(address)
            all_transactions.extend(transactions)
            
            # API 속도 제한 대응
            if i < len(addresses):
                time.sleep(self.api_delay)
        
        logger.info(f"\n✅ 총 {len(all_transactions)}건의 내부 거래 수집 완료")
        return all_transactions
    
    def get_current_balance(self, address: str) -> float:
        """특정 지갑의 현재 ETH 잔액 조회"""
        params = {
            'chainid': self.chainid,  # V2 API 필수 파라미터
            'module': 'account',
            'action': 'balance',
            'address': address,
            'tag': 'latest',
            'apikey': self.api_key
        }
        
        try:
            response = requests.get(self.base_url_v2, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '1':
                balance_wei = float(data.get('result', 0))
                balance_eth = balance_wei / 10**18
                return balance_eth
            else:
                logger.warning(f"⚠️ 잔액 조회 실패: {data.get('message', 'Unknown error')}")
                return 0.0
        
        except Exception as e:
            logger.warning(f"⚠️ 잔액 조회 실패: {e}")
            return 0.0
    
    def filter_transactions(self, 
                          transactions: List[Dict[str, Any]],
                          min_amount_usd: float = None,
                          min_amount_eth: float = None) -> List[Dict[str, Any]]:
        """
        거래 필터링
        
        가격 조회 실패한 토큰 거래도 저장하도록 수정:
        - amount_usd가 None이거나 0이어도 토큰 거래는 저장
        - ETH 거래는 기존과 동일하게 필터링
        """
        if min_amount_usd is None:
            min_amount_usd = self.min_whale_usd
        if min_amount_eth is None:
            min_amount_eth = self.min_whale_eth
        
        filtered = []
        for tx in transactions:
            # 토큰 거래인 경우 (contract_address가 있거나 coin_symbol이 ETH가 아닌 경우)
            is_token_tx = (
                tx.get('contract_address') is not None or 
                (tx.get('coin_symbol', 'ETH').upper() != 'ETH' and 
                 tx.get('coin_symbol', 'ETH').upper() != 'MATIC')
            )
            
            # 토큰 거래는 가격이 없어도 저장 (나중에 가격 업데이트 예정)
            if is_token_tx:
                filtered.append(tx)
            else:
                # ETH/MATIC 거래는 기존 필터링 로직 적용
                amount_usd = tx.get('amount_usd')
                amount = tx.get('amount', 0)
                
                if (amount_usd and amount_usd >= min_amount_usd) or amount >= min_amount_eth:
                    filtered.append(tx)
        
        logger.info(f"✅ {len(filtered)}/{len(transactions)}건 필터링 완료 (최소 기준: ${min_amount_usd:,.0f})")
        logger.info(f"   - 토큰 거래는 가격 없이도 저장됨 (나중에 가격 업데이트 예정)")
        return filtered
