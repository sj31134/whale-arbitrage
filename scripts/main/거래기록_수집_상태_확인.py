#!/usr/bin/env python3
"""거래 기록 수집 상태 확인"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print("=" * 70)
print("📊 whale_transactions 테이블 현황")
print("=" * 70)

# 체인별 통계
for chain in ['ethereum', 'bsc']:
    response = supabase.table('whale_transactions').select('*', count='exact').eq('chain', chain).execute()
    count = response.count if hasattr(response, 'count') else len(response.data)
    print(f"{chain.upper()}: {count}건")

# 코인별 통계
for coin in ['ETH', 'BNB', 'LINK']:
    response = supabase.table('whale_transactions').select('*', count='exact').eq('coin_symbol', coin).execute()
    count = response.count if hasattr(response, 'count') else len(response.data)
    print(f"{coin}: {count}건")

# 전체 통계
response = supabase.table('whale_transactions').select('*', count='exact').execute()
total = response.count if hasattr(response, 'count') else len(response.data)
print(f"\n전체: {total}건")

# 최근 거래 샘플
print("\n" + "=" * 70)
print("최근 거래 샘플 (상위 5건)")
print("=" * 70)

response = supabase.table('whale_transactions').select('*').order('block_timestamp', desc=True).limit(5).execute()
for i, tx in enumerate(response.data, 1):
    print(f"\n[{i}]")
    print(f"  TX Hash: {tx.get('tx_hash', '')[:20]}...")
    print(f"  Chain: {tx.get('chain', '')}")
    print(f"  Coin: {tx.get('coin_symbol', '')}")
    print(f"  From: {tx.get('from_address', '')[:30]}...")
    print(f"  Amount: {tx.get('amount', '')}")
    print(f"  Timestamp: {tx.get('block_timestamp', '')}")



