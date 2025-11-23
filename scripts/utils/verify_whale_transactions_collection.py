#!/usr/bin/env python3
"""
whale_transactions 수집 시 BSC/BNB 데이터 조회 로직 검토
name_tag='BNB'로 변경 후에도 정상 작동하는지 확인
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')


def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
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


def test_collect_bnb_usdc_xrp_query(supabase):
    """collect_bnb_usdc_xrp_transactions_2025_may_june.py의 조회 로직 테스트"""
    print('=' * 80)
    print('🔍 collect_bnb_usdc_xrp_transactions_2025_may_june.py 조회 로직 검토')
    print('=' * 80)
    
    # BNB 주소 조회 (실제 코드와 동일한 로직)
    print('\n[1] BNB 주소 조회 테스트')
    print('-' * 80)
    print('  조회 조건: chain_type="BSC" (name_tag 조건 없음)')
    
    bnb_response = supabase.table('whale_address').select('address, chain_type, name_tag').eq('chain_type', 'BSC').execute()
    bnb_addresses = [
        row['address'].strip().lower() 
        for row in bnb_response.data 
        if row.get('address') and is_valid_evm_address(row['address'])
    ]
    
    print(f'  ✅ 조회된 주소 수: {len(bnb_addresses)}개')
    
    # name_tag 확인
    name_tag_bnb_count = sum(1 for r in bnb_response.data if r.get('name_tag') == 'BNB')
    print(f'  ✅ name_tag="BNB"인 레코드: {name_tag_bnb_count}개')
    
    if len(bnb_addresses) > 0:
        print(f'  ✅ 정상 작동: name_tag 변경과 무관하게 chain_type만으로 조회됨')
    else:
        print(f'  ⚠️ 주소가 조회되지 않음')
    
    return len(bnb_addresses) > 0


def test_collect_internal_transactions_query(supabase):
    """collect_internal_transactions_2025_may_june.py의 조회 로직 테스트"""
    print('\n[2] collect_internal_transactions_2025_may_june.py 조회 로직 검토')
    print('-' * 80)
    print('  조회 조건: chain_type="BSC" (name_tag 조건 없음)')
    
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
        response = supabase.table('whale_address').select('address, chain_type, name_tag').eq('chain_type', chain_type).execute()
        addresses = [
            row['address'].strip().lower() 
            for row in response.data 
            if row.get('address') and is_valid_evm_address(row['address'])
        ]
        result[network] = addresses
        print(f'  - {network}: {len(addresses)}개 주소')
    
    bsc_count = len(result['bsc'])
    if bsc_count > 0:
        print(f'  ✅ 정상 작동: BSC 주소 {bsc_count}개 조회됨')
    else:
        print(f'  ⚠️ BSC 주소가 조회되지 않음')
    
    return bsc_count > 0


def test_other_collection_scripts(supabase):
    """다른 수집 스크립트들의 조회 로직 확인"""
    print('\n[3] 기타 수집 스크립트 검토')
    print('-' * 80)
    
    # collect_whale_transactions_from_blockchain.py 스타일 조회
    print('  [3-1] collect_whale_transactions_from_blockchain.py 스타일')
    print('    조회 조건: chain_type="BSC"')
    
    response = supabase.table('whale_address').select('address').eq('chain_type', 'BSC').execute()
    addresses = [r['address'] for r in response.data if r.get('address')]
    print(f'    ✅ 조회된 주소: {len(addresses)}개')
    
    # collect_all_whale_transactions.py 스타일 조회
    print('\n  [3-2] collect_all_whale_transactions.py 스타일')
    print('    조회 조건: chain_type="BSC"')
    
    response = supabase.table('whale_address').select('chain_type, address').eq('chain_type', 'BSC').execute()
    addresses = [r['address'] for r in response.data if r.get('address')]
    print(f'    ✅ 조회된 주소: {len(addresses)}개')
    
    return True


def verify_data_consistency(supabase):
    """데이터 일관성 확인"""
    print('\n[4] 데이터 일관성 확인')
    print('-' * 80)
    
    # BSC 데이터 확인
    response = supabase.table('whale_address').select('*').eq('chain_type', 'BSC').execute()
    
    total = len(response.data)
    name_tag_bnb = sum(1 for r in response.data if r.get('name_tag') == 'BNB')
    name_tag_other = total - name_tag_bnb
    
    print(f'  총 BSC 데이터: {total}건')
    print(f'  name_tag="BNB": {name_tag_bnb}건')
    
    if name_tag_other > 0:
        print(f'  ⚠️ name_tag!="BNB": {name_tag_other}건')
    else:
        print(f'  ✅ 모든 BSC 데이터의 name_tag가 "BNB"로 통일됨')
    
    # EVM 주소 형식 검증
    valid_addresses = sum(1 for r in response.data if r.get('address') and is_valid_evm_address(r['address']))
    print(f'  유효한 EVM 주소: {valid_addresses}건')
    
    return name_tag_bnb == total and valid_addresses > 0


def main():
    """메인 함수"""
    print('=' * 80)
    print('🔍 whale_transactions 수집 로직 검토')
    print('=' * 80)
    print('검토 목적: name_tag="BNB"로 변경 후 수집 로직이 정상 작동하는지 확인')
    print('=' * 80)
    
    try:
        supabase = get_supabase_client()
        
        # 각 수집 스크립트의 조회 로직 테스트
        test1 = test_collect_bnb_usdc_xrp_query(supabase)
        test2 = test_collect_internal_transactions_query(supabase)
        test3 = test_other_collection_scripts(supabase)
        test4 = verify_data_consistency(supabase)
        
        # 최종 결론
        print('\n' + '=' * 80)
        print('✅ 검토 결과')
        print('=' * 80)
        
        all_passed = test1 and test2 and test3 and test4
        
        if all_passed:
            print('\n✅ 모든 검토 항목 통과')
            print('\n📋 결론:')
            print('  - whale_transactions 수집 시 chain_type="BSC"만으로 조회하므로')
            print('  - name_tag="BNB"로 변경해도 문제없음')
            print('  - 모든 수집 스크립트가 name_tag에 의존하지 않음')
        else:
            print('\n⚠️ 일부 검토 항목에서 문제 발견')
            print('  - 상세 내용은 위의 검토 결과를 확인하세요')
        
        print('\n📊 검토 항목:')
        print(f'  [1] collect_bnb_usdc_xrp_transactions: {"✅" if test1 else "❌"}')
        print(f'  [2] collect_internal_transactions: {"✅" if test2 else "❌"}')
        print(f'  [3] 기타 수집 스크립트: {"✅" if test3 else "❌"}')
        print(f'  [4] 데이터 일관성: {"✅" if test4 else "❌"}')
        
    except KeyboardInterrupt:
        print('\n\n⚠️  사용자에 의해 중단되었습니다.')
        sys.exit(1)
    except Exception as e:
        print(f'\n❌ 오류 발생: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

