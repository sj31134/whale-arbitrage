#!/usr/bin/env python3
"""최종 whale_address 테이블 확인"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print('=' * 70)
print('📊 Supabase whale_address 테이블 최종 확인')
print('=' * 70)

# 체인별 통계
for chain in ['BTC', 'ETH', 'LTC', 'DOGE', 'VTC']:
    response = supabase.table('whale_address').select('*', count='exact').eq('chain_type', chain).execute()
    count = response.count if hasattr(response, 'count') else len(response.data)
    print(f'{chain}: {count}건')

# 전체 통계
response = supabase.table('whale_address').select('*', count='exact').execute()
total = response.count if hasattr(response, 'count') else len(response.data)
print(f'\n전체: {total}건')

# name_tag가 채워진 데이터 확인
print('\n' + '=' * 70)
print('name_tag 통계')
print('=' * 70)

chain_names = {'BTC': 'Bitcoin', 'ETH': 'Ethereum', 'LTC': 'Litecoin', 'DOGE': 'Dogecoin', 'VTC': 'Vertcoin'}
for chain, full_name in chain_names.items():
    response = supabase.table('whale_address').select('*', count='exact').eq('chain_type', chain).eq('name_tag', full_name).execute()
    count = response.count if hasattr(response, 'count') else len(response.data)
    print(f'{chain} ({full_name}): {count}건')

# 샘플 데이터 (name_tag가 채워진 것)
print('\n' + '=' * 70)
print('샘플 데이터 (name_tag가 채워진 데이터)')
print('=' * 70)

for chain, full_name in chain_names.items():
    response = supabase.table('whale_address').select('*').eq('chain_type', chain).eq('name_tag', full_name).limit(1).execute()
    if response.data:
        record = response.data[0]
        print(f'\n{chain}:')
        print(f'  ID: {record.get("id")}')
        print(f'  Address: {record.get("address")[:50]}...')
        print(f'  Name Tag: {record.get("name_tag")}')
        print(f'  Balance: {record.get("balance")}')



