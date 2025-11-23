#!/usr/bin/env python3
"""업로드 상태 확인"""

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
print(f'CSV ID 샘플: {df_csv["id"].head(5).tolist()}')

# Supabase에서 전체 데이터 확인
print('\n' + '=' * 70)
print('Supabase whale_address 테이블 확인')
print('=' * 70)

response = supabase.table('whale_address').select('*', count='exact').execute()
total = response.count if hasattr(response, 'count') else len(response.data)
print(f'전체 레코드 수: {total}건')

# CSV의 ID 중 몇 개가 Supabase에 있는지 확인
print('\n' + '=' * 70)
print('CSV ID와 Supabase 매칭 확인')
print('=' * 70)

csv_ids = set(df_csv['id'].tolist())
print(f'CSV 고유 ID 수: {len(csv_ids)}건')

# Supabase에서 모든 ID 가져오기
all_supabase_ids = set()
for chain in ['BTC', 'ETH', 'LTC', 'DOGE', 'VTC']:
    response = supabase.table('whale_address').select('id').eq('chain_type', chain).execute()
    chain_ids = {r['id'] for r in response.data}
    all_supabase_ids.update(chain_ids)
    print(f'{chain}: {len(chain_ids)}건')

print(f'\nSupabase 고유 ID 수: {len(all_supabase_ids)}건')

# CSV에 있는데 Supabase에 없는 ID
missing_ids = csv_ids - all_supabase_ids
print(f'\nCSV에 있지만 Supabase에 없는 ID: {len(missing_ids)}건')

if missing_ids:
    print('\n없는 ID 샘플 (처음 10개):')
    for id_val in list(missing_ids)[:10]:
        print(f'  {id_val}')
    
    # 해당 ID의 CSV 데이터 확인
    print('\n없는 ID의 CSV 데이터 샘플:')
    sample_missing = df_csv[df_csv['id'].isin(list(missing_ids)[:3])]
    for _, row in sample_missing.iterrows():
        print(f"  ID: {row['id']}, Chain: {row['chain_type']}, Address: {row['address'][:50]}...")

# Supabase에 있는데 CSV에 없는 ID (기존 데이터)
existing_only = all_supabase_ids - csv_ids
print(f'\nSupabase에만 있는 ID (기존 데이터): {len(existing_only)}건')



