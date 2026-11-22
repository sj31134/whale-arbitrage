#!/usr/bin/env python3
"""
Internal Transactions 수집 스크립트
2025년 1월 1일 ~ 오늘까지의 internal transactions 수집
"""

import os
import sys
import time
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

START_DATE = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
END_DATE = datetime.now(timezone.utc)

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def get_whale_addresses(supabase, chain='ethereum'):
    """고래 주소 조회"""
    try:
        # ETH 주소
        if chain == 'ethereum':
            response = supabase.table('whale_address')\
                .select('address, name_tag')\
                .eq('chain_type', 'ETH')\
                .execute()
        # BSC 주소
        elif chain == 'bsc':
            response = supabase.table('whale_address')\
                .select('address, name_tag')\
                .eq('chain_type', 'BSC')\
                .execute()
        else:
            return []
        
        addresses = []
        for row in response.data:
            addresses.append({
                'address': row['address'],
                'name_tag': row.get('name_tag', 'Unknown')
            })
        
        return addresses
        
    except Exception as e:
        print(f"❌ 주소 조회 실패: {e}")
        return []

def fetch_internal_transactions(address: str, api_key: str, chain='ethereum', 
                                start_block=0, end_block=99999999) -> List[Dict]:
    """Etherscan/BSCScan API를 통해 internal transactions 조회 (V2 API 사용)"""
    
    # API 엔드포인트 - V2 사용
    if chain == 'ethereum':
        base_url = 'https://api.etherscan.io/v2/api'
    elif chain == 'bsc':
        base_url = 'https://api.bscscan.com/api'  # BSC는 여전히 V1 사용
    else:
        print(f"⚠️ 지원하지 않는 체인: {chain}")
        return []
    
    try:
        # V2 API 파라미터
        if chain == 'ethereum':
            params = {
                'chainid': '1',  # Ethereum mainnet
                'module': 'account',
                'action': 'txlistinternal',
                'address': address,
                'startblock': start_block,
                'endblock': end_block,
                'page': 1,
                'offset': 10000,  # 최대 10000개
                'sort': 'asc',
                'apikey': api_key
            }
        else:  # BSC
            params = {
                'module': 'account',
                'action': 'txlistinternal',
                'address': address,
                'startblock': start_block,
                'endblock': end_block,
                'page': 1,
                'offset': 10000,
                'sort': 'asc',
                'apikey': api_key
            }
        
        response = requests.get(base_url, params=params, timeout=30)
        
        if response.status_code != 200:
            print(f"  ⚠️ API 오류 (HTTP {response.status_code})")
            return []
        
        data = response.json()
        
        # V2 응답 구조 확인
        if data.get('status') != '1':
            message = data.get('message', 'Unknown error')
            if message not in ['No transactions found', 'No records found']:
                print(f"  ⚠️ API 응답 오류: {message}")
            return []
        
        return data.get('result', [])
        
    except Exception as e:
        print(f"  ❌ 조회 오류: {e}")
        return []

def parse_internal_transaction(tx: Dict, chain='ethereum') -> Dict:
    """Internal transaction 데이터 파싱"""
    try:
        # 타임스탬프 변환
        timestamp = datetime.fromtimestamp(int(tx['timeStamp']), tz=timezone.utc)
        
        # Wei를 ETH/BNB로 변환
        value = int(tx.get('value', '0'))
        if chain == 'ethereum':
            value_native = value / 1e18  # Wei -> ETH
        elif chain == 'bsc':
            value_native = value / 1e18  # Wei -> BNB
        else:
            value_native = 0
        
        parsed = {
            'tx_hash': tx['hash'],
            'trace_id': tx.get('traceId', ''),
            'block_number': int(tx['blockNumber']),
            'block_timestamp': timestamp.isoformat(),
            'from_address': tx['from'].lower(),
            'to_address': tx.get('to', '').lower() if tx.get('to') else None,
            'contract_address': tx.get('contractAddress', '').lower() if tx.get('contractAddress') else None,
            'chain': chain,
            'value_eth': value_native,
            'transaction_type': tx.get('type', 'call').upper(),
            'is_error': tx.get('isError', '0') != '0',
            'input_data': tx.get('input', ''),
            'gas': int(tx.get('gas', 0)) if tx.get('gas') else None,
            'gas_used': int(tx.get('gasUsed', 0)) if tx.get('gasUsed') else None
        }
        
        return parsed
        
    except Exception as e:
        print(f"  ⚠️ 파싱 오류: {e}")
        return None

def save_internal_transactions(supabase, transactions: List[Dict]) -> int:
    """Internal transactions를 DB에 저장"""
    if not transactions:
        return 0
    
    saved_count = 0
    batch_size = 50
    
    for i in range(0, len(transactions), batch_size):
        batch = transactions[i:i+batch_size]
        
        try:
            # 중복 체크 후 삽입
            for tx in batch:
                try:
                    # 이미 존재하는지 확인
                    existing = supabase.table('internal_transactions')\
                        .select('tx_hash')\
                        .eq('tx_hash', tx['tx_hash'])\
                        .eq('trace_id', tx['trace_id'])\
                        .limit(1)\
                        .execute()
                    
                    if not existing.data:
                        supabase.table('internal_transactions').insert(tx).execute()
                        saved_count += 1
                except Exception as e:
                    # 개별 오류는 무시하고 계속 진행
                    pass
            
            # Rate limit
            time.sleep(0.2)
            
        except Exception as e:
            print(f"  ⚠️ 배치 저장 오류: {e}")
    
    return saved_count

def collect_internal_transactions_for_address(supabase, address: str, name_tag: str, 
                                              api_key: str, chain='ethereum') -> int:
    """특정 주소의 internal transactions 수집"""
    print(f"\n  📊 Internal Transactions 수집: {name_tag} ({address[:10]}...)")
    
    # 해당 주소의 최신 block_number 확인
    try:
        response = supabase.table('internal_transactions')\
            .select('block_number')\
            .eq('from_address', address.lower())\
            .eq('chain', chain)\
            .order('block_number', desc=True)\
            .limit(1)\
            .execute()
        
        if response.data:
            start_block = response.data[0]['block_number'] + 1
            print(f"    마지막 블록: {response.data[0]['block_number']}, {start_block}부터 수집")
        else:
            # 2025년 1월 1일 기준 블록 번호
            if chain == 'ethereum':
                start_block = 18900000  # 대략 2024년 1월 기준
            elif chain == 'bsc':
                start_block = 34000000  # 대략 2024년 1월 기준
            else:
                start_block = 0
            print(f"    처음 수집, {start_block}부터 시작")
    except:
        start_block = 0
    
    # Internal transactions 조회
    txs = fetch_internal_transactions(address, api_key, chain, start_block)
    
    if not txs:
        print(f"    ⚠️ 수집된 거래 없음")
        return 0
    
    print(f"    ✅ {len(txs)}건 조회")
    
    # 파싱
    parsed_txs = []
    for tx in txs:
        parsed = parse_internal_transaction(tx, chain)
        if parsed:
            # 2025년 1월 1일 이후만
            tx_time = datetime.fromisoformat(parsed['block_timestamp'])
            if tx_time >= START_DATE and tx_time <= END_DATE:
                parsed_txs.append(parsed)
    
    if not parsed_txs:
        print(f"    ⚠️ 2025년 데이터 없음")
        return 0
    
    print(f"    📅 2025년 데이터: {len(parsed_txs)}건")
    
    # 저장
    saved = save_internal_transactions(supabase, parsed_txs)
    print(f"    💾 {saved}건 저장 완료")
    
    return saved

def main():
    """메인 함수"""
    print("=" * 80)
    print("🔄 Internal Transactions 수집")
    print("=" * 80)
    print(f"\n수집 기간: {START_DATE.strftime('%Y-%m-%d')} ~ {END_DATE.strftime('%Y-%m-%d')}")
    
    try:
        supabase = get_supabase_client()
        
        # API 키
        etherscan_key = os.getenv('ETHERSCAN_API_KEY')
        bscscan_key = os.getenv('BSCSCAN_API_KEY', etherscan_key)  # BSC는 같은 키 사용 가능
        
        if not etherscan_key:
            print("❌ ETHERSCAN_API_KEY가 설정되지 않았습니다")
            return
        
        total_saved = 0
        
        # 1. Ethereum Internal Transactions
        print("\n" + "=" * 80)
        print("🔷 Ethereum Internal Transactions")
        print("=" * 80)
        
        eth_addresses = get_whale_addresses(supabase, 'ethereum')
        print(f"\nETH 고래 주소: {len(eth_addresses)}개")
        
        for idx, addr_info in enumerate(eth_addresses, 1):
            print(f"\n[{idx}/{len(eth_addresses)}]", end='')
            saved = collect_internal_transactions_for_address(
                supabase,
                addr_info['address'],
                addr_info['name_tag'],
                etherscan_key,
                'ethereum'
            )
            total_saved += saved
            
            # Rate limit
            time.sleep(0.5)
        
        # 2. BSC Internal Transactions
        if bscscan_key:
            print("\n" + "=" * 80)
            print("🟡 BSC Internal Transactions")
            print("=" * 80)
            
            bsc_addresses = get_whale_addresses(supabase, 'bsc')
            print(f"\nBSC 고래 주소: {len(bsc_addresses)}개")
            
            for idx, addr_info in enumerate(bsc_addresses, 1):
                print(f"\n[{idx}/{len(bsc_addresses)}]", end='')
                saved = collect_internal_transactions_for_address(
                    supabase,
                    addr_info['address'],
                    addr_info['name_tag'],
                    bscscan_key,
                    'bsc'
                )
                total_saved += saved
                
                # Rate limit
                time.sleep(0.5)
        
        print("\n" + "=" * 80)
        print("✅ 수집 완료")
        print("=" * 80)
        print(f"\n총 저장: {total_saved:,}건")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

