#!/usr/bin/env python3
"""
BNB, USDC, XRP 고래 지갑 주소의 2025년 5-6월 거래 이력 수집
whale_address 테이블에서 주소를 조회하고, 블록체인 API로 거래 기록을 수집하여 whale_transactions에 저장
"""

import os
import sys
import time
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dotenv import load_dotenv
from supabase import create_client

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

# API 키 로드
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')
SOLSCAN_API_KEY = os.getenv('SOLSCAN_API_KEY', '')
XRPSCAN_API_URL = os.getenv('XRPSCAN_API_URL', 'https://api.xrpscan.com/api/v1')
XRP_LEDGER_API_URL = os.getenv('XRP_LEDGER_API_URL', 'https://s1.ripple.com:51234/')

# USDC 컨트랙트 주소 (네트워크별)
USDC_CONTRACTS = {
    'ethereum': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
    'bsc': '0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d',
    'polygon': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
    'arbitrum': '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',
    'optimism': '0x7F5c764cBc14f9669B88837ca1490cCa17c31607',
    'avalanche': '0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E',
    'solana': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # Mint Address
    'base': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
}

# 날짜 범위 설정 (7-8월로 확장)
START_DATE = datetime(2025, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
END_DATE = datetime(2025, 8, 31, 23, 59, 59, tzinfo=timezone.utc)


def is_valid_evm_address(address: str) -> bool:
    """
    EVM 주소 형식 검증 (Ethereum, BSC, Polygon 등)
    
    Parameters:
    -----------
    address : str
        주소 문자열
    
    Returns:
    --------
    bool : 유효한 EVM 주소인지 여부
    """
    if not address:
        return False
    address = address.strip()
    # EVM 주소는 0x로 시작하고 42자 (0x + 40자 hex)
    if address.startswith('0x') and len(address) == 42:
        try:
            # hex 문자인지 확인
            int(address[2:], 16)
            return True
        except ValueError:
            return False
    return False


def is_valid_solana_address(address: str) -> bool:
    """
    Solana 주소 형식 검증
    
    Parameters:
    -----------
    address : str
        주소 문자열
    
    Returns:
    --------
    bool : 유효한 Solana 주소인지 여부
    """
    if not address:
        return False
    address = address.strip()
    # EVM 형식 제외
    if address.startswith('0x'):
        return False
    # Solana 주소는 Base58 인코딩, 32-44자
    if 32 <= len(address) <= 44:
        # Base58 문자만 포함하는지 간단히 확인 (0, O, I, l 제외)
        valid_chars = set('123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz')
        if all(c in valid_chars for c in address):
            return True
    return False


def is_valid_xrp_address(address: str) -> bool:
    """
    XRP 주소 형식 검증
    XRP는 Ripple Base58 변형 사용 (0 포함)
    
    Parameters:
    -----------
    address : str
        주소 문자열
    
    Returns:
    --------
    bool : 유효한 XRP 주소인지 여부
    """
    if not address:
        return False
    address = address.strip()
    # XRP 주소는 r로 시작하고 25-35자, 영숫자만 포함
    if address.startswith('r') and 25 <= len(address) <= 35:
        # 영숫자만 확인 (XRP는 Ripple Base58 사용, 일부 특수문자 제외)
        if address.isalnum():
            return True
    return False


def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)


def get_whale_addresses_by_coin(supabase) -> Dict[str, Dict[str, List[str]]]:
    """
    whale_address 테이블에서 BNB, USDC, XRP 주소 조회
    
    Returns:
    --------
    Dict[str, Dict[str, List[str]]]: {
        'BNB': {'bsc': [addresses]},
        'USDC': {'ethereum': [addresses], 'bsc': [addresses], ...},
        'XRP': {'xrp': [addresses]}
    }
    """
    try:
        # BNB 주소 조회 (name_tag 조건 제거, EVM 주소만 필터링)
        bnb_response = supabase.table('whale_address').select('address').eq('chain_type', 'BSC').execute()
        bnb_addresses = [
            row['address'].strip().lower() 
            for row in bnb_response.data 
            if row.get('address') and is_valid_evm_address(row['address'])
        ]
        
        # USDC 주소 조회 (모든 네트워크)
        usdc_response = supabase.table('whale_address').select('chain_type, address').eq('name_tag', 'USD Coin').execute()
        usdc_by_network = {}
        for row in usdc_response.data:
            chain_type = row.get('chain_type', '').upper()
            address = row.get('address', '').strip()
            if not address:
                continue
            
            # chain_type을 네트워크 이름으로 매핑
            network_mapping = {
                'ETH': 'ethereum',
                'BSC': 'bsc',
                'POLYGON': 'polygon',
                'ARBITRUM': 'arbitrum',
                'OPTIMISM': 'optimism',
                'AVALANCHE': 'avalanche',
                'SOL': 'solana',
                'BASE': 'base'
            }
            network = network_mapping.get(chain_type, chain_type.lower())
            
            # 주소 형식 검증
            if network == 'solana':
                if not is_valid_solana_address(address):
                    continue  # Solana 주소 형식이 아니면 건너뛰기
            else:
                if not is_valid_evm_address(address):
                    continue  # EVM 주소 형식이 아니면 건너뛰기
            
            if network not in usdc_by_network:
                usdc_by_network[network] = []
            usdc_by_network[network].append(address.lower() if network != 'solana' else address)
        
        # XRP 주소 조회 (name_tag 조건 제거, 주소 형식 검증 추가)
        xrp_response = supabase.table('whale_address').select('address').eq('chain_type', 'XRP').execute()
        xrp_addresses = [
            row['address'].strip() 
            for row in xrp_response.data 
            if row.get('address') and is_valid_xrp_address(row['address'])
        ]
        
        result = {
            'BNB': {'bsc': bnb_addresses},
            'USDC': usdc_by_network,
            'XRP': {'xrp': xrp_addresses}
        }
        
        print("✅ whale_address에서 주소 조회 완료:")
        print(f"   - BNB (BSC): {len(bnb_addresses)}개")
        print(f"   - USDC: {sum(len(addrs) for addrs in usdc_by_network.values())}개 ({len(usdc_by_network)}개 네트워크)")
        print(f"   - XRP: {len(xrp_addresses)}개")
        
        return result
        
    except Exception as e:
        print(f"⚠️ whale_address 조회 실패: {e}")
        return {'BNB': {}, 'USDC': {}, 'XRP': {}}


def filter_by_date_range(transactions: List[Dict], start_date: datetime, end_date: datetime) -> List[Dict]:
    """
    거래 기록을 날짜 범위로 필터링
    
    Parameters:
    -----------
    transactions : List[Dict]
        거래 기록 리스트
    start_date : datetime
        시작 날짜
    end_date : datetime
        종료 날짜
    
    Returns:
    --------
    List[Dict] : 필터링된 거래 기록 리스트
    """
    filtered = []
    for tx in transactions:
        block_timestamp = tx.get('block_timestamp')
        if not block_timestamp:
            continue
        
        # datetime 객체로 변환
        if isinstance(block_timestamp, str):
            try:
                block_timestamp = datetime.fromisoformat(block_timestamp.replace('Z', '+00:00'))
            except:
                continue
        elif isinstance(block_timestamp, (int, float)):
            block_timestamp = datetime.fromtimestamp(block_timestamp, tz=timezone.utc)
        
        # 타임존이 없으면 UTC로 가정
        if block_timestamp.tzinfo is None:
            block_timestamp = block_timestamp.replace(tzinfo=timezone.utc)
        
        # 날짜 범위 확인
        if start_date <= block_timestamp <= end_date:
            filtered.append(tx)
    
    return filtered


def calculate_block_range_by_date(chain: str, start_date: datetime, end_date: datetime, api_key: str) -> Optional[Tuple[int, int]]:
    """
    날짜를 블록 번호로 변환 (Etherscan/BSCScan API 사용)
    실패 시 None 반환 (timestamp 필터링 사용)
    
    Parameters:
    -----------
    chain : str
        체인 이름 ('bsc', 'ethereum' 등)
    start_date : datetime
        시작 날짜
    end_date : datetime
        종료 날짜
    api_key : str
        API 키
    
    Returns:
    --------
    Optional[Tuple[int, int]]: (start_block, end_block) 또는 None
    """
    if not api_key:
        print(f"   ⚠️ {chain} API 키가 없어 블록 번호 계산을 건너뜁니다. timestamp 필터링을 사용합니다.")
        return None
    
    try:
        # API 엔드포인트 설정
        if chain.lower() == 'bsc':
            base_url = 'https://api.bscscan.com/api'
        elif chain.lower() in ['ethereum', 'eth']:
            base_url = 'https://api.etherscan.io/api'
        else:
            print(f"   ⚠️ {chain}는 블록 번호 계산을 지원하지 않습니다. timestamp 필터링을 사용합니다.")
            return None
        
        # 시작 블록 조회
        start_timestamp = int(start_date.timestamp())
        start_params = {
            'module': 'block',
            'action': 'getblocknobytime',
            'timestamp': start_timestamp,
            'closest': 'before',
            'apikey': api_key
        }
        
        try:
            start_response = requests.get(base_url, params=start_params, timeout=30)
            start_response.raise_for_status()
            start_data = start_response.json()
            
            if start_data.get('status') == '1' and start_data.get('result'):
                start_block = int(start_data['result'])
            else:
                error_msg = start_data.get('message', 'Unknown error')
                print(f"   ⚠️ {chain} 시작 블록 조회 실패: {error_msg}. timestamp 필터링을 사용합니다.")
                return None
        except Exception as e:
            print(f"   ⚠️ {chain} 시작 블록 조회 중 오류: {e}. timestamp 필터링을 사용합니다.")
            return None
        
        # 종료 블록 조회
        end_timestamp = int(end_date.timestamp())
        end_params = {
            'module': 'block',
            'action': 'getblocknobytime',
            'timestamp': end_timestamp,
            'closest': 'after',
            'apikey': api_key
        }
        
        try:
            end_response = requests.get(base_url, params=end_params, timeout=30)
            end_response.raise_for_status()
            end_data = end_response.json()
            
            if end_data.get('status') == '1' and end_data.get('result'):
                end_block = int(end_data['result'])
            else:
                error_msg = end_data.get('message', 'Unknown error')
                print(f"   ⚠️ {chain} 종료 블록 조회 실패: {error_msg}. timestamp 필터링을 사용합니다.")
                return None
            
            print(f"   ✅ {chain} 블록 범위 계산 완료: {start_block} ~ {end_block}")
            return (start_block, end_block)
            
        except Exception as e:
            print(f"   ⚠️ {chain} 종료 블록 조회 중 오류: {e}. timestamp 필터링을 사용합니다.")
            return None
        
    except Exception as e:
        print(f"   ⚠️ {chain} 블록 번호 계산 중 예상치 못한 오류: {e}. timestamp 필터링을 사용합니다.")
        return None


def fetch_bnb_transactions(addresses: List[str], api_key: str, start_date: datetime, end_date: datetime) -> List[Dict]:
    """
    BNB 거래 수집 (BSC 네트워크)
    
    Parameters:
    -----------
    addresses : List[str]
        지갑 주소 리스트
    api_key : str
        Etherscan/BSCScan API 키
    start_date : datetime
        시작 날짜
    end_date : datetime
        종료 날짜
    
    Returns:
    --------
    List[Dict] : 거래 기록 리스트
    """
    if not api_key:
        print("   ⚠️ ETHERSCAN_API_KEY가 설정되지 않아 BNB 수집을 건너뜁니다.")
        return []
    
    if not addresses:
        return []
    
    print(f"\n[BNB] {len(addresses)}개 주소의 거래 기록 수집 중...")
    
    # 블록 번호 계산 시도
    block_range = calculate_block_range_by_date('bsc', start_date, end_date, api_key)
    start_block = block_range[0] if block_range else 0
    end_block = block_range[1] if block_range else 99999999
    
    if block_range:
        print(f"   블록 범위: {start_block} ~ {end_block}")
    
    all_transactions = []
    base_url = 'https://api.bscscan.com/api'
    
    for i, address in enumerate(addresses, 1):
        try:
            params = {
                'module': 'account',
                'action': 'txlist',
                'address': address,
                'startblock': start_block,
                'endblock': end_block,
                'sort': 'desc',
                'apikey': api_key
            }
            
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '1' and data.get('result'):
                for tx in data['result']:
                    try:
                        value = int(tx.get('value', 0)) / 1e18
                        block_timestamp = datetime.fromtimestamp(int(tx.get('timeStamp', 0)), tz=timezone.utc)
                        
                        all_transactions.append({
                            'tx_hash': tx.get('hash'),
                            'block_number': int(tx.get('blockNumber', 0)),
                            'block_timestamp': block_timestamp,
                            'from_address': tx.get('from', '').lower(),
                            'to_address': tx.get('to', '').lower() if tx.get('to') else None,
                            'value': value,
                            'coin_symbol': 'BNB',
                            'chain': 'bsc',
                            'gas_used': int(tx.get('gasUsed', 0)),
                            'gas_price': int(tx.get('gasPrice', 0)),
                            'is_error': tx.get('isError') == '1',
                        })
                    except Exception as e:
                        continue
            
            if i % 10 == 0:
                print(f"   진행 중: {i}/{len(addresses)}개 주소 처리 완료...")
            
            time.sleep(0.25)  # Rate limit 방지
            
        except Exception as e:
            print(f"   ⚠️ 주소 {address[:10]}... 처리 실패: {e}")
            continue
    
    # 날짜 필터링 (블록 번호 계산 실패 시)
    if not block_range:
        all_transactions = filter_by_date_range(all_transactions, start_date, end_date)
    
    print(f"   ✅ {len(all_transactions)}건의 BNB 거래 기록 수집 완료")
    return all_transactions


def fetch_usdc_token_transactions(addresses: List[str], network: str, contract_address: str, api_key: str, start_date: datetime, end_date: datetime) -> List[Dict]:
    """
    USDC 토큰 거래 수집 (네트워크별)
    
    Parameters:
    -----------
    addresses : List[str]
        지갑 주소 리스트
    network : str
        네트워크 이름 (ethereum, bsc, polygon 등)
    contract_address : str
        USDC 컨트랙트 주소
    api_key : str
        API 키
    start_date : datetime
        시작 날짜
    end_date : datetime
        종료 날짜
    
    Returns:
    --------
    List[Dict] : 거래 기록 리스트
    """
    if not addresses:
        return []
    
    print(f"\n[USDC - {network.upper()}] {len(addresses)}개 주소의 거래 기록 수집 중...")
    
    # Solana는 별도 처리
    if network == 'solana':
        return fetch_solana_usdc_transactions(addresses, contract_address, api_key, start_date, end_date)
    
    # EVM 네트워크 처리
    if not api_key:
        print(f"   ⚠️ API 키가 설정되지 않아 {network} 네트워크 수집을 건너뜁니다.")
        return []
    
    # API 엔드포인트 설정
    api_endpoints = {
        'ethereum': 'https://api.etherscan.io/api',
        'bsc': 'https://api.bscscan.com/api',
        'polygon': 'https://api.polygonscan.com/api',
        'arbitrum': 'https://api.arbiscan.io/api',
        'optimism': 'https://api-optimistic.etherscan.io/api',
        'avalanche': 'https://api.snowtrace.io/api',
        'base': 'https://api.basescan.org/api'
    }
    
    base_url = api_endpoints.get(network)
    if not base_url:
        print(f"   ⚠️ {network} 네트워크는 아직 지원되지 않습니다.")
        return []
    
    # 블록 번호 계산 시도
    block_range = calculate_block_range_by_date(network, start_date, end_date, api_key)
    start_block = block_range[0] if block_range else 0
    end_block = block_range[1] if block_range else 99999999
    
    if block_range:
        print(f"   블록 범위: {start_block} ~ {end_block}")
    
    all_transactions = []
    
    for i, address in enumerate(addresses, 1):
        try:
            params = {
                'module': 'account',
                'action': 'tokentx',
                'contractaddress': contract_address,
                'address': address,
                'startblock': start_block,
                'endblock': end_block,
                'sort': 'desc',
                'apikey': api_key
            }
            
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '1' and data.get('result'):
                for tx in data['result']:
                    try:
                        value = int(tx.get('value', 0)) / (10 ** int(tx.get('tokenDecimal', 18)))
                        block_timestamp = datetime.fromtimestamp(int(tx.get('timeStamp', 0)), tz=timezone.utc)
                        
                        all_transactions.append({
                            'tx_hash': tx.get('hash'),
                            'block_number': int(tx.get('blockNumber', 0)),
                            'block_timestamp': block_timestamp,
                            'from_address': tx.get('from', '').lower(),
                            'to_address': tx.get('to', '').lower() if tx.get('to') else None,
                            'value': value,
                            'coin_symbol': 'USDC',
                            'chain': network,
                            'contract_address': tx.get('contractAddress', '').lower(),
                            'gas_used': int(tx.get('gasUsed', 0)),
                            'gas_price': int(tx.get('gasPrice', 0)),
                            'is_error': False,
                        })
                    except Exception as e:
                        continue
            
            if i % 10 == 0:
                print(f"   진행 중: {i}/{len(addresses)}개 주소 처리 완료...")
            
            time.sleep(0.25)  # Rate limit 방지
            
        except Exception as e:
            print(f"   ⚠️ 주소 {address[:10]}... 처리 실패: {e}")
            continue
    
    # 날짜 필터링 (블록 번호 계산 실패 시)
    if not block_range:
        all_transactions = filter_by_date_range(all_transactions, start_date, end_date)
    
    print(f"   ✅ {len(all_transactions)}건의 USDC ({network}) 거래 기록 수집 완료")
    return all_transactions


def fetch_solana_usdc_transactions(addresses: List[str], mint_address: str, api_key: str, start_date: datetime, end_date: datetime) -> List[Dict]:
    """
    Solana USDC 거래 수집 (SPL 토큰)
    
    Parameters:
    -----------
    addresses : List[str]
        지갑 주소 리스트
    mint_address : str
        USDC Mint Address
    api_key : str
        Solscan API 키
    start_date : datetime
        시작 날짜
    end_date : datetime
        종료 날짜
    
    Returns:
    --------
    List[Dict] : 거래 기록 리스트
    """
    if not api_key:
        print("   ⚠️ SOLSCAN_API_KEY가 설정되지 않아 Solana USDC 수집을 건너뜁니다.")
        return []
    
    if not addresses:
        return []
    
    print(f"\n[USDC - SOLANA] {len(addresses)}개 주소의 거래 기록 수집 중...")
    
    # 유효한 Solana 주소만 필터링
    valid_addresses = [addr for addr in addresses if is_valid_solana_address(addr)]
    invalid_count = len(addresses) - len(valid_addresses)
    
    if invalid_count > 0:
        print(f"   ⚠️ 잘못된 주소 형식 {invalid_count}개 건너뛰기 (EVM 형식 주소)")
    
    if not valid_addresses:
        print("   ⚠️ 유효한 Solana 주소가 없습니다.")
        return []
    
    all_transactions = []
    base_url = 'https://public-api.solscan.io/account/spl-token-transactions'
    
    for i, address in enumerate(valid_addresses, 1):
        try:
            params = {
                'account': address,
                'limit': 100
            }
            
            headers = {
                'token': api_key
            }
            
            response = requests.get(base_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                for tx in data:
                    try:
                        # USDC Mint Address 확인
                        if tx.get('mint') != mint_address:
                            continue
                        
                        block_time = tx.get('blockTime', 0)
                        if not block_time:
                            continue
                        
                        block_timestamp = datetime.fromtimestamp(block_time, tz=timezone.utc)
                        
                        # 날짜 필터링
                        if not (start_date <= block_timestamp <= end_date):
                            continue
                        
                        amount = float(tx.get('amount', 0)) / 1e6  # USDC는 6 decimal
                        
                        all_transactions.append({
                            'tx_hash': tx.get('txHash', ''),
                            'block_number': tx.get('slot', 0),
                            'block_timestamp': block_timestamp,
                            'from_address': tx.get('source', '').lower(),
                            'to_address': tx.get('destination', '').lower() if tx.get('destination') else None,
                            'value': amount,
                            'coin_symbol': 'USDC',
                            'chain': 'solana',
                            'contract_address': mint_address.lower(),
                            'is_error': False,
                        })
                    except Exception as e:
                        continue
            
            if i % 10 == 0:
                print(f"   진행 중: {i}/{len(addresses)}개 주소 처리 완료...")
            
            time.sleep(0.5)  # Rate limit 방지
            
        except Exception as e:
            print(f"   ⚠️ 주소 {address[:10]}... 처리 실패: {e}")
            continue
    
    print(f"   ✅ {len(all_transactions)}건의 USDC (Solana) 거래 기록 수집 완료")
    return all_transactions


def fetch_xrp_transactions(addresses: List[str], start_date: datetime, end_date: datetime) -> List[Dict]:
    """
    XRP 거래 수집 (XRP Ledger)
    XRPScan API 실패 시 XRP Ledger Public API (JSON-RPC) 사용
    
    Parameters:
    -----------
    addresses : List[str]
        지갑 주소 리스트
    start_date : datetime
        시작 날짜
    end_date : datetime
        종료 날짜
    
    Returns:
    --------
    List[Dict] : 거래 기록 리스트
    """
    if not addresses:
        return []
    
    print(f"\n[XRP] {len(addresses)}개 주소의 거래 기록 수집 중...")
    
    all_transactions = []
    
    # XRPScan API 사용 (공개 API)
    for i, address in enumerate(addresses, 1):
        try:
            # XRPScan API 시도
            url = f"{XRPSCAN_API_URL}/account/{address}/transactions"
            
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, list):
                    for tx in data:
                        try:
                            # 날짜 필터링
                            tx_date_str = tx.get('date', '')
                            if not tx_date_str:
                                continue
                            
                            # XRPScan 날짜 형식: "2025-05-15T10:30:00Z"
                            try:
                                block_timestamp = datetime.fromisoformat(tx_date_str.replace('Z', '+00:00'))
                            except:
                                continue
                            
                            if not (start_date <= block_timestamp <= end_date):
                                continue
                            
                            # XRP 거래 정보 추출
                            amount_xrp = float(tx.get('amount', 0)) / 1e6  # XRP는 6 decimal
                            
                            all_transactions.append({
                                'tx_hash': tx.get('hash', ''),
                                'block_number': tx.get('ledger_index', 0),
                                'block_timestamp': block_timestamp,
                                'from_address': tx.get('from', ''),
                                'to_address': tx.get('to', ''),
                                'value': amount_xrp,
                                'coin_symbol': 'XRP',
                                'chain': 'xrp',
                                'is_error': tx.get('result') != 'tesSUCCESS' if tx.get('result') else False,
                            })
                        except Exception as e:
                            continue
                            
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    # 403 오류 발생 시 XRP Ledger Public API 사용
                    print(f"   ⚠️ XRPScan API 403 오류, XRP Ledger Public API 사용: {address[:10]}...")
                    try:
                        # XRP Ledger Public API (JSON-RPC)
                        xrp_ledger_url = 'https://s1.ripple.com:51234'
                        payload = {
                            'method': 'account_tx',
                            'params': [{
                                'account': address,
                                'ledger_index_min': -1,
                                'ledger_index_max': -1,
                                'binary': False,
                                'limit': 100
                            }]
                        }
                        
                        response = requests.post(xrp_ledger_url, json=payload, timeout=30)
                        response.raise_for_status()
                        data = response.json()
                        
                        if data.get('result') and data['result'].get('transactions'):
                            for tx_info in data['result']['transactions']:
                                tx = tx_info.get('tx', {})
                                meta = tx_info.get('meta', {})
                                
                                try:
                                    # 날짜 필터링
                                    if 'date' in tx:
                                        # XRP Ledger 날짜는 Ripple epoch (2000-01-01) 기준 초
                                        ripple_epoch = datetime(2000, 1, 1, tzinfo=timezone.utc)
                                        block_timestamp = ripple_epoch + timedelta(seconds=int(tx['date']))
                                    else:
                                        continue
                                    
                                    if not (start_date <= block_timestamp <= end_date):
                                        continue
                                    
                                    # XRP 거래 정보 추출
                                    amount_xrp = float(tx.get('Amount', 0)) / 1e6 if isinstance(tx.get('Amount'), (int, str)) else 0
                                    
                                    all_transactions.append({
                                        'tx_hash': tx.get('hash', ''),
                                        'block_number': tx.get('ledger_index', 0),
                                        'block_timestamp': block_timestamp,
                                        'from_address': tx.get('Account', ''),
                                        'to_address': tx.get('Destination', ''),
                                        'value': amount_xrp,
                                        'coin_symbol': 'XRP',
                                        'chain': 'xrp',
                                        'is_error': meta.get('TransactionResult') != 'tesSUCCESS' if meta.get('TransactionResult') else False,
                                    })
                                except Exception as e:
                                    continue
                    except Exception as e2:
                        print(f"   ⚠️ XRP Ledger Public API도 실패: {e2}")
                else:
                    print(f"   ⚠️ XRPScan API 오류 ({e.response.status_code}): {e}")
            except Exception as e:
                print(f"   ⚠️ 주소 {address[:10]}... 처리 실패: {e}")
            
            if i % 10 == 0:
                print(f"   진행 중: {i}/{len(addresses)}개 주소 처리 완료...")
            
            time.sleep(0.5)  # Rate limit 방지
            
        except Exception as e:
            print(f"   ⚠️ 주소 {address[:10]}... 처리 실패: {e}")
            continue
    
    print(f"   ✅ {len(all_transactions)}건의 XRP 거래 기록 수집 완료")
    return all_transactions


def save_to_whale_transactions(supabase, transactions: List[Dict]) -> int:
    """
    whale_transactions 테이블에 저장
    
    Parameters:
    -----------
    supabase : Client
        Supabase 클라이언트
    transactions : List[Dict]
        거래 기록 리스트
    
    Returns:
    --------
    int : 저장된 거래 기록 수
    """
    if not transactions:
        return 0
    
    print(f"\n💾 whale_transactions 테이블에 저장 중... (총 {len(transactions)}건)")
    
    records = []
    batch_size = 100
    
    for tx in transactions:
        try:
            # whale_transactions 스키마에 맞게 변환
            record = {
                'tx_hash': tx['tx_hash'],
                'block_number': tx['block_number'],
                'block_timestamp': tx['block_timestamp'].isoformat() if isinstance(tx['block_timestamp'], datetime) else tx['block_timestamp'],
                'from_address': tx['from_address'],
                'to_address': tx.get('to_address'),
                'coin_symbol': tx['coin_symbol'],
                'chain': tx['chain'],
                'amount': str(tx['value']),
                'amount_usd': None,  # 나중에 가격 업데이트
                'gas_used': str(tx.get('gas_used', 0)),
                'gas_price': str(tx.get('gas_price', 0)),
                'transaction_status': 'SUCCESS' if not tx.get('is_error') else 'FAILED',
                'is_whale': True,
            }
            
            # contract_address 추가 (토큰 거래인 경우)
            if tx.get('contract_address'):
                record['contract_address'] = tx['contract_address']
            
            records.append(record)
            
        except Exception as e:
            print(f"   ⚠️ 거래 변환 실패: {e}")
            continue
    
    # 배치로 저장
    total_saved = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        
        try:
            response = supabase.table('whale_transactions').upsert(batch).execute()
            saved_count = len(response.data) if response.data else len(batch)
            total_saved += saved_count
            
            print(f"   ✅ 배치 {i//batch_size + 1}: {saved_count}건 저장 완료")
            
        except Exception as e:
            print(f"   ⚠️ 배치 {i//batch_size + 1} 저장 실패: {e}")
            # 개별 레코드로 재시도
            for record in batch:
                try:
                    supabase.table('whale_transactions').upsert([record]).execute()
                    total_saved += 1
                except Exception as e2:
                    print(f"      ⚠️ 개별 레코드 저장 실패 ({record.get('tx_hash', '')[:20]}...): {e2}")
    
    print(f"\n✅ 총 {total_saved}건의 거래 기록을 whale_transactions에 저장했습니다.")
    return total_saved


def main():
    """메인 함수"""
    print("=" * 70)
    print("🐋 BNB, USDC, XRP 거래 이력 수집 (2025년 7-8월)")
    print("=" * 70)
    print(f"수집 기간: {START_DATE} ~ {END_DATE}")
    print("=" * 70)
    
    try:
        # Supabase 클라이언트 생성
        supabase = get_supabase_client()
        
        # 1. whale_address에서 주소 조회
        print("\n[1단계] whale_address에서 주소 조회 중...")
        addresses_by_coin = get_whale_addresses_by_coin(supabase)
        
        if not any(addresses_by_coin.values()):
            print("❌ 수집할 주소가 없습니다.")
            return
        
        all_transactions = []
        
        # 2. BNB 거래 수집
        if addresses_by_coin.get('BNB', {}).get('bsc'):
            bnb_addresses = addresses_by_coin['BNB']['bsc']
            bnb_txs = fetch_bnb_transactions(bnb_addresses, ETHERSCAN_API_KEY, START_DATE, END_DATE)
            all_transactions.extend(bnb_txs)
        
        # 3. USDC 거래 수집 (네트워크별)
        if addresses_by_coin.get('USDC'):
            for network, network_addresses in addresses_by_coin['USDC'].items():
                if not network_addresses:
                    continue
                
                contract_address = USDC_CONTRACTS.get(network)
                if not contract_address:
                    print(f"   ⚠️ {network} 네트워크의 USDC 컨트랙트 주소를 찾을 수 없습니다.")
                    continue
                
                # API 키 결정
                api_key = ETHERSCAN_API_KEY  # 기본값
                if network == 'solana':
                    api_key = SOLSCAN_API_KEY
                elif network not in ['ethereum', 'bsc']:
                    # 다른 네트워크는 별도 API 키 필요 (현재는 ETHERSCAN_API_KEY 사용)
                    api_key = ETHERSCAN_API_KEY
                
                usdc_txs = fetch_usdc_token_transactions(
                    network_addresses, 
                    network, 
                    contract_address, 
                    api_key, 
                    START_DATE, 
                    END_DATE
                )
                all_transactions.extend(usdc_txs)
        
        # 4. XRP 거래 수집
        if addresses_by_coin.get('XRP', {}).get('xrp'):
            xrp_addresses = addresses_by_coin['XRP']['xrp']
            xrp_txs = fetch_xrp_transactions(xrp_addresses, START_DATE, END_DATE)
            all_transactions.extend(xrp_txs)
        
        # 5. whale_transactions에 저장
        if all_transactions:
            print("\n[2단계] whale_transactions 테이블에 저장 중...")
            saved_count = save_to_whale_transactions(supabase, all_transactions)
            
            # 통계 출력
            print("\n" + "=" * 70)
            print("✅ 수집 완료")
            print("=" * 70)
            print(f"📊 수집 통계:")
            print(f"   - 수집된 거래 기록: {len(all_transactions)}건")
            print(f"   - 저장된 거래 기록: {saved_count}건")
            
            # 코인별 통계
            coin_stats = {}
            for tx in all_transactions:
                coin = tx.get('coin_symbol', 'UNKNOWN')
                chain = tx.get('chain', 'unknown')
                key = f"{coin} ({chain})"
                coin_stats[key] = coin_stats.get(key, 0) + 1
            
            print("\n코인별 통계:")
            for key, count in sorted(coin_stats.items()):
                print(f"   - {key}: {count}건")
        else:
            print("\n❌ 수집된 거래 기록이 없습니다.")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

