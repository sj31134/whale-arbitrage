#!/usr/bin/env python3
"""업로드된 whale_address 데이터 확인"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

# 체인별 통계
print('=' * 70)
print('📊 Supabase whale_address 테이블 통계')
print('=' * 70)

for chain in ['BTC', 'ETH', 'LTC', 'DOGE', 'VTC']:
    response = supabase.table('whale_address').select('*', count='exact').eq('chain_type', chain).execute()
    count = response.count if hasattr(response, 'count') else len(response.data)
    print(f'{chain}: {count}건')

# 전체 통계
response = supabase.table('whale_address').select('*', count='exact').execute()
total = response.count if hasattr(response, 'count') else len(response.data)
print(f'\n전체: {total}건')

# 샘플 데이터 확인
print('\n' + '=' * 70)
print('📋 샘플 데이터 (BTC 상위 3건)')
print('=' * 70)
response = supabase.table('whale_address').select('*').eq('chain_type', 'BTC').limit(3).execute()
for i, record in enumerate(response.data, 1):
    print(f'\n[{i}]')
    print(f'  ID: {record.get("id")}')
    print(f'  Chain: {record.get("chain_type")}')
    print(f'  Address: {record.get("address")}')
    print(f'  Name Tag: {record.get("name_tag")}')
    print(f'  Balance: {record.get("balance")}')
    print(f'  Percentage: {record.get("percentage")}')
    print(f'  Txn Count: {record.get("txn_count")}')



