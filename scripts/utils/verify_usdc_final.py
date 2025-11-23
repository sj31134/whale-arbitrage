#!/usr/bin/env python3
"""
USDC 데이터 최종 확인
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print('=' * 80)
print('✅ USDC 데이터 최종 확인')
print('=' * 80)

# USDC chain_type 데이터 확인
response = supabase.table('whale_address').select('*', count='exact').eq('chain_type', 'USDC').eq('name_tag', 'USDC').execute()
count = response.count if hasattr(response, 'count') else len(response.data)
print(f'\n📊 USDC 데이터 (chain_type="USDC", name_tag="USDC"): {count}건')

if count > 0:
    # 샘플 데이터 출력
    sample_response = supabase.table('whale_address').select('*').eq('chain_type', 'USDC').eq('name_tag', 'USDC').limit(5).execute()
    print('\n📋 샘플 데이터 (상위 5건):')
    for i, record in enumerate(sample_response.data, 1):
        print(f'  [{i}] ID={record.get("id")}, Address={record.get("address")}, name_tag={record.get("name_tag")}')

# 삭제된 네트워크 확인
deleted_networks = ['POLYGON', 'ARBITRUM', 'OPTIMISM', 'AVALANCHE', 'SOL', 'BASE']
print('\n🗑️  삭제된 네트워크 확인:')
for chain_type in deleted_networks:
    response = supabase.table('whale_address').select('*', count='exact').eq('chain_type', chain_type).eq('name_tag', 'USD Coin').execute()
    count = response.count if hasattr(response, 'count') else len(response.data)
    status = '✅' if count == 0 else '⚠️'
    print(f'  {status} {chain_type} (name_tag="USD Coin"): {count}건')

print('\n' + '=' * 80)
print('✅ 확인 완료')
print('=' * 80)

