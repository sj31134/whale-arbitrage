#!/usr/bin/env python3
"""
모든 블록체인에서 고래 지갑 주소의 거래 기록을 수집하여 whale_transactions에 저장
1. 모든 블록체인 API에서 거래 기록 수집
2. whale_address 테이블의 고래 지갑 주소로 필터링
3. 필터링된 거래 기록을 whale_transactions에 저장
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set
from dotenv import load_dotenv
from supabase import create_client

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'src'))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 멀티체인 수집기 import
from src.collectors.multi_chain_collector import (
    fetch_etherscan_transactions,
    fetch_sochain_transactions,
    fetch_subscan_transactions,
    fetch_solscan_transactions,
    fetch_vtc_transactions
)

# API 키 로드
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')
SOCHAIN_API_KEY = os.getenv('SOCHAIN_API_KEY', '')
SUBSCAN_API_KEY = os.getenv('SUBSCAN_API_KEY', '')
SOLSCAN_API_KEY = os.getenv('SOLSCAN_API_KEY', '')


def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)


def get_all_whale_addresses(supabase) -> Dict[str, Set[str]]:
    """
    whale_address 테이블에서 체인별 고래 지갑 주소 조회
    
    Returns:
    --------
    Dict[str, Set[str]] : 체인별 고래 지갑 주소 Set (빠른 조회용)
    """
    try:
        response = supabase.table('whale_address').select('chain_type, address').execute()
        
        whale_addresses_by_chain = {}
        
        for row in response.data:
            chain_type = row.get('chain_type', '').upper()
            address = row.get('address', '').strip()
            
            if not address:
                continue
            
            # 체인 타입을 API에 맞게 매핑
            chain_mapping = {
                'ETH': 'ethereum',
                'BSC': 'bsc',
                'BTC': 'btc',
                'LTC': 'ltc',
                'DOGE': 'doge',
                'VTC': 'vtc',
                'DOT': 'polkadot',
                'LINK': 'ethereum',  # LINK는 Ethereum 체인
                'SOL': 'solana'
            }
            
            api_chain = chain_mapping.get(chain_type, chain_type.lower())
            
            if api_chain not in whale_addresses_by_chain:
                whale_addresses_by_chain[api_chain] = set()
            
            whale_addresses_by_chain[api_chain].add(address.lower())
        
        # LINK 주소도 ethereum에 추가 (LINK는 Ethereum 체인에서 처리)
        if 'LINK' in [row.get('chain_type', '').upper() for row in response.data]:
            link_addresses = set()
            for row in response.data:
                if row.get('chain_type', '').upper() == 'LINK':
                    address = row.get('address', '').strip()
                    if address:
                        link_addresses.add(address.lower())
            
            if link_addresses:
                if 'ethereum' not in whale_addresses_by_chain:
                    whale_addresses_by_chain['ethereum'] = set()
                whale_addresses_by_chain['ethereum'].update(link_addresses)
        
        print(f"✅ 체인별 고래 지갑 주소 조회 완료:")
        for chain, addresses in whale_addresses_by_chain.items():
            print(f"   - {chain}: {len(addresses)}개")
        
        return whale_addresses_by_chain
    
    except Exception as e:
        print(f"⚠️ 고래 지갑 주소 조회 실패: {e}")
        return {}


def collect_all_transactions(supabase, whale_addresses: Dict[str, Set[str]]) -> List[Dict]:
    """
    모든 블록체인에서 거래 기록 수집
    
    Parameters:
    -----------
    supabase : Client
        Supabase 클라이언트
    whale_addresses : Dict[str, Set[str]]
        체인별 고래 지갑 주소 Set
    
    Returns:
    --------
    List[Dict] : 모든 거래 기록 리스트
    """
    all_transactions = []
    
    print("\n" + "=" * 70)
    print("📊 블록체인별 거래 기록 수집 시작")
    print("=" * 70)
    
    # 1. Etherscan API (ETH, BNB, LINK)
    if ETHERSCAN_API_KEY:
        # Ethereum
        if 'ethereum' in whale_addresses:
            addresses = list(whale_addresses['ethereum'])
            print(f"\n[Ethereum] {len(addresses)}개 주소의 거래 기록 수집 중...")
            eth_txs = fetch_etherscan_transactions(addresses, 'ethereum', ETHERSCAN_API_KEY)
            all_transactions.extend(eth_txs)
            print(f"   ✅ {len(eth_txs)}건 수집 완료")
        
        # BSC
        if 'bsc' in whale_addresses:
            addresses = list(whale_addresses['bsc'])
            print(f"\n[BSC] {len(addresses)}개 주소의 거래 기록 수집 중...")
            bsc_txs = fetch_etherscan_transactions(addresses, 'bsc', ETHERSCAN_API_KEY)
            all_transactions.extend(bsc_txs)
            print(f"   ✅ {len(bsc_txs)}건 수집 완료")
    else:
        print("\n⚠️ ETHERSCAN_API_KEY가 설정되지 않아 ETH, BNB, LINK 수집을 건너뜁니다.")
    
    # 2. SoChain API (BTC, LTC, DOGE)
    if SOCHAIN_API_KEY:
        for coin in ['BTC', 'LTC', 'DOGE']:
            chain_key = coin.lower()
            if chain_key in whale_addresses:
                addresses = list(whale_addresses[chain_key])
                print(f"\n[{coin}] {len(addresses)}개 주소의 거래 기록 수집 중...")
                coin_txs = fetch_sochain_transactions(addresses, coin, SOCHAIN_API_KEY)
                all_transactions.extend(coin_txs)
                print(f"   ✅ {len(coin_txs)}건 수집 완료")
    else:
        print("\n⚠️ SOCHAIN_API_KEY가 설정되지 않아 BTC, LTC, DOGE 수집을 건너뜁니다.")
    
    # 3. Subscan API (DOT)
    if SUBSCAN_API_KEY:
        if 'polkadot' in whale_addresses:
            addresses = list(whale_addresses['polkadot'])
            print(f"\n[DOT] {len(addresses)}개 주소의 거래 기록 수집 중...")
            dot_txs = fetch_subscan_transactions(addresses, SUBSCAN_API_KEY)
            all_transactions.extend(dot_txs)
            print(f"   ✅ {len(dot_txs)}건 수집 완료")
    else:
        print("\n⚠️ SUBSCAN_API_KEY가 설정되지 않아 DOT 수집을 건너뜁니다.")
    
    # 4. Solscan API (SOL)
    if SOLSCAN_API_KEY:
        if 'solana' in whale_addresses:
            addresses = list(whale_addresses['solana'])
            print(f"\n[SOL] {len(addresses)}개 주소의 거래 기록 수집 중...")
            sol_txs = fetch_solscan_transactions(addresses, SOLSCAN_API_KEY)
            all_transactions.extend(sol_txs)
            print(f"   ✅ {len(sol_txs)}건 수집 완료")
    else:
        print("\n⚠️ SOLSCAN_API_KEY가 설정되지 않아 SOL 수집을 건너뜁니다.")
    
    # 5. VTC (공개 API)
    if 'vtc' in whale_addresses:
        addresses = list(whale_addresses['vtc'])
        print(f"\n[VTC] {len(addresses)}개 주소의 거래 기록 수집 중...")
        vtc_txs = fetch_vtc_transactions(addresses)
        all_transactions.extend(vtc_txs)
        print(f"   ✅ {len(vtc_txs)}건 수집 완료")
    
    print(f"\n✅ 총 {len(all_transactions)}건의 거래 기록 수집 완료")
    
    return all_transactions


def filter_whale_transactions(transactions: List[Dict], whale_addresses: Dict[str, Set[str]]) -> List[Dict]:
    """
    whale_address로 필터링 및 중복 제거
    
    Parameters:
    -----------
    transactions : List[Dict]
        수집된 거래 기록 리스트
    whale_addresses : Dict[str, Set[str]]
        체인별 고래 지갑 주소 Set
    
    Returns:
    --------
    List[Dict] : 필터링된 거래 기록 리스트 (중복 제거됨)
    """
    print("\n" + "=" * 70)
    print("🔍 고래 지갑 주소로 필터링 중...")
    print("=" * 70)
    
    filtered = []
    seen_tx_hashes = set()  # 중복 제거용
    
    for tx in transactions:
        chain = tx.get('chain', '').lower()
        from_address = tx.get('from_address', '').lower() if tx.get('from_address') else None
        to_address = tx.get('to_address', '').lower() if tx.get('to_address') else None
        tx_hash = tx.get('tx_hash', '').lower()
        
        # 중복 체크
        if tx_hash in seen_tx_hashes:
            continue
        seen_tx_hashes.add(tx_hash)
        
        # 체인별 고래 지갑 주소 확인
        # 체인 매핑 (API 체인 -> whale_address 체인)
        chain_mapping = {
            'ethereum': 'ethereum',
            'bsc': 'bsc',
            'btc': 'btc',
            'ltc': 'ltc',
            'doge': 'doge',
            'vtc': 'vtc',
            'polkadot': 'polkadot',
            'solana': 'solana'
        }
        
        api_chain = chain_mapping.get(chain, chain)
        addresses = whale_addresses.get(api_chain, set())
        
        # LINK는 Ethereum 체인에서 처리
        if chain == 'ethereum' and 'ethereum' in whale_addresses:
            addresses = addresses.union(whale_addresses.get('ethereum', set()))
        
        # from_address 또는 to_address가 고래 지갑 주소와 일치하는지 확인
        if (from_address and from_address in addresses) or (to_address and to_address in addresses):
            filtered.append(tx)
    
    print(f"✅ 필터링 완료: {len(filtered)}/{len(transactions)}건 (중복 제거됨)")
    
    return filtered


def save_to_whale_transactions(supabase, transactions: List[Dict]) -> int:
    """
    필터링된 거래 기록을 whale_transactions에 저장
    
    Parameters:
    -----------
    supabase : Client
        Supabase 클라이언트
    transactions : List[Dict]
        필터링된 거래 기록 리스트
    
    Returns:
    --------
    int : 저장된 거래 기록 수
    """
    if not transactions:
        return 0
    
    print("\n" + "=" * 70)
    print("💾 whale_transactions 테이블에 저장 중...")
    print("=" * 70)
    
    records = []
    
    for tx in transactions:
        try:
            # 거래 기록을 whale_transactions 스키마에 맞게 변환
            record = {
                'tx_hash': tx['tx_hash'],
                'block_number': str(tx['block_number']),
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
            
            # 컨트랙트 주소가 있으면 추가 (토큰 거래인 경우)
            if tx.get('contract_address'):
                record['contract_address'] = tx['contract_address']
            
            records.append(record)
        
        except Exception as e:
            print(f"⚠️ 거래 기록 변환 실패: {e}")
            continue
    
    # 배치로 저장
    saved_count = 0
    batch_size = 100
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            response = supabase.table('whale_transactions').upsert(batch).execute()
            saved_count += len(batch)
            
            if (i + batch_size) % 500 == 0 or i + batch_size >= len(records):
                print(f"   ✅ {saved_count}/{len(records)}건 저장 완료...")
        
        except Exception as e:
            print(f"⚠️ whale_transactions 저장 실패 (배치 {i//batch_size + 1}): {e}")
            # 개별 저장 시도
            for record in batch:
                try:
                    supabase.table('whale_transactions').upsert([record]).execute()
                    saved_count += 1
                except:
                    pass
    
    print(f"\n✅ 총 {saved_count}건의 거래 기록을 whale_transactions에 저장했습니다.")
    
    return saved_count


def main():
    """메인 함수"""
    print("=" * 70)
    print("🐋 고래 거래 기록 수집 및 필터링 시스템")
    print("=" * 70)
    
    try:
        # Supabase 클라이언트 생성
        supabase = get_supabase_client()
        
        # 1. whale_address 테이블에서 고래 지갑 주소 조회
        print("\n[1단계] 고래 지갑 주소 조회 중...")
        whale_addresses = get_all_whale_addresses(supabase)
        
        if not whale_addresses:
            print("❌ 고래 지갑 주소를 찾을 수 없습니다.")
            return
        
        # 2. 모든 블록체인에서 거래 기록 수집
        print("\n[2단계] 블록체인별 거래 기록 수집 중...")
        all_transactions = collect_all_transactions(supabase, whale_addresses)
        
        if not all_transactions:
            print("❌ 수집된 거래 기록이 없습니다.")
            return
        
        # 3. whale_address로 필터링
        print("\n[3단계] 고래 지갑 주소로 필터링 중...")
        filtered_transactions = filter_whale_transactions(all_transactions, whale_addresses)
        
        if not filtered_transactions:
            print("❌ 필터링된 거래 기록이 없습니다.")
            return
        
        # 4. whale_transactions에 저장
        print("\n[4단계] whale_transactions 테이블에 저장 중...")
        saved_count = save_to_whale_transactions(supabase, filtered_transactions)
        
        print("\n" + "=" * 70)
        print("✅ 작업 완료")
        print("=" * 70)
        print(f"📊 수집 통계:")
        print(f"   - 수집된 거래 기록: {len(all_transactions)}건")
        print(f"   - 필터링된 거래 기록: {len(filtered_transactions)}건")
        print(f"   - 저장된 거래 기록: {saved_count}건")
    
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

