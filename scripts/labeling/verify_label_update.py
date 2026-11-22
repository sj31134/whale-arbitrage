#!/usr/bin/env python3
"""
라벨 업데이트가 실제로 진행되고 있는지 검증
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def check_recent_updates(supabase):
    """최근 업데이트된 레코드 확인"""
    print("=" * 80)
    print("🔍 최근 업데이트 검증")
    print("=" * 80)
    
    try:
        # from_label이 최근 업데이트된 것 (updated_at 기준)
        print("\n1️⃣ 최근 업데이트된 from_label (5건):")
        response = supabase.table('whale_transactions')\
            .select('tx_hash, from_address, from_label, updated_at')\
            .not_.is_('from_label', 'null')\
            .order('updated_at', desc=True)\
            .limit(5)\
            .execute()
        
        if response.data:
            for idx, tx in enumerate(response.data, 1):
                print(f"  {idx}. {tx['tx_hash'][:16]}...")
                print(f"     from_label: {tx['from_label']}")
                print(f"     updated_at: {tx['updated_at']}")
        else:
            print("  ⚠️ 데이터 없음")
        
        # to_label이 최근 업데이트된 것
        print("\n2️⃣ 최근 업데이트된 to_label (5건):")
        response = supabase.table('whale_transactions')\
            .select('tx_hash, to_address, to_label, updated_at')\
            .not_.is_('to_label', 'null')\
            .order('updated_at', desc=True)\
            .limit(5)\
            .execute()
        
        if response.data:
            for idx, tx in enumerate(response.data, 1):
                print(f"  {idx}. {tx['tx_hash'][:16]}...")
                print(f"     to_label: {tx['to_label']}")
                print(f"     updated_at: {tx['updated_at']}")
        else:
            print("  ⚠️ 데이터 없음")
        
    except Exception as e:
        print(f"❌ 오류: {e}")

def count_labels_realtime(supabase):
    """실시간으로 라벨 개수 측정 (10초 간격)"""
    print("\n" + "=" * 80)
    print("⏱️  실시간 진행 확인 (10초 간격 2회 측정)")
    print("=" * 80)
    
    try:
        # 첫 번째 측정
        response1 = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .not_.is_('from_label', 'null')\
            .execute()
        count1 = response1.count if hasattr(response1, 'count') else len(response1.data)
        
        print(f"\n1차 측정: from_label = {count1:,}건")
        print("⏳ 10초 대기 중...")
        time.sleep(10)
        
        # 두 번째 측정
        response2 = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .not_.is_('from_label', 'null')\
            .execute()
        count2 = response2.count if hasattr(response2, 'count') else len(response2.data)
        
        print(f"2차 측정: from_label = {count2:,}건")
        
        diff = count2 - count1
        if diff > 0:
            print(f"\n✅ 증가: +{diff}건 (10초 동안)")
            print(f"   예상 속도: 약 {diff * 6}건/분, {diff * 360}건/시간")
            remaining = 465766 - count2
            hours = remaining / (diff * 360)
            print(f"   예상 완료: 약 {hours:.1f}시간 후")
        elif diff == 0:
            print(f"\n⚠️ 변화 없음 - 프로세스가 멈췄거나 완료됨")
        else:
            print(f"\n❌ 감소: {diff}건 (이상 현상)")
        
    except Exception as e:
        print(f"❌ 오류: {e}")

def main():
    """메인 함수"""
    try:
        supabase = get_supabase_client()
        
        # 최근 업데이트 확인
        check_recent_updates(supabase)
        
        # 실시간 진행 확인
        count_labels_realtime(supabase)
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

