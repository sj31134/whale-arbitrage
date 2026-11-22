#!/usr/bin/env python3
"""
to_label 직접 업데이트 (Python)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print("=" * 80, flush=True)
print("🚀 to_label 빠른 업데이트", flush=True)
print("=" * 80, flush=True)

# whale_address 매핑
wa = supabase.table('whale_address').select('address, name_tag').execute()
whale_map = {r['address'].lower().strip(): r['name_tag'] for r in wa.data if r.get('name_tag')}
print(f"\nwhale_address 매핑: {len(whale_map)}개")

# to_label NULL인 거래 조회 (배치로)
total_updated = 0
batch_size = 500
offset = 0

while offset < 465000:  # 최대 465,000건
    print(f"\n진행: {offset:,}건 처리, {total_updated:,}건 업데이트", flush=True)
    
    # 배치 조회
    wt = supabase.table('whale_transactions')\
        .select('tx_hash, to_address')\
        .is_('to_label', 'null')\
        .not_.is_('to_address', 'null')\
        .limit(batch_size)\
        .offset(offset)\
        .execute()
    
    if not wt.data:
        print("더 이상 업데이트할 데이터 없음", flush=True)
        break
    
    # 업데이트할 거래 찾기
    updates = []
    for tx in wt.data:
        to_addr = tx.get('to_address', '').lower().strip()
        if to_addr in whale_map:
            updates.append({
                'tx_hash': tx['tx_hash'],
                'to_label': whale_map[to_addr]
            })
    
    # 업데이트 실행
    for update in updates:
        try:
            supabase.table('whale_transactions')\
                .update({'to_label': update['to_label']})\
                .eq('tx_hash', update['tx_hash'])\
                .execute()
            total_updated += 1
        except Exception as e:
            pass
    
    offset += batch_size
    
    # 10,000건마다 상태 출력
    if offset % 10000 == 0:
        print(f"  💾 {total_updated:,}건 업데이트 완료", flush=True)

print(f"\n✅ 총 {total_updated:,}건 업데이트 완료!", flush=True)

