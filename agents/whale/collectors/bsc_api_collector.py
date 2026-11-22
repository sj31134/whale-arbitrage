#!/usr/bin/env python3
"""
BSC API Collector Module

BSCScan API를 사용하여 BSC 체인의 거래 기록을 수집하는 모듈
- Supabase에서 BSC 주소 조회
- BSCScan API로 거래 수집
- whale_transactions 스키마에 맞게 변환
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional
from dotenv import load_dotenv
from supabase import create_client
import requests

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

# 환경 변수 로드
load_dotenv(PROJECT_ROOT / 'config' / '.env')

# API 설정
BSCSCAN_API_URL = 'https://api.bscscan.com/api'
RATE_LIMIT_DELAY = 0.25  # 초


def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)


def get_bsc_addresses_from_supabase() -> List[str]:
    """
    Supabase whale_address 테이블에서 BSC 주소 조회
    
    Returns:
    --------
    List[str] : BSC 주소 리스트
    """
    try:
        supabase = get_supabase_client()
        response = supabase.table('whale_address')\
            .select('address')\
            .eq('chain_type', 'BSC')\
            .execute()
        
        addresses = [
            row['address'].strip().lower() 
            for row in response.data 
            if row.get('address')
        ]
        
        print(f"✅ BSC 주소 조회 완료: {len(addresses)}개")
        return addresses
    
    except Exception as e:
        print(f"❌ BSC 주소 조회 실패: {e}")
        return []


def classify_transaction_size(amount: float, coin_symbol: str = 'BNB') -> str:
    """
    거래 금액에 따른 고래 카테고리 분류
    
    Parameters:
    -----------
    amount : float
        거래 금액 (BNB 단위)
    coin_symbol : str
        코인 심볼
    
    Returns:
    --------
    str : 고래 카테고리 (WHALE, LARGE_WHALE, MEGA_WHALE, None)
    """
    if coin_symbol == 'BNB':
        if amount >= 10000:
            return 'MEGA_WHALE'
        elif amount >= 1000:
            return 'LARGE_WHALE'
        elif amount >= 100:
            return 'WHALE'
    
    return None


def is_high_value_transaction(tx: Dict) -> bool:
    """
    고액 거래 여부 판단 (웹 스크래핑 대상)
    
    Parameters:
    -----------
    tx : Dict
        거래 정보
    
    Returns:
    --------
    bool : 고액 거래 여부
    """
    amount = tx.get('amount', 0)
    coin_symbol = tx.get('coin_symbol', 'BNB')
    
    # BNB 100개 이상
    if coin_symbol == 'BNB' and amount >= 100:
        return True
    
    # amount_usd가 있고 $50,000 이상
    amount_usd = tx.get('amount_usd')
    if amount_usd and amount_usd >= 50000:
        return True
    
    return False


def fetch_transactions_via_api(
    address: str, 
    api_key: str,
    start_block: int = 0,
    end_block: int = 99999999
) -> List[Dict]:
    """
    BSCScan API를 사용하여 특정 주소의 거래 기록 수집
    
    Parameters:
    -----------
    address : str
        지갑 주소
    api_key : str
        BSCScan API 키
    start_block : int
        시작 블록 (기본값: 0)
    end_block : int
        종료 블록 (기본값: 99999999)
    
    Returns:
    --------
    List[Dict] : 거래 기록 리스트 (whale_transactions 스키마 형식)
    """
    if not api_key:
        print("⚠️ ETHERSCAN_API_KEY가 설정되지 않았습니다.")
        return []
    
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': address,
        'startblock': start_block,
        'endblock': end_block,
        'sort': 'desc',
        'apikey': api_key
    }
    
    try:
        response = requests.get(BSCSCAN_API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') != '1' or not data.get('result'):
            if data.get('message') == 'No transactions found':
                return []
            print(f"⚠️ API 오류: {data.get('message', 'Unknown error')}")
            return []
        
        transactions = []
        for tx in data['result']:
            try:
                # 값 변환
                value = int(tx.get('value', 0)) / 1e18  # Wei -> BNB
                gas_used = int(tx.get('gasUsed', 0))
                gas_price = int(tx.get('gasPrice', 0))
                gas_fee = (gas_used * gas_price) / 1e18  # Wei -> BNB
                
                # 타임스탬프 변환
                block_timestamp = datetime.fromtimestamp(
                    int(tx.get('timeStamp', 0)), 
                    tz=timezone.utc
                )
                
                # whale_transactions 스키마에 맞게 매핑
                transaction = {
                    'tx_hash': tx.get('hash'),
                    'block_number': int(tx.get('blockNumber', 0)),
                    'block_timestamp': block_timestamp,
                    'from_address': tx.get('from', '').lower(),
                    'to_address': tx.get('to', '').lower() if tx.get('to') else None,
                    'coin_symbol': 'BNB',
                    'chain': 'bsc',
                    'amount': value,
                    'amount_usd': None,  # 가격 조회는 별도 처리
                    'gas_used': gas_used,
                    'gas_price': gas_price,
                    'gas_fee_eth': gas_fee,
                    'gas_fee_usd': None,
                    'transaction_status': 'FAILED' if tx.get('isError') == '1' else 'SUCCESS',
                    'is_whale': True,
                    'whale_category': classify_transaction_size(value, 'BNB'),
                    'contract_address': None,
                    'token_name': None,
                    'input_data': tx.get('input', ''),
                    'is_contract_to_contract': False,
                    'has_method_id': len(tx.get('input', '0x')) > 2,
                    'from_label': None,
                    'to_label': None,
                }
                
                transactions.append(transaction)
            
            except Exception as e:
                print(f"⚠️ 거래 파싱 실패: {e}")
                continue
        
        return transactions
    
    except requests.exceptions.RequestException as e:
        print(f"❌ API 호출 실패: {e}")
        return []
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return []


def collect_all_bsc_transactions(
    addresses: Optional[List[str]] = None,
    api_key: Optional[str] = None
) -> List[Dict]:
    """
    모든 BSC 주소의 거래 기록 수집
    
    Parameters:
    -----------
    addresses : Optional[List[str]]
        주소 리스트 (None일 경우 Supabase에서 조회)
    api_key : Optional[str]
        BSCScan API 키 (None일 경우 환경 변수에서 로드)
    
    Returns:
    --------
    List[Dict] : 모든 거래 기록 리스트
    """
    # API 키 로드
    if api_key is None:
        api_key = os.getenv('ETHERSCAN_API_KEY', '')
    
    if not api_key:
        print("❌ ETHERSCAN_API_KEY가 설정되지 않았습니다.")
        return []
    
    # 주소 로드
    if addresses is None:
        addresses = get_bsc_addresses_from_supabase()
    
    if not addresses:
        print("⚠️ 수집할 BSC 주소가 없습니다.")
        return []
    
    print(f"\n{'='*80}")
    print(f"BSC 거래 기록 수집 시작")
    print(f"{'='*80}")
    print(f"주소 수: {len(addresses)}개")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_transactions = []
    
    for i, address in enumerate(addresses, 1):
        print(f"\n[{i}/{len(addresses)}] 주소 처리 중: {address[:10]}...")
        
        transactions = fetch_transactions_via_api(address, api_key)
        
        if transactions:
            all_transactions.extend(transactions)
            print(f"  ✓ {len(transactions)}건 수집 완료")
        else:
            print(f"  - 거래 없음")
        
        # 진행 상황 출력
        if i % 10 == 0:
            print(f"\n진행률: {i}/{len(addresses)} ({i/len(addresses)*100:.1f}%)")
            print(f"현재까지 수집: {len(all_transactions)}건")
        
        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)
    
    print(f"\n{'='*80}")
    print(f"BSC 거래 기록 수집 완료")
    print(f"{'='*80}")
    print(f"종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"총 수집 거래: {len(all_transactions)}건")
    
    # 고액 거래 통계
    high_value_count = sum(1 for tx in all_transactions if is_high_value_transaction(tx))
    print(f"고액 거래 (웹 스크래핑 대상): {high_value_count}건")
    
    return all_transactions


def save_to_whale_transactions(transactions: List[Dict]) -> int:
    """
    거래 기록을 whale_transactions 테이블에 저장
    
    Parameters:
    -----------
    transactions : List[Dict]
        거래 기록 리스트
    
    Returns:
    --------
    int : 저장 성공 건수
    """
    if not transactions:
        print("⚠️ 저장할 거래가 없습니다.")
        return 0
    
    try:
        supabase = get_supabase_client()
        
        print(f"\n💾 whale_transactions 테이블에 저장 중...")
        
        # 저장을 위한 데이터 변환 (datetime -> ISO string)
        records = []
        for tx in transactions:
            record = tx.copy()
            if isinstance(record.get('block_timestamp'), datetime):
                record['block_timestamp'] = record['block_timestamp'].isoformat()
            records.append(record)
        
        # 배치 저장 (100건씩)
        saved_count = 0
        batch_size = 100
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            try:
                result = supabase.table('whale_transactions').upsert(batch).execute()
                saved_count += len(batch)
                print(f"  진행: {saved_count}/{len(records)}건 저장...")
            
            except Exception as e:
                print(f"  ⚠️ 배치 저장 실패 ({i}-{i+len(batch)}): {e}")
                continue
        
        print(f"✅ 저장 완료: {saved_count}건")
        return saved_count
    
    except Exception as e:
        print(f"❌ 저장 실패: {e}")
        return 0


def main():
    """메인 실행 함수 (테스트용)"""
    import argparse
    
    parser = argparse.ArgumentParser(description='BSC API Collector')
    parser.add_argument('--test', action='store_true', help='테스트 모드 (첫 3개 주소만)')
    parser.add_argument('--save', action='store_true', help='Supabase에 저장')
    args = parser.parse_args()
    
    try:
        # 주소 조회
        addresses = get_bsc_addresses_from_supabase()
        
        if args.test and addresses:
            addresses = addresses[:3]
            print(f"🧪 테스트 모드: 처음 3개 주소만 처리")
        
        # 거래 수집
        transactions = collect_all_bsc_transactions(addresses)
        
        if not transactions:
            print("⚠️ 수집된 거래가 없습니다.")
            return
        
        # 고액 거래 필터링
        high_value_txs = [tx for tx in transactions if is_high_value_transaction(tx)]
        print(f"\n📊 통계:")
        print(f"  - 전체 거래: {len(transactions)}건")
        print(f"  - 고액 거래: {len(high_value_txs)}건")
        
        # 저장
        if args.save:
            save_to_whale_transactions(transactions)
        else:
            print("\n💡 --save 옵션을 추가하면 Supabase에 저장합니다.")
    
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()




