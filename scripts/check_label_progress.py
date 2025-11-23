#!/usr/bin/env python3
"""
라벨 업데이트 진행 상황 확인
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
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def check_labels(supabase):
    """라벨 상태 확인"""
    print("=" * 80)
    print("📊 whale_transactions 라벨 상태")
    print("=" * 80)
    
    try:
        # 전체 거래 수
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .execute()
        total = response.count if hasattr(response, 'count') else len(response.data)
        
        # from_label이 NULL이 아닌 것
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .not_.is_('from_label', 'null')\
            .execute()
        from_labeled = response.count if hasattr(response, 'count') else len(response.data)
        
        # to_label이 NULL이 아닌 것
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .not_.is_('to_label', 'null')\
            .execute()
        to_labeled = response.count if hasattr(response, 'count') else len(response.data)
        
        print(f"\n총 거래 수: {total:,}건")
        print(f"\nfrom_label:")
        print(f"  - 채워진 거래: {from_labeled:,}건 ({from_labeled/total*100:.2f}%)")
        print(f"  - NULL 거래: {total - from_labeled:,}건 ({(total-from_labeled)/total*100:.2f}%)")
        
        print(f"\nto_label:")
        print(f"  - 채워진 거래: {to_labeled:,}건 ({to_labeled/total*100:.2f}%)")
        print(f"  - NULL 거래: {total - to_labeled:,}건 ({(total-to_labeled)/total*100:.2f}%)")
        
        # 라벨별 통계
        print("\n" + "=" * 80)
        print("📈 from_label 분포 (상위 20개)")
        print("=" * 80)
        
        response = supabase.table('whale_transactions')\
            .select('from_label')\
            .not_.is_('from_label', 'null')\
            .execute()
        
        from collections import Counter
        label_counts = Counter([row['from_label'] for row in response.data])
        
        for label, count in label_counts.most_common(20):
            print(f"  {label:<40}: {count:>8,}건")
        
        print("\n" + "=" * 80)
        print("📈 to_label 분포 (상위 20개)")
        print("=" * 80)
        
        response = supabase.table('whale_transactions')\
            .select('to_label')\
            .not_.is_('to_label', 'null')\
            .execute()
        
        label_counts = Counter([row['to_label'] for row in response.data])
        
        for label, count in label_counts.most_common(20):
            print(f"  {label:<40}: {count:>8,}건")
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    try:
        supabase = get_supabase_client()
        check_labels(supabase)
    except Exception as e:
        print(f"❌ 오류: {e}")
        sys.exit(1)

