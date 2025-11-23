#!/usr/bin/env python3
"""name_tag 확인 스크립트"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

# CSV 파일에서 name_tag 확인
df = pd.read_csv('whale_address_cleaned.csv')
print('=' * 70)
print('CSV 파일 name_tag 확인')
print('=' * 70)
print(f'CSV 총 레코드: {len(df)}건')
empty_count = ((df['name_tag'].isna()) | (df['name_tag'] == '')).sum()
print(f'CSV name_tag 빈 값: {empty_count}건')

# BTC 샘플
print('\nCSV BTC 샘플 (상위 3건):')
for i, row in df[df['chain_type'] == 'BTC'].head(3).iterrows():
    print(f"  [{i+1}] ID: {row['id']}, Name Tag: '{row['name_tag']}'")

# Supabase에서 확인
print('\n' + '=' * 70)
print('Supabase name_tag 확인')
print('=' * 70)

response = supabase.table('whale_address').select('*').eq('chain_type', 'BTC').limit(5).execute()
print(f'\nSupabase BTC 샘플 (상위 5건):')
for i, record in enumerate(response.data, 1):
    name_tag = record.get('name_tag')
    print(f"  [{i}] ID: {record.get('id')}, Name Tag: '{name_tag}'")

# name_tag가 'Bitcoin'인 데이터 확인
response = supabase.table('whale_address').select('*', count='exact').eq('chain_type', 'BTC').eq('name_tag', 'Bitcoin').execute()
bitcoin_count = response.count if hasattr(response, 'count') else len(response.data)
print(f'\nSupabase에서 name_tag가 "Bitcoin"인 BTC 데이터: {bitcoin_count}건')
