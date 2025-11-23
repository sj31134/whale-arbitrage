#!/usr/bin/env python3
"""Etherscan API 상세 테스트"""

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

print("=" * 70)
print("Etherscan API 상세 테스트")
print("=" * 70)
print(f"API Key: {api_key[:10]}...{api_key[-5:]}")

# 1. API 키 유효성 확인 (간단한 조회)
print("\n[1] API 키 유효성 확인")
url = 'https://api.etherscan.io/api'
params = {
    'module': 'proxy',
    'action': 'eth_blockNumber',
    'apikey': api_key
}

try:
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    if data.get('status') == '1':
        print(f"✅ API 키 유효함 (최신 블록: {int(data.get('result', '0'), 16)})")
    else:
        print(f"❌ API 키 오류: {data.get('message')}")
except Exception as e:
    print(f"❌ 오류: {e}")

# 2. 거래 조회 테스트 (간단한 주소)
print("\n[2] 거래 조회 테스트")
test_address = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'  # Vitalik Buterin 주소
params = {
    'module': 'account',
    'action': 'txlist',
    'address': test_address,
    'startblock': 0,
    'endblock': 99999999,
    'sort': 'desc',
    'page': 1,
    'offset': 5,  # 처음 5개만
    'apikey': api_key
}

try:
    response = requests.get(url, params=params, timeout=30)
    data = response.json()
    
    print(f"Status: {data.get('status')}")
    print(f"Message: {data.get('message')}")
    
    if data.get('status') == '1':
        result = data.get('result', [])
        if isinstance(result, list):
            print(f"✅ 거래 수: {len(result)}건")
        else:
            print(f"Result type: {type(result)}")
    elif data.get('status') == '0':
        msg = data.get('message', '')
        print(f"❌ 오류: {msg}")
        if 'Invalid API Key' in msg:
            print("   → API 키가 유효하지 않습니다.")
        elif 'rate limit' in msg.lower():
            print("   → Rate limit에 도달했습니다. 잠시 후 다시 시도하세요.")
except Exception as e:
    print(f"❌ 오류: {e}")



