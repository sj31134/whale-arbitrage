#!/usr/bin/env python3
"""
4개 테이블의 실제 스키마 및 관계 분석 스크립트
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_supabase_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    return create_client(supabase_url, supabase_key)

def inspect_table(supabase, table_name):
    print(f"\n🔍 Inspecting {table_name}...")
    try:
        response = supabase.table(table_name).select('*').limit(1).execute()
        if response.data:
            print(f"✅ Sample data found for {table_name}")
            keys = sorted(response.data[0].keys())
            for k in keys:
                print(f"   - {k}")
            return keys
        else:
            print(f"⚠️ No data in {table_name}, fetching column info might be limited.")
            # 데이터가 없으면 스키마를 알기 어렵지만, 여기서는 데이터가 있다고 가정
            return []
    except Exception as e:
        print(f"❌ Error inspecting {table_name}: {e}")
        return []

def main():
    supabase = get_supabase_client()
    
    tables = [
        'whale_transactions',
        'whale_address',
        'internal_transactions',
        'price_history'
    ]
    
    schemas = {}
    
    for t in tables:
        schemas[t] = inspect_table(supabase, t)
        
    print("\n" + "="*50)
    print("🔗 Relationship Analysis")
    print("="*50)
    
    # 1. whale_transactions vs whale_address
    wt_cols = schemas.get('whale_transactions', [])
    wa_cols = schemas.get('whale_address', [])
    
    print("\n1. whale_transactions <-> whale_address")
    if 'from_address' in wt_cols and 'address' in wa_cols:
        print("   - Linked by: whale_transactions.from_address = whale_address.address")
    if 'to_address' in wt_cols and 'address' in wa_cols:
        print("   - Linked by: whale_transactions.to_address = whale_address.address")
    if 'from_label' in wt_cols and 'name_tag' in wa_cols:
         print("   - Label Source: whale_address.name_tag -> whale_transactions.from_label")

    # 2. whale_transactions vs internal_transactions
    it_cols = schemas.get('internal_transactions', [])
    print("\n2. whale_transactions <-> internal_transactions")
    if 'tx_hash' in wt_cols and 'tx_hash' in it_cols:
        print("   - Linked by: whale_transactions.tx_hash = internal_transactions.tx_hash")
        print("   - Relationship: 1:N (One main tx can have multiple internal txs)")

    # 3. whale_transactions vs price_history
    ph_cols = schemas.get('price_history', [])
    print("\n3. whale_transactions <-> price_history")
    if 'block_timestamp' in wt_cols and 'timestamp' in ph_cols:
        print("   - Linked by Time: whale_transactions.block_timestamp ~ price_history.timestamp")
    if 'coin_symbol' in wt_cols:
        print("   - Linked by Symbol: whale_transactions.coin_symbol maps to price_history (via crypto_id/symbol mapping)")
        
    # Check for transaction_direction
    if 'transaction_direction' in wt_cols:
         print("\n✅ 'transaction_direction' column exists in whale_transactions.")
    else:
         print("\n❌ 'transaction_direction' column MISSING in whale_transactions.")

if __name__ == "__main__":
    main()

