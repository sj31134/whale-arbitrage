#!/usr/bin/env python3
"""
소규모 테스트: ETH 체인의 첫 5개 주소만 수집하여 테스트
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

from src.collectors.multi_chain_collector import fetch_etherscan_transactions

def test_eth_collection():
    """ETH 체인의 첫 5개 주소만 수집 테스트"""
    print("=" * 70)
    print("소규모 테스트: ETH 체인 수집")
    print("=" * 70)
    
    # Supabase 클라이언트 생성
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase 설정이 없습니다.")
        return
    
    supabase = create_client(supabase_url, supabase_key)
    
    # ETH 체인의 첫 5개 주소만 조회
    print("\n[1단계] ETH 체인의 첫 5개 주소 조회 중...")
    response = supabase.table('whale_address').select('address').eq('chain_type', 'ETH').limit(5).execute()
    
    if not response.data:
        print("❌ ETH 체인의 고래 지갑 주소를 찾을 수 없습니다.")
        return
    
    addresses = [row['address'] for row in response.data if row.get('address')]
    print(f"✅ {len(addresses)}개의 주소 조회 완료")
    for i, addr in enumerate(addresses, 1):
        print(f"   {i}. {addr[:20]}...")
    
    # Etherscan API 키 확인
    etherscan_key = os.getenv('ETHERSCAN_API_KEY', '')
    if not etherscan_key:
        print("\n❌ ETHERSCAN_API_KEY가 설정되지 않았습니다.")
        return
    
    # 거래 기록 수집
    print(f"\n[2단계] {len(addresses)}개 주소의 거래 기록 수집 중...")
    print("⚠️  이 작업은 몇 분 정도 걸릴 수 있습니다...")
    
    try:
        transactions = fetch_etherscan_transactions(addresses, 'ethereum', etherscan_key)
        print(f"\n✅ 총 {len(transactions)}건의 거래 기록 수집 완료")
        
        if transactions:
            print("\n수집된 거래 기록 샘플 (최대 5개):")
            for i, tx in enumerate(transactions[:5], 1):
                print(f"\n  {i}. 거래 해시: {tx.get('tx_hash', 'N/A')[:20]}...")
                print(f"     From: {tx.get('from_address', 'N/A')[:20]}...")
                print(f"     To: {tx.get('to_address', 'N/A')[:20] if tx.get('to_address') else 'N/A'}...")
                print(f"     금액: {tx.get('value', 0):.6f} {tx.get('coin_symbol', 'ETH')}")
                print(f"     시간: {tx.get('block_timestamp', 'N/A')}")
        else:
            print("\n⚠️  수집된 거래 기록이 없습니다.")
            print("   (주소에 거래 기록이 없거나 API 제한에 걸렸을 수 있습니다)")
        
        # 필터링 테스트
        print(f"\n[3단계] 고래 지갑 주소로 필터링 테스트...")
        whale_addresses = {addr.lower() for addr in addresses}
        
        filtered = []
        for tx in transactions:
            from_addr = tx.get('from_address', '').lower() if tx.get('from_address') else None
            to_addr = tx.get('to_address', '').lower() if tx.get('to_address') else None
            
            if (from_addr and from_addr in whale_addresses) or (to_addr and to_addr in whale_addresses):
                filtered.append(tx)
        
        print(f"✅ 필터링 완료: {len(filtered)}/{len(transactions)}건")
        
        if filtered:
            print("\n필터링된 거래 기록 샘플 (최대 3개):")
            for i, tx in enumerate(filtered[:3], 1):
                print(f"\n  {i}. 거래 해시: {tx.get('tx_hash', 'N/A')[:20]}...")
                print(f"     From: {tx.get('from_address', 'N/A')[:20]}...")
                print(f"     To: {tx.get('to_address', 'N/A')[:20] if tx.get('to_address') else 'N/A'}...")
                print(f"     금액: {tx.get('value', 0):.6f} {tx.get('coin_symbol', 'ETH')}")
        
        print("\n" + "=" * 70)
        print("✅ 테스트 완료")
        print("=" * 70)
        print(f"\n📊 테스트 결과:")
        print(f"   - 테스트 주소 수: {len(addresses)}개")
        print(f"   - 수집된 거래 기록: {len(transactions)}건")
        print(f"   - 필터링된 거래 기록: {len(filtered)}건")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_eth_collection()



