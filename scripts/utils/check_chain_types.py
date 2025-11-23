#!/usr/bin/env python3
"""whale_address 테이블의 체인 타입 확인"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print('whale_address 테이블의 체인 타입 확인:')
response = supabase.table('whale_address').select('chain_type').execute()
chain_types = set([r['chain_type'] for r in response.data])
print(f'체인 타입: {sorted(chain_types)}')

# 각 체인 타입별 주소 수
print('\n체인 타입별 주소 수:')
for ct in sorted(chain_types):
    response = supabase.table('whale_address').select('address', count='exact').eq('chain_type', ct).execute()
    count = response.count if hasattr(response, 'count') else len(response.data)
    print(f'  {ct}: {count}건')



