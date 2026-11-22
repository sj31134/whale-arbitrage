#!/usr/bin/env python3
"""
price_history_btc와 price_history_eth 테이블 스키마 확인
"""

import os
import sys
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

def check_table_schema(supabase, table_name):
    """테이블 스키마 확인"""
    print(f"\n{'='*80}")
    print(f"📋 {table_name} 테이블 스키마")
    print(f"{'='*80}")
    
    try:
        # 샘플 데이터 1건 조회
        response = supabase.table(table_name).select('*').limit(1).execute()
        
        if response.data:
            sample = response.data[0]
            print("\n컬럼 목록:")
            for key in sorted(sample.keys()):
                value = sample[key]
                value_type = type(value).__name__
                print(f"  - {key:<30} ({value_type})")
        else:
            print("\n⚠️ 데이터가 없습니다")
            
    except Exception as e:
        print(f"\n❌ 오류: {e}")

def main():
    """메인 함수"""
    print("=" * 80)
    print("📊 테이블 스키마 확인")
    print("=" * 80)
    
    try:
        supabase = get_supabase_client()
        
        check_table_schema(supabase, 'price_history_btc')
        check_table_schema(supabase, 'price_history_eth')
        check_table_schema(supabase, 'price_history')
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

