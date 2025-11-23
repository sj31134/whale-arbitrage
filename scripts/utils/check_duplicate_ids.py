#!/usr/bin/env python3
"""중복 ID 확인"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from collections import Counter

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print('=' * 70)
print('중복 ID 확인')
print('=' * 70)

for chain in ['BTC', 'ETH', 'LTC', 'DOGE', 'VTC']:
    response = supabase.table('whale_address').select('id').eq('chain_type', chain).execute()
    ids = [r['id'] for r in response.data]
    
    id_counts = Counter(ids)
    duplicates = {id_val: count for id_val, count in id_counts.items() if count > 1}
    
    print(f'\n{chain}:')
    print(f'  총 레코드: {len(ids)}건')
    print(f'  고유 ID: {len(set(ids))}건')
    print(f'  중복 ID: {len(duplicates)}개')
    
    if duplicates:
        print(f'  중복 ID 샘플: {dict(list(duplicates.items())[:5])}')
    else:
        print(f'  ✅ 중복 없음')



