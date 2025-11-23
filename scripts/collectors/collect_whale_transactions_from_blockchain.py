#!/usr/bin/env python3
"""
블록체인에서 고래 지갑 주소의 거래 기록을 조회하여 whale_transactions에 추가
각 체인별 블록체인 탐색기 API 사용
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client
import requests

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 블록체인 탐색기 API 설정
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')
BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY', ETHERSCAN_API_KEY)  # BSCScan도 같은 키 사용 가능

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def get_whale_addresses_by_chain(supabase, chain_type: str) -> List[str]:
    """특정 체인의 고래 지갑 주소 조회"""
    try:
        response = supabase.table('whale_address').select('address').eq('chain_type', chain_type).execute()
        addresses = [r['address'] for r in response.data if r.get('address')]
        return addresses
    except Exception as e:
        print(f"⚠️ 고래 지갑 주소 조회 실패 ({chain_type}): {e}")
        return []

def fetch_ethereum_token_transactions(address: str, contract_address: str, api_key: str) -> List[Dict]:
    """Ethereum ERC-20 토큰 거래 기록 조회 (예: LINK)"""
    if not api_key:
        return []
    
    url = "https://api.etherscan.io/api"
    params = {
        'module': 'account',
        'action': 'tokentx',  # Token Transfer Events
        'contractaddress': contract_address,
        'address': address,
        'sort': 'desc',
        'apikey': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == '1' and data.get('result'):
            transactions = []
            for tx in data['result']:
                value = int(tx.get('value', 0)) / (10 ** int(tx.get('tokenDecimal', 18)))
                
                transactions.append({
                    'tx_hash': tx.get('hash'),
                    'block_number': int(tx.get('blockNumber', 0)),
                    'block_timestamp': datetime.fromtimestamp(int(tx.get('timeStamp', 0))),
                    'from_address': tx.get('from'),
                    'to_address': tx.get('to'),
                    'contract_address': tx.get('contractAddress'),
                    'value': value,
                    'token_symbol': tx.get('tokenSymbol'),
                    'token_name': tx.get('tokenName'),
                    'gas_used': int(tx.get('gasUsed', 0)),
                    'gas_price': int(tx.get('gasPrice', 0)),
                    'is_error': False,
                })
            
            return transactions
        elif data.get('status') == '0':
            # NOTOK 응답 - "No transactions found"는 정상
            error_msg = data.get('message', '')
            if 'No transactions found' in error_msg or 'No record found' in error_msg:
                return []
            # Rate limit 오류는 대기
            if 'rate limit' in error_msg.lower():
                time.sleep(1)
                return []
            return []
        else:
            return []
    except Exception as e:
        print(f"⚠️ Etherscan Token API 호출 실패: {e}")
        return []

def fetch_ethereum_transactions(address: str, api_key: str, start_block: int = 0) -> List[Dict]:
    """Ethereum 주소의 거래 기록 조회 (Etherscan API)"""
    if not api_key:
        print("⚠️ ETHERSCAN_API_KEY가 설정되지 않았습니다.")
        return []
    
    url = "https://api.etherscan.io/api"
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': address,
        'startblock': start_block,
        'endblock': 99999999,
        'sort': 'desc',
        'apikey': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == '1' and data.get('result'):
            transactions = []
            result = data['result']
            # result가 리스트인지 확인
            if not isinstance(result, list):
                return []
            
            for tx in result:
                try:
                    # 고래 거래만 필터링 (예: $50,000 이상)
                    value_eth = int(tx.get('value', 0)) / 1e18
                    
                    transactions.append({
                        'tx_hash': tx.get('hash'),
                        'block_number': int(tx.get('blockNumber', 0)),
                        'block_timestamp': datetime.fromtimestamp(int(tx.get('timeStamp', 0))),
                        'from_address': tx.get('from'),
                        'to_address': tx.get('to'),
                        'value': value_eth,
                        'gas_used': int(tx.get('gasUsed', 0)),
                        'gas_price': int(tx.get('gasPrice', 0)),
                        'is_error': tx.get('isError') == '1',
                    })
                except Exception as e:
                    continue  # 개별 거래 파싱 오류는 넘어감
            
            return transactions
        elif data.get('status') == '0':
            # NOTOK 응답 - 에러 메시지 확인
            error_msg = data.get('message', 'Unknown error')
            # "No transactions found"는 정상 (거래가 없는 주소)
            if 'No transactions found' in error_msg or 'No record found' in error_msg or 'No transactions' in error_msg:
                return []
            # Rate limit 오류는 대기
            if 'rate limit' in error_msg.lower() or 'Max rate limit reached' in error_msg:
                time.sleep(1)  # 1초 대기
                return []
            # 다른 오류는 조용히 넘어감
            return []
        else:
            return []
    except Exception as e:
        print(f"⚠️ Etherscan API 호출 실패: {e}")
        return []

def fetch_bsc_transactions(address: str, api_key: str, start_block: int = 0) -> List[Dict]:
    """BSC 주소의 거래 기록 조회 (BSCScan API)"""
    if not api_key:
        print("⚠️ BSCSCAN_API_KEY가 설정되지 않았습니다.")
        return []
    
    url = "https://api.bscscan.com/api"
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': address,
        'startblock': start_block,
        'endblock': 99999999,
        'sort': 'desc',
        'apikey': api_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == '1' and data.get('result'):
            transactions = []
            for tx in data['result']:
                value_bnb = int(tx.get('value', 0)) / 1e18
                
                transactions.append({
                    'tx_hash': tx.get('hash'),
                    'block_number': int(tx.get('blockNumber', 0)),
                    'block_timestamp': datetime.fromtimestamp(int(tx.get('timeStamp', 0))),
                    'from_address': tx.get('from'),
                    'to_address': tx.get('to'),
                    'value': value_bnb,
                    'gas_used': int(tx.get('gasUsed', 0)),
                    'gas_price': int(tx.get('gasPrice', 0)),
                    'is_error': tx.get('isError') == '1',
                })
            
            return transactions
        else:
            print(f"⚠️ BSCScan API 오류: {data.get('message', 'Unknown error')}")
            return []
    except Exception as e:
        print(f"⚠️ BSCScan API 호출 실패: {e}")
        return []

def get_coin_symbol_by_chain(chain_type: str) -> str:
    """체인 타입에 따른 코인 심볼 반환"""
    mapping = {
        'ETH': 'ETH',
        'BSC': 'BNB',
        'BTC': 'BTC',
        'LTC': 'LTC',
        'DOGE': 'DOGE',
        'VTC': 'VTC',
        'DOT': 'DOT',
        'LINK': 'LINK',
        'SOL': 'SOL'
    }
    return mapping.get(chain_type, chain_type)

def save_to_whale_transactions(supabase, transactions: List[Dict], chain_type: str, coin_symbol: str):
    """whale_transactions 테이블에 저장"""
    if not transactions:
        return 0
    
    records = []
    for tx in transactions:
        # 가격 조회는 나중에 별도로 처리 (현재는 0)
        amount_usd = None
        
        # 토큰 거래인 경우 contract_address 사용
        contract_address = tx.get('contract_address')
        
        record = {
            'tx_hash': tx['tx_hash'],
            'block_number': str(tx['block_number']),
            'block_timestamp': tx['block_timestamp'].isoformat(),
            'from_address': tx['from_address'],
            'to_address': tx.get('to_address'),
            'coin_symbol': coin_symbol,
            'chain': chain_type.lower() if chain_type != 'LINK' else 'ethereum',
            'amount': str(tx['value']),
            'amount_usd': str(amount_usd) if amount_usd else None,
            'gas_used': str(tx.get('gas_used', 0)),
            'gas_price': str(tx.get('gas_price', 0)),
            'transaction_status': 'SUCCESS' if not tx.get('is_error') else 'FAILED',
            'is_whale': True,
        }
        
        # 컨트랙트 주소가 있으면 추가 (토큰 거래인 경우)
        if contract_address:
            record['contract_address'] = contract_address
        
        records.append(record)
    
    # 배치로 저장
    saved_count = 0
    batch_size = 50
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            response = supabase.table('whale_transactions').upsert(batch).execute()
            saved_count += len(batch)
        except Exception as e:
            print(f"⚠️ whale_transactions 저장 실패 (배치 {i//batch_size + 1}): {e}")
            # 개별 저장 시도
            for record in batch:
                try:
                    supabase.table('whale_transactions').upsert([record]).execute()
                    saved_count += 1
                except:
                    pass
    
    return saved_count

def collect_whale_transactions(supabase):
    """고래 지갑 주소의 거래 기록 수집"""
    print("=" * 70)
    print("🐋 고래 지갑 주소 거래 기록 수집 (Etherscan API)")
    print("=" * 70)
    
    if not ETHERSCAN_API_KEY:
        print("❌ ETHERSCAN_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 API 키를 추가하세요.")
        return 0
    
    # 지원하는 체인 및 토큰
    # LINK 토큰 컨트랙트 주소
    LINK_CONTRACT_ADDRESS = '0x514910771AF9Ca656af840dff83E8264EcF986CA'
    
    supported_chains = {
        'ETH': {
            'chain_name': 'ethereum',
            'coin_symbol': 'ETH',
            'fetch_native': lambda addr, key: fetch_ethereum_transactions(addr, key),
            'fetch_token': lambda addr, key: fetch_ethereum_token_transactions(addr, LINK_CONTRACT_ADDRESS, key),  # LINK 토큰도 함께 수집
            'api_key': ETHERSCAN_API_KEY,
            'api_base': 'https://api.etherscan.io/api'
        },
        'BSC': {
            'chain_name': 'bsc',
            'coin_symbol': 'BNB',
            'fetch_native': lambda addr, key: fetch_bsc_transactions(addr, key),
            'fetch_token': None,
            'api_key': BSCSCAN_API_KEY,
            'api_base': 'https://api.bscscan.com/api'
        }
    }
    
    total_saved = 0
    
    for chain_type, config in supported_chains.items():
        print(f"\n[{chain_type}] 고래 지갑 주소 거래 기록 수집 중...")
        
        # 고래 지갑 주소 조회
        addresses = get_whale_addresses_by_chain(supabase, chain_type)
        if not addresses:
            print(f"   ⚠️ {chain_type} 체인의 고래 지갑 주소를 찾을 수 없습니다.")
            continue
        
        print(f"   ✅ {len(addresses)}개의 고래 지갑 주소 발견")
        
        coin_symbol = config['coin_symbol']
        all_transactions = []
        
        # 각 주소별로 거래 기록 조회 (전체 주소 처리)
        for i, address in enumerate(addresses, 1):
            if i % 10 == 0:
                print(f"   진행 중: {i}/{len(addresses)}개 주소 처리 완료...")
            
            # 네이티브 코인 거래 조회
            if config['fetch_native']:
                try:
                    transactions = config['fetch_native'](address, config['api_key'])
                    if transactions:
                        all_transactions.extend(transactions)
                except Exception as e:
                    # 타임아웃 등은 조용히 넘어감
                    if 'timeout' not in str(e).lower():
                        pass
            
            # 토큰 거래 조회 (LINK 등)
            if config['fetch_token']:
                try:
                    token_transactions = config['fetch_token'](address, config['api_key'])
                    if token_transactions:
                        all_transactions.extend(token_transactions)
                except Exception as e:
                    pass  # 토큰 거래가 없을 수 있으므로 조용히 넘어감
            
            # API rate limit 방지 (5 calls/second)
            time.sleep(0.25)  # 초당 4회 호출로 안전하게
        
        print(f"   ✅ 총 {len(all_transactions)}건의 거래 기록 수집 완료")
        
        # whale_transactions에 저장
        if all_transactions:
            # ETH와 LINK 거래를 분리하여 저장
            eth_transactions = [tx for tx in all_transactions if not tx.get('contract_address')]
            link_transactions = [tx for tx in all_transactions if tx.get('contract_address') == LINK_CONTRACT_ADDRESS]
            
            saved_eth = 0
            saved_link = 0
            
            if eth_transactions:
                saved_eth = save_to_whale_transactions(supabase, eth_transactions, chain_type, 'ETH')
            
            if link_transactions:
                # LINK 토큰 거래는 coin_symbol을 LINK로 저장
                for tx in link_transactions:
                    tx['coin_symbol'] = 'LINK'
                saved_link = save_to_whale_transactions(supabase, link_transactions, chain_type, 'LINK')
            
            total_saved += saved_eth + saved_link
            if saved_eth > 0:
                print(f"   ✅ ETH: {saved_eth}건 저장 완료")
            if saved_link > 0:
                print(f"   ✅ LINK: {saved_link}건 저장 완료")
    
    print(f"\n✅ 총 {total_saved}건의 거래 기록을 whale_transactions에 저장했습니다.")
    return total_saved

def main():
    """메인 함수"""
    supabase = get_supabase_client()
    
    # 고래 지갑 주소의 거래 기록 수집
    collect_whale_transactions(supabase)
    
    print("\n" + "=" * 70)
    print("✅ 작업 완료")
    print("=" * 70)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

