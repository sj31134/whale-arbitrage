#!/usr/bin/env python3
"""Etherscan API 테스트"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

api_key = os.getenv('ETHERSCAN_API_KEY', '')
if not api_key:
    print('❌ API 키가 없습니다.')
    exit(1)

# 테스트 주소 (ETH 고래 지갑 - 이미 거래 기록이 있는 주소)
test_address = '0x28c6c06298d514db089934071355e5743bf21d60'

print("=" * 70)
print("Etherscan API 테스트")
print("=" * 70)
print(f"테스트 주소: {test_address}")

url = 'https://api.etherscan.io/api'
params = {
    'module': 'account',
    'action': 'txlist',
    'address': test_address,
    'startblock': 0,
    'endblock': 99999999,
    'sort': 'desc',
    'page': 1,
    'offset': 10,  # 처음 10개만
    'apikey': api_key
}

try:
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    print(f"\nStatus: {data.get('status')}")
    print(f"Message: {data.get('message')}")
    
    if data.get('status') == '1' and data.get('result'):
        result = data['result']
        if isinstance(result, list):
            print(f"✅ 거래 수: {len(result)}건")
            if len(result) > 0:
                print(f"\n첫 번째 거래 샘플:")
                tx = result[0]
                print(f"  Hash: {tx.get('hash')[:30]}...")
                print(f"  From: {tx.get('from')}")
                print(f"  To: {tx.get('to')}")
                print(f"  Value: {int(tx.get('value', 0)) / 1e18} ETH")
                print(f"  Block: {tx.get('blockNumber')}")
        else:
            print(f"❌ Result가 리스트가 아닙니다: {type(result)}")
            print(f"Result: {str(result)[:200]}")
    elif data.get('status') == '0':
        print(f"❌ API 오류: {data.get('message')}")
    else:
        print(f"❌ 예상치 못한 응답: {data}")
        
except Exception as e:
    print(f"❌ 오류: {e}")
    import traceback
    traceback.print_exc()



