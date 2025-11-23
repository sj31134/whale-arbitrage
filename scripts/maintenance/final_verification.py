#!/usr/bin/env python3
"""최종 검증: CSV 데이터가 Supabase에 제대로 추가되었는지 확인"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print('=' * 70)
print('📊 최종 검증: CSV 데이터가 Supabase에 추가되었는지 확인')
print('=' * 70)

# CSV 파일 읽기
df_csv = pd.read_csv('whale_address_cleaned.csv')
print(f'\nCSV 파일: {len(df_csv)}건')

# Supabase 전체 통계
response = supabase.table('whale_address').select('*', count='exact').execute()
total = response.count if hasattr(response, 'count') else len(response.data)
print(f'Supabase 전체: {total}건')

# 체인별 상세 확인
print('\n' + '=' * 70)
print('체인별 상세 확인')
print('=' * 70)

for chain in ['BTC', 'ETH', 'LTC', 'DOGE', 'VTC']:
    # CSV에서 해당 체인 데이터
    csv_chain = df_csv[df_csv['chain_type'] == chain]
    
    # Supabase에서 해당 체인 데이터
    response = supabase.table('whale_address').select('*').eq('chain_type', chain).execute()
    supabase_chain = response.data
    
    # name_tag 통계
    csv_with_name_tag = csv_chain[csv_chain['name_tag'].notna() & (csv_chain['name_tag'] != '')]
    supabase_with_name_tag = [r for r in supabase_chain if r.get('name_tag') and r.get('name_tag') != 'None']
    
    print(f'\n{chain}:')
    print(f'  CSV: {len(csv_chain)}건 (name_tag 채워진 것: {len(csv_with_name_tag)}건)')
    print(f'  Supabase: {len(supabase_chain)}건 (name_tag 채워진 것: {len(supabase_with_name_tag)}건)')
    
    # 샘플 데이터 비교
    print(f'\n  샘플 데이터 (CSV vs Supabase):')
    for i in range(min(3, len(csv_chain))):
        csv_row = csv_chain.iloc[i]
        supabase_row = next((r for r in supabase_chain if r.get('id') == csv_row['id']), None)
        
        if supabase_row:
            print(f'    [{i+1}] ID: {csv_row["id"]}')
            print(f'        CSV name_tag: "{csv_row["name_tag"]}"')
            print(f'        Supabase name_tag: "{supabase_row.get("name_tag")}"')
            print(f'        주소 일치: {csv_row["address"] == supabase_row.get("address")}')
        else:
            print(f'    [{i+1}] ID: {csv_row["id"]} - ❌ Supabase에 없음!')

# 특정 ID로 상세 확인
print('\n' + '=' * 70)
print('특정 ID 상세 확인')
print('=' * 70)

test_ids = ['BTC001', 'ETH001', 'LTC001', 'DOGE001', 'VTC001']
for test_id in test_ids:
    csv_row = df_csv[df_csv['id'] == test_id].iloc[0] if len(df_csv[df_csv['id'] == test_id]) > 0 else None
    response = supabase.table('whale_address').select('*').eq('id', test_id).execute()
    supabase_row = response.data[0] if response.data else None
    
    if csv_row is not None and supabase_row is not None:
        print(f'\n{test_id}:')
        print(f'  CSV:')
        print(f'    Chain: {csv_row["chain_type"]}')
        print(f'    Address: {csv_row["address"][:50]}...')
        print(f'    Name Tag: "{csv_row["name_tag"]}"')
        print(f'    Balance: {csv_row["balance"]}')
        print(f'  Supabase:')
        print(f'    Chain: {supabase_row.get("chain_type")}')
        print(f'    Address: {supabase_row.get("address", "")[:50]}...')
        print(f'    Name Tag: "{supabase_row.get("name_tag")}"')
        print(f'    Balance: {supabase_row.get("balance")}')
        print(f'  ✅ 매칭: {csv_row["address"] == supabase_row.get("address")}')
    else:
        print(f'\n{test_id}: ❌ 데이터 없음')



