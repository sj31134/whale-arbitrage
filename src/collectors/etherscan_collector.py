# src/collectors/etherscan_collector.py

import requests
import os
import time
from dotenv import load_dotenv
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from src.utils.logger import logger

# 환경변수 로드
load_dotenv('config/.env')

class EtherscanCollector:
    """Etherscan API를 통한 거래 데이터 수집"""
    
    def __init__(self):
        """Etherscan 수집기 초기화"""
        self.api_key = os.getenv('ETHERSCAN_API_KEY')
        # Etherscan API - V1은 deprecated되었으므로 V2 사용 (chainid 필수)
        self.base_url_v1 = 'https://api.etherscan.io/api'
        self.base_url_v2 = 'https://api.etherscan.io/v2/api'
        # 이더리움 메인넷 chainid = 1
        self.chainid = int(os.getenv('ETHERSCAN_CHAINID', 1))
        self.base_url = self.base_url_v2  # V2를 기본값으로 사용
        self.min_whale_eth = float(os.getenv('MIN_WHALE_AMOUNT_ETH', 10))
        self.min_whale_usd = float(os.getenv('MIN_WHALE_AMOUNT_USD', 50000))
        self.api_delay = float(os.getenv('API_DELAY_SECONDS', 0.5))  # Rate limit 방지
        
        # 가격 캐시 (API 호출 최소화)
        self._eth_price_cache = None
        self._token_price_cache = {}
        self._last_price_fetch_time = 0
        self._last_token_price_fetch_time = 0
        self._price_cache_duration = 300  # 5분 캐시 유지 (무료 API rate limit 방지)
        
        if not self.api_key:
            raise ValueError("❌ ETHERSCAN_API_KEY가 설정되지 않았습니다")
        
        logger.info(f"✅ Etherscan 수집기 초기화 완료 (API V2, ChainID: {self.chainid})")
        logger.info(f"   - 고래 기준 (ETH): {self.min_whale_eth}")
        logger.info(f"   - 고래 기준 (USD): ${self.min_whale_usd:,.0f}")
        logger.info(f"   - 가격 캐시: {self._price_cache_duration}초")
    
    def get_wallet_transactions(self, 
                               address: str, 
                               page: int = 1, 
                               offset: int = 10000) -> List[Dict[str, Any]]:
        """
        특정 지갑의 거래 이력 조회
        
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
            
            # V2 API 직접 사용 (V1은 deprecated)
            response = requests.get(self.base_url_v2, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
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
                logger.warning(f"⚠️ Etherscan API 오류: {error_msg}")
                logger.warning(f"📋 전체 API 응답: {data}")
                
                # 특정 에러 처리
                if isinstance(result_msg, str):
                    if 'missing chainid' in result_msg.lower() or 'chainid' in result_msg.lower():
                        logger.error("❌ chainid 파라미터가 누락되었습니다. ETHERSCAN_CHAINID 환경변수를 확인하세요.")
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
                logger.error(f"📋 전체 API 응답: {data}")
                return []
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request failed: {e}")
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
                
                parsed_tx = {
                    'tx_hash': str(tx['hash']),
                    'block_number': int(tx['blockNumber']),
                    'block_timestamp': block_timestamp_str,  # ISO 형식 문자열로 저장
                    'from_address': str(tx['from']).lower(),
                    'to_address': str(tx['to']).lower() if tx.get('to') else None,
                    'coin_symbol': 'ETH',
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
                    'input_data': str(tx.get('input', '')),
                    'is_contract_to_contract': bool(str(tx.get('isError', '1')) == '0' and tx.get('input') not in [None, '', '0x']),
                    'has_method_id': len(str(tx.get('input', ''))) > 10,
                }
                
                parsed.append(parsed_tx)
            
            except Exception as e:
                logger.warning(f"⚠️ 거래 파싱 오류: {e}")
                continue
        
        return parsed
    
    def _get_eth_to_usd_rate(self, use_cache: bool = True) -> float:
        """
        현재 ETH/USD 환율 조회 (캐시 사용으로 API 호출 최소화)
        
        Parameters:
        -----------
        use_cache : bool
            캐시 사용 여부 (기본값: True)
        
        Returns:
        --------
        float : ETH/USD 환율
        """
        import time
        
        current_time = time.time()
        
        # 캐시 확인 (5분 유효)
        if use_cache and self._eth_price_cache is not None:
            if current_time - self._last_price_fetch_time < self._price_cache_duration:
                return self._eth_price_cache
        
        try:
            # CoinGecko API에서 현재 가격 조회 (무료, 빠름)
            # Rate limit 방지를 위한 딜레이 (CoinGecko 무료 플랜: 분당 10-50회)
            # 첫 실행 시 최소 10초 대기, 이후 호출은 60초 간격 유지
            if self._last_price_fetch_time > 0:
                time_since_last = current_time - self._last_price_fetch_time
                if time_since_last < 60.0:  # 최소 60초 간격 (무료 플랜 안전)
                    wait_time = 60.0 - time_since_last
                    logger.debug(f"⏳ Rate Limit 방지: {wait_time:.1f}초 대기 중...")
                    time.sleep(wait_time)
            else:
                # 첫 실행 시 10초 대기
                logger.debug("⏳ 첫 가격 조회 전 10초 대기 중...")
                time.sleep(10.0)
            
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/price',
                params={'ids': 'ethereum', 'vs_currencies': 'usd'},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # 응답 구조 확인
            if 'ethereum' in data and 'usd' in data['ethereum']:
                rate = float(data['ethereum']['usd'])
                # 캐시 저장
                self._eth_price_cache = rate
                self._last_price_fetch_time = time.time()
                logger.debug(f"💹 현재 ETH 가격: ${rate:,.2f}")
                return rate
            else:
                logger.warning(f"⚠️ ETH 가격 응답 구조 이상: {data}")
                if self._eth_price_cache is not None:
                    logger.info(f"   캐시된 가격 사용: ${self._eth_price_cache:,.2f}")
                    return self._eth_price_cache
                return 3500.0  # 폴백
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                logger.warning(f"⚠️ CoinGecko Rate Limit 도달")
                # Rate Limit에 걸렸다면 다음 실행까지 충분히 대기하도록 시간 갱신
                self._last_price_fetch_time = current_time
                if self._eth_price_cache is not None:
                    logger.info(f"   캐시된 가격 사용: ${self._eth_price_cache:,.2f}")
                    return self._eth_price_cache
                logger.warning("   다음 실행까지 최소 60초 이상 대기 후 다시 시도하세요")
            logger.warning(f"⚠️ ETH 가격 조회 실패: {e}")
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"⚠️ ETH 가격 파싱 실패: {e}")
        except Exception as e:
            logger.warning(f"⚠️ ETH 가격 조회 실패: {e}")
        
        # 에러 시 캐시 또는 기본값 사용
        if self._eth_price_cache is not None:
            logger.info(f"   캐시된 ETH 가격 사용: ${self._eth_price_cache:,.2f}")
            return self._eth_price_cache
        
        logger.warning("   기본값 $3500 사용")
        return 3500.0  # 폴백 가격
    
    def _get_token_prices_batch(self, token_addresses: List[str]) -> Dict[str, float]:
        """
        여러 토큰의 가격을 배치로 조회 (API 호출 최소화)
        
        Parameters:
        -----------
        token_addresses : List[str]
            토큰 컨트랙트 주소 리스트
        
        Returns:
        --------
        Dict[str, float] : {token_address: price} 형태의 딕셔너리
        """
        if not token_addresses:
            return {}
        
        prices = {}
        
        try:
            # CoinGecko API는 최대 50개 토큰까지 배치 조회 가능 (무료 플랜)
            # 주소를 쉼표로 구분하여 한 번에 조회
            addresses_str = ','.join([addr.lower() for addr in token_addresses[:50]])  # 최대 50개
            
            # Rate limit 방지: 토큰 가격 조회 전 최소 60초 대기
            import time
            current_time = time.time()
            if hasattr(self, '_last_token_price_fetch_time'):
                time_since_last = current_time - self._last_token_price_fetch_time
                if time_since_last < 60.0:
                    wait_time = 60.0 - time_since_last
                    logger.debug(f"⏳ 토큰 가격 조회 전 {wait_time:.1f}초 대기 중...")
                    time.sleep(wait_time)
            
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/token_price/ethereum',
                params={'contract_addresses': addresses_str, 'vs_currencies': 'usd'},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # 조회 시간 갱신
            self._last_token_price_fetch_time = time.time()
            
            for addr in token_addresses:
                addr_lower = addr.lower()
                if addr_lower in data and 'usd' in data[addr_lower]:
                    prices[addr_lower] = float(data[addr_lower]['usd'])
                else:
                    prices[addr_lower] = 0.0
            
            logger.debug(f"💹 {len([p for p in prices.values() if p > 0])}개 토큰 가격 조회 완료")
            return prices
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                logger.warning(f"⚠️ CoinGecko Rate Limit 도달 (토큰 가격)")
                # Rate Limit에 걸렸다면 다음 실행까지 충분히 대기하도록 시간 갱신
                if hasattr(self, '_last_token_price_fetch_time'):
                    self._last_token_price_fetch_time = time.time()
                logger.warning("   다음 실행까지 최소 60초 이상 대기 후 다시 시도하세요")
            else:
                logger.warning(f"⚠️ 토큰 가격 배치 조회 실패: {e}")
        except Exception as e:
            logger.warning(f"⚠️ 토큰 가격 배치 조회 실패: {e}")
        
        # 실패 시 모든 토큰에 대해 0 반환
        return {addr.lower(): 0.0 for addr in token_addresses}
    
    def _get_token_price_usd(self, token_address: str, token_symbol: str) -> float:
        """
        ERC-20 토큰의 USD 가격 조회 (캐시 사용)
        
        Parameters:
        -----------
        token_address : str
            토큰 컨트랙트 주소 (0x로 시작)
        token_symbol : str
            토큰 심볼 (예: USDT, USDC)
        
        Returns:
        --------
        float : 토큰의 USD 가격
        """
        addr_lower = token_address.lower()
        
        # 캐시 확인
        if addr_lower in self._token_price_cache:
            return self._token_price_cache[addr_lower]
        
        try:
            # 단일 토큰 조회 (배치가 불가능한 경우)
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/token_price/ethereum',
                params={'contract_addresses': addr_lower, 'vs_currencies': 'usd'},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if addr_lower in data and 'usd' in data[addr_lower]:
                price = float(data[addr_lower]['usd'])
                # 캐시 저장
                self._token_price_cache[addr_lower] = price
                logger.debug(f"💹 {token_symbol} 가격: ${price:,.2f}")
                return price
            else:
                # 가격을 찾을 수 없음 (없는 토큰이거나 rate limit)
                self._token_price_cache[addr_lower] = 0.0
                logger.debug(f"⚠️ {token_symbol} 가격 조회 실패 (주소: {token_address[:10]}...), $0 사용")
                return 0.0
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                logger.warning(f"⚠️ CoinGecko Rate Limit 도달 ({token_symbol})")
            self._token_price_cache[addr_lower] = 0.0
            return 0.0
        except Exception as e:
            logger.debug(f"⚠️ {token_symbol} 가격 조회 실패: {e}, $0 사용")
            self._token_price_cache[addr_lower] = 0.0
            return 0.0
    
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
        특정 지갑의 ERC-20 토큰 거래 이력 조회
        
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
            
            # V2 API 직접 사용 (V1은 deprecated)
            response = requests.get(self.base_url_v2, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
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
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 토큰 거래 조회 실패: {e}")
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
        
        # 2단계: 배치로 토큰 가격 조회 (API 호출 최소화)
        token_addresses_list = list(unique_token_addresses)
        batch_size = 50  # CoinGecko 무료 플랜 배치 제한
        token_prices = {}
        
        if not token_addresses_list:
            logger.debug("ℹ️ 조회할 토큰이 없습니다")
        else:
            logger.info(f"💹 {len(token_addresses_list)}개 고유 토큰 가격 조회 중...")
        
        for i in range(0, len(token_addresses_list), batch_size):
            batch = token_addresses_list[i:i + batch_size]
            batch_prices = self._get_token_prices_batch(batch)
            token_prices.update(batch_prices)
            
            # Rate limit 방지 (배치 사이 최소 60초 간격 - 무료 플랜 안전)
            if i + batch_size < len(token_addresses_list):
                logger.debug(f"⏳ 다음 배치 전 60초 대기 중... ({i//batch_size + 1}/{len(token_addresses_list)//batch_size + 1})")
                time.sleep(60.0)  # 무료 플랜: 분당 10-50회 제한 고려
        
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
                
                # 토큰 USD 가격 조회 (배치 조회로 이미 가져온 가격 사용)
                token_price_usd = token_prices.get(contract_address, 0.0)
                
                # 캐시에도 저장 (다음번 개별 조회 방지)
                if contract_address not in self._token_price_cache:
                    self._token_price_cache[contract_address] = token_price_usd
                
                # USD 가치 계산
                amount_usd = token_amount * token_price_usd
                
                # 가스비 계산 (ETH 기준)
                gas_used = float(tx['gasUsed'])
                gas_price = float(tx['gasPrice'])
                gas_fee_eth = (gas_used * gas_price) / 10**18
                
                # ETH 가격은 이미 조회됨 (매개변수로 받음)
                gas_fee_usd = gas_fee_eth * eth_to_usd_rate
                
                # 고래 판정 (USD 기준만 사용, ETH 기준은 토큰에 적용 안 됨)
                is_whale = amount_usd >= self.min_whale_usd
                
                if not is_whale:
                    continue  # 고래가 아니면 스킵
                
                # 고래 분류
                whale_category = self._classify_whale(amount_usd)
                
                # 타임스탬프 처리
                try:
                    timestamp = int(tx['timeStamp'])
                    block_timestamp = datetime.fromtimestamp(timestamp)
                except (ValueError, TypeError, OSError) as e:
                    logger.warning(f"⚠️ 타임스탬프 파싱 실패: {tx.get('timeStamp')}, {e}")
                    continue
                
                # datetime을 ISO 형식 문자열로 변환 (Supabase JSON 직렬화 호환)
                block_timestamp_str = block_timestamp.isoformat()
                
                parsed_tx = {
                    'tx_hash': str(tx['hash']),
                    'block_number': int(tx['blockNumber']),
                    'block_timestamp': block_timestamp_str,
                    'from_address': str(tx['from']).lower(),
                    'to_address': str(tx['to']).lower() if tx.get('to') else None,
                    'coin_symbol': token_symbol,  # 토큰 심볼 저장
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
                    'input_data': str(tx.get('input', '')),
                    'is_contract_to_contract': bool(str(tx.get('isError', '0')) == '0' and tx.get('input') not in [None, '', '0x']),
                    'has_method_id': len(str(tx.get('input', ''))) > 10,
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
        특정 지갑의 내부 거래(Internal Transactions) 조회
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
            
            # V2 API 직접 사용 (V1은 deprecated)
            response = requests.get(self.base_url_v2, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
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
        
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 내부 거래 조회 실패: {e}")
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
        """거래 필터링"""
        if min_amount_usd is None:
            min_amount_usd = self.min_whale_usd
        if min_amount_eth is None:
            min_amount_eth = self.min_whale_eth
        
        filtered = [
            tx for tx in transactions
            if tx['amount'] >= min_amount_eth or tx['amount_usd'] >= min_amount_usd
        ]
        
        logger.info(f"✅ {len(filtered)}/{len(transactions)}건 필터링 완료 (최소 기준: ${min_amount_usd:,.0f})")
        return filtered
