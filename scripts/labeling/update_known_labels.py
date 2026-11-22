#!/usr/bin/env python3
"""
정적 리스트(known_exchanges.py)를 사용하여 whale_address 테이블 업데이트
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.data.known_exchanges import KNOWN_EXCHANGES

load_dotenv(PROJECT_ROOT / 'config' / '.env')

def main():
    print("=" * 80)
    print("📚 정적 거래소 리스트 업데이트")
    print("=" * 80)
    
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    )
    
    updated_count = 0
    
    for exchange in KNOWN_EXCHANGES:
        try:
            # upsert using address + chain_type matching?
            # address is usually unique enough per chain.
            # Let's check if address exists first
            
            res = supabase.table('whale_address')\
                .select('id')\
                .eq('address', exchange['address'].lower())\
                .execute()
                
            if res.data:
                # Update existing
                supabase.table('whale_address')\
                    .update({'name_tag': exchange['name_tag']})\
                    .eq('address', exchange['address'].lower())\
                    .execute()
                print(f"✅ 업데이트: {exchange['name_tag']}")
                updated_count += 1
            else:
                # Insert new (optional, but good to have)
                import uuid
                new_record = {
                    'id': str(uuid.uuid4()),
                    'address': exchange['address'].lower(),
                    'name_tag': exchange['name_tag'],
                    'chain_type': exchange['chain_type'],
                    'balance': '0',
                    'txn_count': '0'
                }
                supabase.table('whale_address').insert(new_record).execute()
                print(f"✨ 신규 추가: {exchange['name_tag']}")
                updated_count += 1
                
        except Exception as e:
            print(f"❌ 오류 ({exchange['name_tag']}): {e}")
            
    print(f"\n총 {updated_count}건 처리 완료.")

if __name__ == "__main__":
    main()

