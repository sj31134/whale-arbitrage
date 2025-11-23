#!/usr/bin/env python3
"""
Internal Transactions 테이블 데이터 확인
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent.parent
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

def check_internal_transactions(supabase):
    """Internal transactions 테이블 확인"""
    print("=" * 80)
    print("🔄 internal_transactions 테이블 데이터 확인")
    print("=" * 80)
    
    try:
        # 전체 레코드 수
        response = supabase.table('internal_transactions')\
            .select('*', count='exact')\
            .execute()
        
        total_count = response.count if hasattr(response, 'count') else len(response.data)
        print(f"\n총 레코드 수: {total_count:,}건")
        
        if total_count == 0:
            print("\n⚠️ 테이블이 비어있습니다!")
            return
        
        # 2025년 데이터
        response = supabase.table('internal_transactions')\
            .select('*', count='exact')\
            .gte('block_timestamp', START_DATE.isoformat())\
            .lte('block_timestamp', END_DATE.isoformat())\
            .execute()
        
        count_2025 = response.count if hasattr(response, 'count') else len(response.data)
        print(f"2025년 데이터: {count_2025:,}건")
        
        # 체인별 분포
        print("\n체인별 분포:")
        for chain in ['ethereum', 'bsc']:
            response = supabase.table('internal_transactions')\
                .select('*', count='exact')\
                .eq('chain', chain)\
                .gte('block_timestamp', START_DATE.isoformat())\
                .lte('block_timestamp', END_DATE.isoformat())\
                .execute()
            
            count = response.count if hasattr(response, 'count') else len(response.data)
            print(f"  {chain}: {count:,}건")
        
        # 최신 데이터 샘플
        print("\n최신 데이터 샘플 (5건):")
        response = supabase.table('internal_transactions')\
            .select('*')\
            .gte('block_timestamp', START_DATE.isoformat())\
            .lte('block_timestamp', END_DATE.isoformat())\
            .order('block_timestamp', desc=True)\
            .limit(5)\
            .execute()
        
        for idx, tx in enumerate(response.data, 1):
            print(f"\n  {idx}. {tx.get('tx_hash', 'N/A')[:16]}...")
            print(f"     Chain: {tx.get('chain')}")
            print(f"     Block: {tx.get('block_number')}")
            print(f"     Time: {tx.get('block_timestamp')}")
            print(f"     Value: {tx.get('value_eth', 0):.4f} ETH")
        
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()

def check_api_response():
    """실제 API 응답 테스트"""
    print("\n" + "=" * 80)
    print("🧪 Etherscan API 응답 테스트")
    print("=" * 80)
    
    import requests
    
    api_key = os.getenv('ETHERSCAN_API_KEY')
    if not api_key:
        print("❌ ETHERSCAN_API_KEY가 설정되지 않았습니다")
        return
    
    # 알려진 고래 주소 테스트 (Binance)
    test_address = '0x28c6c06298d514db089934071355e5743bf21d60'  # Binance 14
    
    print(f"\n테스트 주소: {test_address}")
    print(f"API 키: {api_key[:10]}...")
    
    try:
        params = {
            'module': 'account',
            'action': 'txlistinternal',
            'address': test_address,
            'startblock': 18900000,
            'endblock': 99999999,
            'page': 1,
            'offset': 10,
            'sort': 'desc',
            'apikey': api_key
        }
        
        response = requests.get('https://api.etherscan.io/api', params=params, timeout=30)
        
        print(f"\nHTTP Status: {response.status_code}")
        
        data = response.json()
        print(f"API Status: {data.get('status')}")
        print(f"API Message: {data.get('message')}")
        
        if data.get('status') == '1':
            result = data.get('result', [])
            print(f"결과 수: {len(result)}건")
            
            if result:
                print("\n첫 번째 거래 샘플:")
                first_tx = result[0]
                print(f"  Hash: {first_tx.get('hash')}")
                print(f"  Block: {first_tx.get('blockNumber')}")
                print(f"  From: {first_tx.get('from')[:16]}...")
                print(f"  To: {first_tx.get('to', 'N/A')[:16]}...")
                print(f"  Value: {int(first_tx.get('value', 0)) / 1e18:.4f} ETH")
        else:
            print(f"\n⚠️ API 오류: {data.get('message')}")
            print(f"상세: {data.get('result', 'N/A')}")
        
    except Exception as e:
        print(f"\n❌ 오류: {e}")
        import traceback
        traceback.print_exc()

def main():
    """메인 함수"""
    try:
        supabase = get_supabase_client()
        check_internal_transactions(supabase)
        check_api_response()
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

