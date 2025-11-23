#!/usr/bin/env python3
"""중복 데이터 확인"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from collections import Counter

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print('=' * 70)
print('중복 데이터 확인')
print('=' * 70)

# 모든 데이터 가져오기
response = supabase.table('whale_address').select('id, chain_type, address').execute()
all_data = response.data

print(f'전체 레코드 수: {len(all_data)}건')

# ID별 중복 확인
id_counts = Counter([r['id'] for r in all_data])
duplicate_ids = {id_val: count for id_val, count in id_counts.items() if count > 1}

if duplicate_ids:
    print(f'\n중복된 ID: {len(duplicate_ids)}개')
    print('\n중복 ID 샘플 (처음 10개):')
    for i, (id_val, count) in enumerate(list(duplicate_ids.items())[:10], 1):
        print(f'  [{i}] ID: {id_val}, 중복 횟수: {count}회')
        
        # 해당 ID의 모든 레코드 확인
        duplicates = [r for r in all_data if r['id'] == id_val]
        for j, dup in enumerate(duplicates, 1):
            print(f'      [{j}] Chain: {dup.get("chain_type")}, Address: {dup.get("address")[:50]}...')
else:
    print('\n중복된 ID 없음')

# address별 중복 확인
address_counts = Counter([r['address'] for r in all_data if r.get('address')])
duplicate_addresses = {addr: count for addr, count in address_counts.items() if count > 1}

if duplicate_addresses:
    print(f'\n중복된 주소: {len(duplicate_addresses)}개')
    print('\n중복 주소 샘플 (처음 5개):')
    for i, (addr, count) in enumerate(list(duplicate_addresses.items())[:5], 1):
        print(f'  [{i}] Address: {addr[:50]}..., 중복 횟수: {count}회')
else:
    print('\n중복된 주소 없음')

# 체인별 통계
print('\n' + '=' * 70)
print('체인별 통계')
print('=' * 70)
chain_counts = Counter([r.get('chain_type') for r in all_data])
for chain, count in sorted(chain_counts.items()):
    print(f'{chain}: {count}건')



