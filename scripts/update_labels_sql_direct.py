#!/usr/bin/env python3
"""
SQL로 직접 라벨 업데이트 (빠른 방법)
"""

import os
import sys
from pathlib import Path
from datetime import datetime
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

def check_before_update(supabase):
    """업데이트 전 상태 확인"""
    print("=" * 80)
    print("📊 업데이트 전 상태")
    print("=" * 80)
    
    try:
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .execute()
        total = response.count if hasattr(response, 'count') else len(response.data)
        
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .not_.is_('from_label', 'null')\
            .execute()
        from_labeled = response.count if hasattr(response, 'count') else len(response.data)
        
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .not_.is_('to_label', 'null')\
            .execute()
        to_labeled = response.count if hasattr(response, 'count') else len(response.data)
        
        print(f"\n총 거래 수: {total:,}건")
        print(f"from_label: {from_labeled:,}건 ({from_labeled/total*100:.2f}%)")
        print(f"to_label: {to_labeled:,}건 ({to_labeled/total*100:.2f}%)")
        
        return total, from_labeled, to_labeled
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return 0, 0, 0

def update_labels_with_sql(supabase):
    """SQL로 직접 라벨 업데이트"""
    print("\n" + "=" * 80)
    print("🚀 SQL로 빠른 업데이트 실행")
    print("=" * 80)
    
    try:
        # from_label 업데이트
        print("\n1️⃣ from_label 업데이트 중...")
        start_time = datetime.now()
        
        sql_from = """
        UPDATE whale_transactions wt
        SET from_label = wa.name_tag
        FROM whale_address wa
        WHERE LOWER(wt.from_address) = LOWER(wa.address)
          AND wt.from_label IS NULL
          AND wa.name_tag IS NOT NULL;
        """
        
        result = supabase.rpc('exec_sql', {'query': sql_from}).execute()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ from_label 업데이트 완료 ({duration:.2f}초)")
        
        # to_label 업데이트
        print("\n2️⃣ to_label 업데이트 중...")
        start_time = datetime.now()
        
        sql_to = """
        UPDATE whale_transactions wt
        SET to_label = wa.name_tag
        FROM whale_address wa
        WHERE LOWER(wt.to_address) = LOWER(wa.address)
          AND wt.to_label IS NULL
          AND wa.name_tag IS NOT NULL;
        """
        
        result = supabase.rpc('exec_sql', {'query': sql_to}).execute()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ to_label 업데이트 완료 ({duration:.2f}초)")
        
        return True
        
    except Exception as e:
        print(f"❌ SQL 실행 오류: {e}")
        print("\n⚠️ Supabase에서 직접 SQL을 실행해주세요:")
        print("\n" + "=" * 80)
        print("Supabase Dashboard → SQL Editor에서 다음 SQL 실행:")
        print("=" * 80)
        
        sql_file = PROJECT_ROOT / 'sql' / 'update_whale_labels_fast.sql'
        if sql_file.exists():
            with open(sql_file, 'r') as f:
                print(f.read())
        
        return False

def check_after_update(supabase):
    """업데이트 후 상태 확인"""
    print("\n" + "=" * 80)
    print("📊 업데이트 후 상태")
    print("=" * 80)
    
    try:
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .execute()
        total = response.count if hasattr(response, 'count') else len(response.data)
        
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .not_.is_('from_label', 'null')\
            .execute()
        from_labeled = response.count if hasattr(response, 'count') else len(response.data)
        
        response = supabase.table('whale_transactions')\
            .select('*', count='exact')\
            .not_.is_('to_label', 'null')\
            .execute()
        to_labeled = response.count if hasattr(response, 'count') else len(response.data)
        
        print(f"\n총 거래 수: {total:,}건")
        print(f"from_label: {from_labeled:,}건 ({from_labeled/total*100:.2f}%)")
        print(f"to_label: {to_labeled:,}건 ({to_labeled/total*100:.2f}%)")
        
        # 라벨 분포 확인
        print("\n" + "=" * 80)
        print("📈 라벨 분포 (상위 10개)")
        print("=" * 80)
        
        response = supabase.table('whale_transactions')\
            .select('from_label')\
            .not_.is_('from_label', 'null')\
            .limit(10000)\
            .execute()
        
        from collections import Counter
        if response.data:
            label_counts = Counter([row['from_label'] for row in response.data])
            print("\nfrom_label:")
            for label, count in label_counts.most_common(10):
                print(f"  {label:<40}: {count:>6,}건")
        
        response = supabase.table('whale_transactions')\
            .select('to_label')\
            .not_.is_('to_label', 'null')\
            .limit(10000)\
            .execute()
        
        if response.data:
            label_counts = Counter([row['to_label'] for row in response.data])
            print("\nto_label:")
            for label, count in label_counts.most_common(10):
                print(f"  {label:<40}: {count:>6,}건")
        
        return total, from_labeled, to_labeled
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        return 0, 0, 0

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='whale_transactions 라벨 빠른 업데이트')
    parser.add_argument('--yes', action='store_true', help='확인 없이 자동 진행')
    args = parser.parse_args()
    
    print("=" * 80)
    print("🚀 whale_transactions 라벨 빠른 업데이트 (SQL)")
    print("=" * 80)
    
    try:
        supabase = get_supabase_client()
        
        # 업데이트 전 상태
        before_total, before_from, before_to = check_before_update(supabase)
        
        # 확인
        if not args.yes:
            print("\n" + "=" * 80)
            response = input("SQL로 업데이트를 실행하시겠습니까? (y/n): ")
            if response.lower() != 'y':
                print("취소되었습니다.")
                return
        else:
            print("\n✅ 자동 진행 모드")
        
        # SQL 업데이트 실행
        start = datetime.now()
        success = update_labels_with_sql(supabase)
        end = datetime.now()
        
        if not success:
            print("\n⚠️ Python에서 직접 실행 실패")
            print("Supabase Dashboard에서 SQL을 직접 실행해주세요.")
            print(f"\nSQL 파일 위치: {PROJECT_ROOT / 'sql' / 'update_whale_labels_fast.sql'}")
            return
        
        # 업데이트 후 상태
        after_total, after_from, after_to = check_after_update(supabase)
        
        # 결과 요약
        print("\n" + "=" * 80)
        print("✅ 업데이트 완료")
        print("=" * 80)
        
        total_time = (end - start).total_seconds()
        print(f"\n총 소요 시간: {total_time:.2f}초")
        print(f"\nfrom_label: {before_from:,}건 → {after_from:,}건 (+{after_from - before_from:,}건)")
        print(f"to_label: {before_to:,}건 → {after_to:,}건 (+{after_to - before_to:,}건)")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

