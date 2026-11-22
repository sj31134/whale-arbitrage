#!/usr/bin/env python3
"""
BSC Hybrid System 검증 스크립트

BSC Hybrid Collection System의 각 컴포넌트를 검증합니다.
- Supabase 연결 및 주소 조회
- API 호출 및 응답 파싱
- 고액 거래 필터링 정확도
- 웹 스크래핑 성공률
- whale_transactions 저장 성공률
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.collectors.bsc_api_collector import (
    get_supabase_client,
    get_bsc_addresses_from_supabase,
    fetch_transactions_via_api,
    classify_transaction_size,
    is_high_value_transaction
)

from scripts.collectors.bsc_web_scraper import (
    scrape_transaction_details
)


def print_test_header(test_name: str):
    """테스트 헤더 출력"""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")


def print_test_result(success: bool, message: str = ""):
    """테스트 결과 출력"""
    if success:
        print(f"✅ 성공: {message}")
    else:
        print(f"❌ 실패: {message}")
    return success


def test_supabase_connection():
    """1. Supabase 연결 테스트"""
    print_test_header("Supabase 연결 및 환경 변수")
    
    try:
        # 환경 변수 확인
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url:
            return print_test_result(False, "SUPABASE_URL이 설정되지 않았습니다")
        
        if not supabase_key:
            return print_test_result(False, "SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
        
        print(f"SUPABASE_URL: {supabase_url[:30]}...")
        print(f"SUPABASE_KEY: {'*' * 20}...")
        
        # 연결 테스트
        supabase = get_supabase_client()
        
        # 간단한 쿼리로 연결 확인
        result = supabase.table('cryptocurrencies').select('id').limit(1).execute()
        
        return print_test_result(True, "Supabase 연결 성공")
    
    except Exception as e:
        return print_test_result(False, f"연결 실패: {e}")


def test_whale_address_query():
    """2. whale_address 테이블 조회 테스트"""
    print_test_header("whale_address 테이블에서 BSC 주소 조회")
    
    try:
        addresses = get_bsc_addresses_from_supabase()
        
        if not addresses:
            return print_test_result(False, "BSC 주소가 없습니다")
        
        print(f"조회된 주소 수: {len(addresses)}개")
        print(f"샘플 주소: {addresses[0]}")
        
        # 주소 형식 검증
        for addr in addresses[:5]:
            if not addr.startswith('0x'):
                return print_test_result(False, f"잘못된 주소 형식: {addr}")
            if len(addr) != 42:
                return print_test_result(False, f"주소 길이 오류: {addr}")
        
        return print_test_result(True, f"{len(addresses)}개 주소 조회 성공")
    
    except Exception as e:
        return print_test_result(False, f"조회 실패: {e}")


def test_api_collection():
    """3. BSCScan API 호출 테스트"""
    print_test_header("BSCScan API 거래 수집")
    
    try:
        api_key = os.getenv('ETHERSCAN_API_KEY', '')
        
        if not api_key:
            return print_test_result(False, "ETHERSCAN_API_KEY가 설정되지 않았습니다")
        
        # 테스트 주소 (Binance Hot Wallet)
        test_address = "0xf977814e90da44bfa03b6295a0616a897441acec"
        
        print(f"테스트 주소: {test_address}")
        print(f"API 호출 중...")
        
        transactions = fetch_transactions_via_api(test_address, api_key)
        
        if not transactions:
            return print_test_result(False, "거래를 수집하지 못했습니다")
        
        print(f"수집된 거래 수: {len(transactions)}건")
        
        # 첫 거래 검증
        first_tx = transactions[0]
        required_fields = [
            'tx_hash', 'block_number', 'block_timestamp',
            'from_address', 'to_address', 'coin_symbol',
            'chain', 'amount', 'gas_used', 'gas_price'
        ]
        
        for field in required_fields:
            if field not in first_tx:
                return print_test_result(False, f"필수 필드 누락: {field}")
        
        print(f"샘플 거래:")
        print(f"  - TX Hash: {first_tx['tx_hash'][:20]}...")
        print(f"  - Block: {first_tx['block_number']}")
        print(f"  - Amount: {first_tx['amount']} BNB")
        print(f"  - Status: {first_tx['transaction_status']}")
        
        return print_test_result(True, f"{len(transactions)}건 수집 및 파싱 성공")
    
    except Exception as e:
        return print_test_result(False, f"API 호출 실패: {e}")


def test_high_value_filtering():
    """4. 고액 거래 필터링 테스트"""
    print_test_header("고액 거래 필터링")
    
    try:
        # 테스트 데이터
        test_transactions = [
            {'tx_hash': '0x1', 'amount': 50, 'coin_symbol': 'BNB'},      # 작은 거래
            {'tx_hash': '0x2', 'amount': 150, 'coin_symbol': 'BNB'},     # 고액
            {'tx_hash': '0x3', 'amount': 1500, 'coin_symbol': 'BNB'},    # 초대형
            {'tx_hash': '0x4', 'amount': 15000, 'coin_symbol': 'BNB'},   # 메가
        ]
        
        # 분류 테스트
        print("거래 분류 테스트:")
        for tx in test_transactions:
            category = classify_transaction_size(tx['amount'], tx['coin_symbol'])
            is_high_value = is_high_value_transaction(tx)
            
            print(f"  {tx['amount']} BNB -> {category or 'NORMAL'} (고액: {is_high_value})")
        
        # 필터링 테스트
        high_value_txs = [tx for tx in test_transactions if is_high_value_transaction(tx)]
        
        expected_count = 3  # 150, 1500, 15000
        if len(high_value_txs) != expected_count:
            return print_test_result(
                False,
                f"필터링 오류: 예상 {expected_count}건, 실제 {len(high_value_txs)}건"
            )
        
        return print_test_result(True, f"필터링 정확: {len(high_value_txs)}/{len(test_transactions)}건")
    
    except Exception as e:
        return print_test_result(False, f"필터링 테스트 실패: {e}")


def test_web_scraping():
    """5. 웹 스크래핑 테스트"""
    print_test_header("웹 스크래핑")
    
    try:
        # 실제 BNB 거래 해시 (Binance)
        test_tx_hash = "0x7c025a75d7506b09a47c4468b222a82b6c77e20b95af89086b4e22e0e3b45e28"
        
        print(f"테스트 TX: {test_tx_hash}")
        print(f"스크래핑 중...")
        
        result = scrape_transaction_details(test_tx_hash)
        
        if not result:
            return print_test_result(False, "스크래핑 결과 없음")
        
        print(f"스크래핑 결과:")
        for key, value in result.items():
            if value:
                print(f"  {key}: {value}")
        
        # 최소한 하나 이상의 정보가 추출되어야 함
        has_data = any(v is not None for v in result.values())
        
        if not has_data:
            return print_test_result(False, "추가 정보를 추출하지 못했습니다")
        
        return print_test_result(True, "스크래핑 성공")
    
    except Exception as e:
        return print_test_result(False, f"스크래핑 실패: {e}")


def test_database_save():
    """6. whale_transactions 저장 테스트 (dry run)"""
    print_test_header("whale_transactions 저장 (검증만)")
    
    try:
        # 테스트용 더미 데이터
        test_transaction = {
            'tx_hash': f'0xtest_{datetime.now().timestamp()}',
            'block_number': 12345678,
            'block_timestamp': datetime.now().isoformat(),
            'from_address': '0x' + '0' * 40,
            'to_address': '0x' + '1' * 40,
            'coin_symbol': 'BNB',
            'chain': 'bsc',
            'amount': 100.0,
            'amount_usd': None,
            'gas_used': 21000,
            'gas_price': 5000000000,
            'gas_fee_eth': 0.000105,
            'transaction_status': 'SUCCESS',
            'is_whale': True,
            'whale_category': 'WHALE'
        }
        
        # 필드 검증
        required_fields = [
            'tx_hash', 'block_number', 'block_timestamp',
            'from_address', 'to_address', 'coin_symbol',
            'chain', 'amount', 'transaction_status', 'is_whale'
        ]
        
        for field in required_fields:
            if field not in test_transaction:
                return print_test_result(False, f"필수 필드 누락: {field}")
        
        print("테스트 데이터 구조:")
        for key, value in test_transaction.items():
            print(f"  {key}: {type(value).__name__}")
        
        # 실제 저장은 하지 않음 (dry run)
        return print_test_result(True, "데이터 구조 검증 완료 (실제 저장 안함)")
    
    except Exception as e:
        return print_test_result(False, f"검증 실패: {e}")


def run_all_tests():
    """모든 테스트 실행"""
    print(f"\n{'#'*80}")
    print(f"# BSC Hybrid System 검증 테스트")
    print(f"# 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*80}")
    
    results = []
    
    # 테스트 실행
    results.append(("Supabase 연결", test_supabase_connection()))
    results.append(("whale_address 조회", test_whale_address_query()))
    results.append(("BSCScan API", test_api_collection()))
    results.append(("고액 거래 필터링", test_high_value_filtering()))
    results.append(("웹 스크래핑", test_web_scraping()))
    results.append(("DB 저장 검증", test_database_save()))
    
    # 결과 요약
    print(f"\n{'#'*80}")
    print(f"# 테스트 결과 요약")
    print(f"{'#'*80}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n총 {total}개 테스트 중 {passed}개 통과 ({passed/total*100:.0f}%)")
    
    if passed == total:
        print(f"\n🎉 모든 테스트를 통과했습니다!")
        return 0
    else:
        print(f"\n⚠️ {total - passed}개 테스트가 실패했습니다.")
        return 1


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='BSC Hybrid System Test')
    parser.add_argument('--test', type=str, help='특정 테스트만 실행 (1-6)')
    args = parser.parse_args()
    
    try:
        if args.test:
            test_num = int(args.test)
            tests = [
                test_supabase_connection,
                test_whale_address_query,
                test_api_collection,
                test_high_value_filtering,
                test_web_scraping,
                test_database_save
            ]
            
            if 1 <= test_num <= len(tests):
                result = tests[test_num - 1]()
                return 0 if result else 1
            else:
                print(f"❌ 잘못된 테스트 번호: {test_num}")
                return 1
        else:
            return run_all_tests()
    
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
        return 1
    
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())




