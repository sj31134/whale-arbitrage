#!/usr/bin/env python3
"""
Etherscan V2 API 테스트
"""

import os
import requests
from dotenv import load_dotenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

def test_v2_api():
    """Etherscan V2 API 테스트"""
    api_key = os.getenv('ETHERSCAN_API_KEY')
    
    if not api_key:
        print("❌ ETHERSCAN_API_KEY가 설정되지 않았습니다")
        return
    
    print("=" * 80)
    print("🧪 Etherscan V2 API 테스트")
    print("=" * 80)
    
    # 테스트 주소 (Binance 14)
    test_address = '0x28c6c06298d514db089934071355e5743bf21d60'
    
    print(f"\n테스트 주소: {test_address}")
    print(f"API 키: {api_key[:10]}...")
    
    # V2 API 테스트
    print("\n1️⃣ V2 API 테스트:")
    try:
        params = {
            'chainid': '1',
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
        
        response = requests.get('https://api.etherscan.io/v2/api', params=params, timeout=30)
        
        print(f"   HTTP Status: {response.status_code}")
        
        data = response.json()
        print(f"   API Status: {data.get('status')}")
        print(f"   API Message: {data.get('message')}")
        
        if data.get('status') == '1':
            result = data.get('result', [])
            print(f"   ✅ 결과: {len(result)}건")
            
            if result:
                first_tx = result[0]
                print(f"\n   첫 번째 거래:")
                print(f"     Hash: {first_tx.get('hash')}")
                print(f"     Block: {first_tx.get('blockNumber')}")
                print(f"     Value: {int(first_tx.get('value', 0)) / 1e18:.4f} ETH")
        else:
            print(f"   ❌ 오류: {data.get('message')}")
            print(f"   상세: {data.get('result', 'N/A')}")
    
    except Exception as e:
        print(f"   ❌ 예외: {e}")
    
    # V1 API 비교
    print("\n2️⃣ V1 API 비교 (현재 사용 중):")
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
        
        print(f"   HTTP Status: {response.status_code}")
        
        data = response.json()
        print(f"   API Status: {data.get('status')}")
        print(f"   API Message: {data.get('message')}")
        
        if data.get('status') == '1':
            result = data.get('result', [])
            print(f"   ✅ 결과: {len(result)}건")
        else:
            print(f"   ❌ 오류: {data.get('message')}")
    
    except Exception as e:
        print(f"   ❌ 예외: {e}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    test_v2_api()

