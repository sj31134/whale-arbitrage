#!/usr/bin/env python3
"""
Internal Transactions 수집 스크립트
whale_address 테이블의 EVM 네트워크 주소에 대해 2025년 5-6월 Internal Transactions 수집
"""

import os
import sys
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
from supabase import create_client

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 환경변수 로드
load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 날짜 범위 설정 (7-8월로 확장)
START_DATE = datetime(2025, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
END_DATE = datetime(2025, 8, 31, 23, 59, 59, tzinfo=timezone.utc)

# API 키 설정
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')
BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY', os.getenv('ETHERSCAN_API_KEY', ''))
POLYGONSCAN_API_KEY = os.getenv('POLYGONSCAN_API_KEY', '')

# Chain ID 매핑 (Etherscan V2 API)
CHAIN_IDS = {
    'ethereum': 1,
    'bsc': 56,
    'polygon': 137
}

# API Base URL
API_BASE_URLS = {
    'ethereum': 'https://api.etherscan.io/api',
    'bsc': 'https://api.bscscan.com/api',
    'polygon': 'https://api.polygonscan.com/api'
}

# Etherscan V2 API Base URL
API_V2_BASE_URL = 'https://api.etherscan.io/v2/api'


def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("SUPABASE_URL과 SUPABASE_SERVICE_ROLE_KEY가 설정되어야 합니다.")
    
    return create_client(supabase_url, supabase_key)


def is_valid_evm_address(address: str) -> bool:
    """EVM 주소 형식 검증"""
    if not address:
        return False
    address = address.strip()
    if address.startswith('0x') and len(address) == 42:
        try:
            int(address[2:], 16)
            return True
        except ValueError:
            return False
    return False


def get_whale_addresses_for_internal_tx(supabase) -> Dict[str, List[str]]:
    """
    whale_address 테이블에서 EVM 네트워크 주소만 조회
    
    Returns:
    --------
    Dict[str, List[str]]: {
        'ethereum': [addresses],
        'bsc': [addresses],
        'polygon': [addresses]
    }
    """
    try:
        # EVM 네트워크 체인 타입 매핑
        chain_mapping = {
            'ETH': 'ethereum',
            'BSC': 'bsc',
            'POLYGON': 'polygon'
        }
        
        result = {
            'ethereum': [],
            'bsc': [],
            'polygon': []
        }
        
        # 각 체인 타입별로 주소 조회
        for chain_type, network in chain_mapping.items():
            response = supabase.table('whale_address').select('address').eq('chain_type', chain_type).execute()
            addresses = [
                row['address'].strip().lower() 
                for row in response.data 
                if row.get('address') and is_valid_evm_address(row['address'])
            ]
            result[network] = addresses
            print(f"   - {network}: {len(addresses)}개 주소")
        
        return result
        
    except Exception as e:
        print(f"⚠️ whale_address 조회 실패: {e}")
        return {'ethereum': [], 'bsc': [], 'polygon': []}


def calculate_block_range_by_date(chain: str, start_date: datetime, end_date: datetime, api_key: str) -> Optional[Tuple[int, int]]:
    """날짜를 블록 번호로 변환"""
    if not api_key:
        return None
    
    try:
        base_url = API_BASE_URLS.get(chain)
        if not base_url:
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
        
        start_response = requests.get(base_url, params=start_params, timeout=30)
        start_response.raise_for_status()
        start_data = start_response.json()
        
        if start_data.get('status') == '1' and start_data.get('result'):
            start_block = int(start_data['result'])
        else:
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
        
        end_response = requests.get(base_url, params=end_params, timeout=30)
        end_response.raise_for_status()
        end_data = end_response.json()
        
        if end_data.get('status') == '1' and end_data.get('result'):
            end_block = int(end_data['result'])
            return (start_block, end_block)
        
        return None
        
    except Exception as e:
        print(f"   ⚠️ {chain} 블록 번호 계산 실패: {e}")
        return None


def filter_by_date_range(transactions: List[Dict], start_date: datetime, end_date: datetime) -> List[Dict]:
    """거래 기록을 날짜 범위로 필터링"""
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


def fetch_internal_transactions_etherscan(addresses: List[str], start_date: datetime, end_date: datetime, api_key: str) -> List[Dict]:
    """Ethereum Internal Transactions 수집"""
    if not api_key:
        print("   ⚠️ ETHERSCAN_API_KEY가 설정되지 않아 Ethereum 내부 거래 수집을 건너뜁니다.")
        return []
    
    if not addresses:
        return []
    
    print(f"\n[Ethereum Internal Transactions] {len(addresses)}개 주소의 내부 거래 수집 중...")
    
    # 블록 번호 계산
    block_range = calculate_block_range_by_date('ethereum', start_date, end_date, api_key)
    start_block = block_range[0] if block_range else 0
    end_block = block_range[1] if block_range else 99999999
    
    all_transactions = []
    chain_id = CHAIN_IDS['ethereum']
    
    for i, address in enumerate(addresses, 1):
        try:
            # Etherscan V2 API 사용
            params = {
                'chainid': chain_id,
                'module': 'account',
                'action': 'txlistinternal',
                'address': address,
                'startblock': start_block,
                'endblock': end_block,
                'page': 1,
                'offset': 10000,
                'sort': 'desc',
                'apikey': api_key
            }
            
            response = requests.get(API_V2_BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '1':
                transactions = data.get('result', [])
                if not isinstance(transactions, list):
                    transactions = []
                
                for tx in transactions:
                    try:
                        # type=call이고 isError=0인 거래만 필터링
                        tx_type = str(tx.get('type', '')).lower()
                        is_error = str(tx.get('isError', '1'))
                        
                        if tx_type != 'call' or is_error != '0':
                            continue
                        
                        # Wei를 ETH로 변환
                        value_eth = float(tx.get('value', 0)) / 10**18
                        
                        # 타임스탬프 처리
                        timestamp = int(tx.get('timeStamp', 0))
                        block_timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        
                        # 날짜 필터링 (블록 번호 계산 실패 시)
                        if not block_range:
                            if not (start_date <= block_timestamp <= end_date):
                                continue
                        
                        all_transactions.append({
                            'tx_hash': str(tx.get('hash', '')),
                            'trace_id': str(tx.get('traceId', '')),
                            'block_number': int(tx.get('blockNumber', 0)),
                            'block_timestamp': block_timestamp.isoformat(),
                            'from_address': str(tx.get('from', '')).lower(),
                            'to_address': str(tx.get('to', '')).lower() if tx.get('to') else None,
                            'contract_address': str(tx.get('contractAddress', '')).lower() if tx.get('contractAddress') else None,
                            'value_eth': value_eth,
                            'value_usd': None,  # 나중에 계산 가능
                            'transaction_type': tx_type.upper(),
                            'is_error': False,
                            'input_data': str(tx.get('input', '')),
                            'gas': int(tx.get('gas', 0)) if tx.get('gas') else None,
                            'gas_used': int(tx.get('gasUsed', 0)) if tx.get('gasUsed') else None,
                            'chain': 'ethereum'
                        })
                    except Exception as e:
                        continue
            
            if i % 10 == 0:
                print(f"   진행 중: {i}/{len(addresses)}개 주소 처리 완료...")
            
            time.sleep(0.25)  # Rate limit 방지
            
        except Exception as e:
            print(f"   ⚠️ 주소 {address[:10]}... 처리 실패: {e}")
            continue
    
    print(f"   ✅ {len(all_transactions)}건의 Ethereum 내부 거래 기록 수집 완료")
    return all_transactions


def fetch_internal_transactions_bscscan(addresses: List[str], start_date: datetime, end_date: datetime, api_key: str) -> List[Dict]:
    """BSC Internal Transactions 수집"""
    if not api_key:
        print("   ⚠️ BSCSCAN_API_KEY가 설정되지 않아 BSC 내부 거래 수집을 건너뜁니다.")
        return []
    
    if not addresses:
        return []
    
    print(f"\n[BSC Internal Transactions] {len(addresses)}개 주소의 내부 거래 수집 중...")
    
    # 블록 번호 계산
    block_range = calculate_block_range_by_date('bsc', start_date, end_date, api_key)
    start_block = block_range[0] if block_range else 0
    end_block = block_range[1] if block_range else 99999999
    
    all_transactions = []
    chain_id = CHAIN_IDS['bsc']
    base_url = API_BASE_URLS['bsc']
    
    for i, address in enumerate(addresses, 1):
        try:
            # BSCScan API 사용 (V2 API 지원)
            params = {
                'chainid': chain_id,
                'module': 'account',
                'action': 'txlistinternal',
                'address': address,
                'startblock': start_block,
                'endblock': end_block,
                'page': 1,
                'offset': 10000,
                'sort': 'desc',
                'apikey': api_key
            }
            
            # BSCScan은 V2 API를 지원하지 않을 수 있으므로 V1 API 사용
            params_v1 = {k: v for k, v in params.items() if k != 'chainid'}
            response = requests.get(base_url, params=params_v1, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '1':
                transactions = data.get('result', [])
                if not isinstance(transactions, list):
                    transactions = []
                
                for tx in transactions:
                    try:
                        # type=call이고 isError=0인 거래만 필터링
                        tx_type = str(tx.get('type', '')).lower()
                        is_error = str(tx.get('isError', '1'))
                        
                        if tx_type != 'call' or is_error != '0':
                            continue
                        
                        # Wei를 BNB로 변환
                        value_eth = float(tx.get('value', 0)) / 10**18
                        
                        # 타임스탬프 처리
                        timestamp = int(tx.get('timeStamp', 0))
                        block_timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        
                        # 날짜 필터링 (블록 번호 계산 실패 시)
                        if not block_range:
                            if not (start_date <= block_timestamp <= end_date):
                                continue
                        
                        all_transactions.append({
                            'tx_hash': str(tx.get('hash', '')),
                            'trace_id': str(tx.get('traceId', '')),
                            'block_number': int(tx.get('blockNumber', 0)),
                            'block_timestamp': block_timestamp.isoformat(),
                            'from_address': str(tx.get('from', '')).lower(),
                            'to_address': str(tx.get('to', '')).lower() if tx.get('to') else None,
                            'contract_address': str(tx.get('contractAddress', '')).lower() if tx.get('contractAddress') else None,
                            'value_eth': value_eth,
                            'value_usd': None,
                            'transaction_type': tx_type.upper(),
                            'is_error': False,
                            'input_data': str(tx.get('input', '')),
                            'gas': int(tx.get('gas', 0)) if tx.get('gas') else None,
                            'gas_used': int(tx.get('gasUsed', 0)) if tx.get('gasUsed') else None,
                            'chain': 'bsc'
                        })
                    except Exception as e:
                        continue
            
            if i % 10 == 0:
                print(f"   진행 중: {i}/{len(addresses)}개 주소 처리 완료...")
            
            time.sleep(0.25)  # Rate limit 방지
            
        except Exception as e:
            print(f"   ⚠️ 주소 {address[:10]}... 처리 실패: {e}")
            continue
    
    print(f"   ✅ {len(all_transactions)}건의 BSC 내부 거래 기록 수집 완료")
    return all_transactions


def fetch_internal_transactions_polygonscan(addresses: List[str], start_date: datetime, end_date: datetime, api_key: str) -> List[Dict]:
    """Polygon Internal Transactions 수집"""
    if not api_key:
        print("   ⚠️ POLYGONSCAN_API_KEY가 설정되지 않아 Polygon 내부 거래 수집을 건너뜁니다.")
        return []
    
    if not addresses:
        return []
    
    print(f"\n[Polygon Internal Transactions] {len(addresses)}개 주소의 내부 거래 수집 중...")
    
    # 블록 번호 계산
    block_range = calculate_block_range_by_date('polygon', start_date, end_date, api_key)
    start_block = block_range[0] if block_range else 0
    end_block = block_range[1] if block_range else 99999999
    
    all_transactions = []
    base_url = API_BASE_URLS['polygon']
    
    for i, address in enumerate(addresses, 1):
        try:
            # PolygonScan API 사용
            params = {
                'module': 'account',
                'action': 'txlistinternal',
                'address': address,
                'startblock': start_block,
                'endblock': end_block,
                'page': 1,
                'offset': 10000,
                'sort': 'desc',
                'apikey': api_key
            }
            
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') == '1':
                transactions = data.get('result', [])
                if not isinstance(transactions, list):
                    transactions = []
                
                for tx in transactions:
                    try:
                        # type=call이고 isError=0인 거래만 필터링
                        tx_type = str(tx.get('type', '')).lower()
                        is_error = str(tx.get('isError', '1'))
                        
                        if tx_type != 'call' or is_error != '0':
                            continue
                        
                        # Wei를 MATIC으로 변환
                        value_eth = float(tx.get('value', 0)) / 10**18
                        
                        # 타임스탬프 처리
                        timestamp = int(tx.get('timeStamp', 0))
                        block_timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        
                        # 날짜 필터링 (블록 번호 계산 실패 시)
                        if not block_range:
                            if not (start_date <= block_timestamp <= end_date):
                                continue
                        
                        all_transactions.append({
                            'tx_hash': str(tx.get('hash', '')),
                            'trace_id': str(tx.get('traceId', '')),
                            'block_number': int(tx.get('blockNumber', 0)),
                            'block_timestamp': block_timestamp.isoformat(),
                            'from_address': str(tx.get('from', '')).lower(),
                            'to_address': str(tx.get('to', '')).lower() if tx.get('to') else None,
                            'contract_address': str(tx.get('contractAddress', '')).lower() if tx.get('contractAddress') else None,
                            'value_eth': value_eth,
                            'value_usd': None,
                            'transaction_type': tx_type.upper(),
                            'is_error': False,
                            'input_data': str(tx.get('input', '')),
                            'gas': int(tx.get('gas', 0)) if tx.get('gas') else None,
                            'gas_used': int(tx.get('gasUsed', 0)) if tx.get('gasUsed') else None,
                            'chain': 'polygon'
                        })
                    except Exception as e:
                        continue
            
            if i % 10 == 0:
                print(f"   진행 중: {i}/{len(addresses)}개 주소 처리 완료...")
            
            time.sleep(0.25)  # Rate limit 방지
            
        except Exception as e:
            print(f"   ⚠️ 주소 {address[:10]}... 처리 실패: {e}")
            continue
    
    print(f"   ✅ {len(all_transactions)}건의 Polygon 내부 거래 기록 수집 완료")
    return all_transactions


def save_to_internal_transactions(supabase, transactions: List[Dict]) -> int:
    """internal_transactions 테이블에 저장"""
    if not transactions:
        return 0
    
    # 중복 제거 (tx_hash + trace_id 조합 기준)
    unique_keys = set()
    unique_transactions = []
    
    for tx in transactions:
        key = f"{tx['tx_hash']}_{tx.get('trace_id', '')}"
        if key not in unique_keys:
            unique_keys.add(key)
            unique_transactions.append(tx)
    
    if not unique_transactions:
        return 0
    
    try:
        print(f"\n💾 {len(unique_transactions)}건의 내부 거래를 internal_transactions 테이블에 저장 중...")
        
        # 배치로 저장 (1000건씩)
        batch_size = 1000
        total_saved = 0
        
        for i in range(0, len(unique_transactions), batch_size):
            batch = unique_transactions[i:i + batch_size]
            
            try:
                response = supabase.table('internal_transactions').upsert(batch).execute()
                saved_count = len(batch)
                total_saved += saved_count
                print(f"   ✅ {saved_count}건 저장 완료 ({i+1}~{min(i+batch_size, len(unique_transactions))}/{len(unique_transactions)})")
            except Exception as e:
                print(f"   ⚠️ 배치 저장 실패: {e}")
                continue
        
        print(f"\n✅ 총 {total_saved}건의 내부 거래 저장 완료")
        return total_saved
        
    except Exception as e:
        print(f"❌ 내부 거래 저장 실패: {e}")
        return 0


def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("🔍 Internal Transactions 수집 (2025년 7-8월)")
    print("=" * 70)
    print(f"수집 기간: {START_DATE} ~ {END_DATE}")
    print("=" * 70)
    
    try:
        supabase = get_supabase_client()
        
        print("\n[1단계] whale_address에서 EVM 네트워크 주소 조회 중...")
        whale_addresses = get_whale_addresses_for_internal_tx(supabase)
        
        total_addresses = sum(len(addrs) for addrs in whale_addresses.values())
        if total_addresses == 0:
            print("⚠️ 조회된 주소가 없습니다.")
            return
        
        print(f"\n✅ 총 {total_addresses}개 주소 조회 완료")
        
        print("\n[2단계] Internal Transactions 수집 중...")
        all_internal_transactions = []
        
        # Ethereum
        if whale_addresses['ethereum']:
            eth_txs = fetch_internal_transactions_etherscan(
                whale_addresses['ethereum'], 
                START_DATE, 
                END_DATE, 
                ETHERSCAN_API_KEY
            )
            all_internal_transactions.extend(eth_txs)
        
        # BSC
        if whale_addresses['bsc']:
            bsc_txs = fetch_internal_transactions_bscscan(
                whale_addresses['bsc'], 
                START_DATE, 
                END_DATE, 
                BSCSCAN_API_KEY
            )
            all_internal_transactions.extend(bsc_txs)
        
        # Polygon
        if whale_addresses['polygon']:
            polygon_txs = fetch_internal_transactions_polygonscan(
                whale_addresses['polygon'], 
                START_DATE, 
                END_DATE, 
                POLYGONSCAN_API_KEY
            )
            all_internal_transactions.extend(polygon_txs)
        
        print(f"\n✅ 총 {len(all_internal_transactions)}건의 Internal Transactions 수집 완료")
        
        print("\n[3단계] internal_transactions 테이블에 저장 중...")
        total_saved = save_to_internal_transactions(supabase, all_internal_transactions)
        
        print("\n" + "=" * 70)
        print("✅ 수집 완료")
        print("=" * 70)
        print(f"📊 수집 통계:")
        print(f"   - 수집된 내부 거래: {len(all_internal_transactions)}건")
        print(f"   - 저장된 내부 거래: {total_saved}건")
        
        print("\n네트워크별 통계:")
        chain_stats = {}
        for tx in all_internal_transactions:
            chain = tx.get('chain', 'unknown')
            chain_stats[chain] = chain_stats.get(chain, 0) + 1
        
        for chain, count in chain_stats.items():
            print(f"   - {chain}: {count}건")
        
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

