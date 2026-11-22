#!/usr/bin/env python3
"""최종 통계 확인"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print('=' * 70)
print('📊 최종 통계')
print('=' * 70)

for chain in ['BTC', 'ETH', 'LTC', 'DOGE', 'VTC', 'BSC', 'DOT', 'LINK', 'SOL']:
    response = supabase.table('whale_address').select('*', count='exact').eq('chain_type', chain).execute()
    count = response.count if hasattr(response, 'count') else len(response.data)
    print(f'{chain}: {count}건')

# 전체
response = supabase.table('whale_address').select('*', count='exact').execute()
total = response.count if hasattr(response, 'count') else len(response.data)
print(f'\n전체: {total}건')



