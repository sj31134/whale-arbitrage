#!/usr/bin/env python3
"""
작업 진행 상황 체크 (샘플링 방식)
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

def check_progress_sampling():
    supabase = get_supabase_client()
    print("📊 작업 진행 상황 체크 (샘플링)...")
    
    try:
        # 1. 최근 데이터 100건 (최신순)
        print("\n1️⃣ 최근 데이터 (Block Timestamp DESC):")
        res_recent = supabase.table('whale_transactions')\
            .select('transaction_direction')\
            .order('block_timestamp', desc=True)\
            .limit(100)\
            .execute()
        
        recent_done = sum(1 for r in res_recent.data if r.get('transaction_direction'))
        print(f"   - 최근 100건 중 처리됨: {recent_done}건 ({recent_done}%)")
        
        # 2. 오래된 데이터 100건 (최신순)
        print("\n2️⃣ 오래된 데이터 (Block Timestamp ASC):")
        res_old = supabase.table('whale_transactions')\
            .select('transaction_direction')\
            .order('block_timestamp', desc=False)\
            .limit(100)\
            .execute()
        
        old_done = sum(1 for r in res_old.data if r.get('transaction_direction'))
        print(f"   - 오래된 100건 중 처리됨: {old_done}건 ({old_done}%)")
        
        # 3. 무작위 중간 데이터 확인 (중간 쯤의 블록 번호 기준)
        # 대략적인 중간 지점 파악을 위해 블록 번호 범위 확인은 생략하고,
        # transaction_direction이 NULL인 데이터가 있는지 확인
        
        print("\n3️⃣ 처리 안 된 데이터 존재 여부:")
        res_null = supabase.table('whale_transactions')\
            .select('tx_hash')\
            .is_('transaction_direction', 'null')\
            .limit(1)\
            .execute()
            
        if res_null.data:
            print("   ⚠️ 아직 처리되지 않은 데이터가 남아있습니다.")
        else:
            print("   ✅ 모든 데이터 처리 완료 (샘플링 기준)")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == '__main__':
    check_progress_sampling()

