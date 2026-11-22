#!/usr/bin/env python3
"""
whale_address 테이블에 PRIMARY KEY 추가
Supabase SQL Editor에서 직접 실행하거나, 이 스크립트를 통해 실행
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / 'config' / '.env')

def add_primary_key():
    """whale_address 테이블에 PRIMARY KEY 추가"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    supabase = create_client(supabase_url, supabase_key)
    
    print("=" * 70)
    print("🔧 whale_address 테이블에 PRIMARY KEY 추가")
    print("=" * 70)
    
    # SQL 파일 읽기
    sql_file = PROJECT_ROOT / 'sql' / 'schema' / 'fix_whale_address_primary_key.sql'
    
    if not sql_file.exists():
        print(f"❌ SQL 파일을 찾을 수 없습니다: {sql_file}")
        return False
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    print("\n⚠️  주의: Supabase Python 클라이언트로는 직접 SQL을 실행하기 어렵습니다.")
    print("   다음 방법 중 하나를 사용하세요:\n")
    print("   방법 1: Supabase 대시보드 SQL Editor에서 실행")
    print(f"   1. Supabase 대시보드 → SQL Editor 열기")
    print(f"   2. 다음 SQL을 복사해서 실행:\n")
    print("-" * 70)
    print(sql)
    print("-" * 70)
    
    print("\n   방법 2: psql 또는 다른 PostgreSQL 클라이언트 사용")
    print(f"   psql -h [host] -U [user] -d [database] -f {sql_file}")
    
    return True

if __name__ == '__main__':
    try:
        add_primary_key()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()



