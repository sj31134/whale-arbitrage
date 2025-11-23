#!/usr/bin/env python3
"""CSV 데이터가 Supabase에 있는지 확인"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

# CSV 파일 읽기
df_csv = pd.read_csv('whale_address_cleaned.csv')
print(f'CSV 파일 총 레코드: {len(df_csv)}건')
print(f'CSV 체인: {df_csv["chain_type"].unique().tolist()}')

# CSV의 ID 샘플 확인
csv_ids = df_csv['id'].tolist()
print(f'\nCSV ID 샘플 (처음 10개): {csv_ids[:10]}')

# Supabase에서 CSV의 ID가 있는지 확인
print('\n' + '=' * 70)
print('Supabase에서 CSV ID 확인')
print('=' * 70)

# 체인별로 확인
for chain in ['BTC', 'ETH', 'LTC', 'DOGE', 'VTC']:
    chain_csv = df_csv[df_csv['chain_type'] == chain]
    chain_csv_ids = set(chain_csv['id'].tolist())
    
    # Supabase에서 해당 체인의 모든 ID 가져오기
    response = supabase.table('whale_address').select('id').eq('chain_type', chain).execute()
    supabase_ids = {r['id'] for r in response.data}
    
    # 매칭 확인
    found = chain_csv_ids & supabase_ids
    missing = chain_csv_ids - supabase_ids
    
    print(f'\n{chain}:')
    print(f'  CSV ID 수: {len(chain_csv_ids)}건')
    print(f'  Supabase ID 수: {len(supabase_ids)}건')
    print(f'  매칭된 ID: {len(found)}건')
    print(f'  없는 ID: {len(missing)}건')
    
    if missing:
        print(f'  없는 ID 샘플: {list(missing)[:5]}')
    
    # Supabase에 있는 ID 샘플
    if supabase_ids:
        print(f'  Supabase ID 샘플: {list(supabase_ids)[:5]}')

# 특정 ID로 직접 확인
print('\n' + '=' * 70)
print('특정 ID 직접 확인')
print('=' * 70)

test_ids = ['BTC001', 'BTC002', 'ETH001', 'LTC001', 'DOGE001', 'VTC001']
for test_id in test_ids:
    response = supabase.table('whale_address').select('*').eq('id', test_id).execute()
    if response.data:
        print(f'✅ {test_id}: 존재함 (Chain: {response.data[0].get("chain_type")})')
    else:
        print(f'❌ {test_id}: 없음')



