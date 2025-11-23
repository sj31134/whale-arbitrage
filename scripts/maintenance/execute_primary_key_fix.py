#!/usr/bin/env python3
"""
whale_address 테이블에 PRIMARY KEY 추가 실행
Supabase REST API를 통해 SQL 실행 시도
"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

def execute_sql_via_rpc():
    """RPC를 통해 SQL 실행 시도"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    # SQL 파일 읽기
    sql_file = PROJECT_ROOT / 'sql' / 'fix_whale_address_primary_key.sql'
    
    if not sql_file.exists():
        print(f"❌ SQL 파일을 찾을 수 없습니다: {sql_file}")
        return False
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    print("=" * 70)
    print("🔧 whale_address 테이블에 PRIMARY KEY 추가")
    print("=" * 70)
    
    # Supabase REST API를 통한 SQL 실행은 직접 지원하지 않음
    # 대신 사용자에게 SQL Editor 사용 안내
    print("\n⚠️  Supabase Python 클라이언트로는 직접 SQL을 실행할 수 없습니다.")
    print("   Supabase 대시보드의 SQL Editor를 사용하세요.\n")
    
    print("📋 실행 방법:")
    print("   1. Supabase 대시보드 접속")
    print("   2. 좌측 메뉴에서 'SQL Editor' 클릭")
    print("   3. 'New query' 클릭")
    print("   4. 아래 SQL을 복사해서 붙여넣기")
    print("   5. 'Run' 버튼 클릭\n")
    
    print("-" * 70)
    print(sql)
    print("-" * 70)
    
    print("\n✅ SQL 실행 후, update_whale_address_supabase.py를 실행하세요.")
    
    return True

if __name__ == '__main__':
    try:
        execute_sql_via_rpc()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()



