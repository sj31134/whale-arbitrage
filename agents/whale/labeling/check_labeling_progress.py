#!/usr/bin/env python3
"""
작업 진행 상황 체크
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_supabase_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    return create_client(supabase_url, supabase_key)

def check_progress():
    supabase = get_supabase_client()
    print("📊 작업 진행 상황 체크 중...")
    
    try:
        # 1. 전체 데이터 수
        res_total = supabase.table('whale_transactions').select('count', count='exact').execute()
        total_count = res_total.count
        
        # 2. 처리 완료된 데이터 수 (transaction_direction IS NOT NULL)
        res_done = supabase.table('whale_transactions')\
            .select('count', count='exact')\
            .not_.is_('transaction_direction', 'null')\
            .execute()
        done_count = res_done.count
        
        # 3. 남은 데이터 수
        remaining = total_count - done_count
        progress = (done_count / total_count * 100) if total_count > 0 else 0
        
        print(f"\n📈 전체 진행률: {progress:.2f}%")
        print(f"   - 전체: {total_count:,}건")
        print(f"   - 완료: {done_count:,}건")
        print(f"   - 잔여: {remaining:,}건")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == '__main__':
    check_progress()

