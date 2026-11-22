#!/usr/bin/env python3
"""업로드 결과 검증"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print('=' * 70)
print('📊 업로드 결과 검증')
print('=' * 70)

# CSV 파일 읽기
df_csv = pd.read_csv('whale_address_cleaned.csv')
print(f'\nCSV 파일: {len(df_csv)}건')

# Supabase에서 체인별 확인
print('\n' + '=' * 70)
print('체인별 데이터 확인')
print('=' * 70)

for chain in ['BTC', 'ETH', 'LTC', 'DOGE', 'VTC']:
    # CSV에서 해당 체인 데이터
    csv_chain = df_csv[df_csv['chain_type'] == chain]
    csv_ids = set(csv_chain['id'].tolist())
    
    # Supabase에서 해당 체인 데이터
    response = supabase.table('whale_address').select('*').eq('chain_type', chain).execute()
    supabase_chain = response.data
    supabase_ids = {r['id'] for r in supabase_chain}
    
    # 매칭 확인
    found = csv_ids & supabase_ids
    missing = csv_ids - supabase_ids
    
    print(f'\n{chain}:')
    print(f'  CSV: {len(csv_ids)}건')
    print(f'  Supabase: {len(supabase_ids)}건')
    print(f'  매칭: {len(found)}건')
    print(f'  누락: {len(missing)}건')
    
    if missing:
        print(f'  누락된 ID 샘플: {list(missing)[:5]}')
    
    # 샘플 데이터 확인
    if supabase_chain:
        sample = supabase_chain[0]
        print(f'  샘플: ID={sample.get("id")}, Address={sample.get("address")[:30]}..., Name Tag={sample.get("name_tag")}')

# 전체 통계
print('\n' + '=' * 70)
print('전체 통계')
print('=' * 70)

response = supabase.table('whale_address').select('chain_type', count='exact').execute()
total = response.count if hasattr(response, 'count') else len(response.data)

chain_counts = {}
for record in response.data:
    chain = record.get('chain_type', 'UNKNOWN')
    chain_counts[chain] = chain_counts.get(chain, 0) + 1

print(f'\n전체 레코드: {total}건')
print('\n체인별 분포:')
for chain, count in sorted(chain_counts.items()):
    print(f'  {chain}: {count}건')

# CSV의 모든 ID가 Supabase에 있는지 확인
print('\n' + '=' * 70)
print('CSV ID 전체 매칭 확인')
print('=' * 70)

csv_all_ids = set(df_csv['id'].tolist())
supabase_all_ids = set()

# 모든 체인에서 ID 수집
for chain in ['BTC', 'ETH', 'LTC', 'DOGE', 'VTC', 'BSC', 'DOT', 'LINK', 'SOL']:
    response = supabase.table('whale_address').select('id').eq('chain_type', chain).execute()
    for record in response.data:
        supabase_all_ids.add(record['id'])

missing_all = csv_all_ids - supabase_all_ids
print(f'CSV 총 ID: {len(csv_all_ids)}건')
print(f'Supabase 총 ID: {len(supabase_all_ids)}건')
print(f'CSV에 있지만 Supabase에 없는 ID: {len(missing_all)}건')

if missing_all:
    print(f'\n누락된 ID 샘플: {list(missing_all)[:10]}')
else:
    print('\n✅ CSV의 모든 ID가 Supabase에 존재합니다!')



