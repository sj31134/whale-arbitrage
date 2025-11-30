#!/usr/bin/env python3
"""
Supabase에 누락된 테이블 생성
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# SQL 파일 읽기
sql_file = PROJECT_ROOT / 'sql' / 'create_project_tables.sql'
with open(sql_file, 'r') as f:
    sql_content = f.read()

# SQL 문을 세미콜론으로 분리
sql_statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]

print("=" * 80)
print("📊 Supabase 테이블 생성")
print("=" * 80)

# 각 SQL 문 실행
for i, sql in enumerate(sql_statements, 1):
    if not sql:
        continue
    try:
        # Supabase는 RPC를 통해 SQL 실행
        # 하지만 직접 SQL 실행은 제한적이므로, 테이블별로 확인 후 생성
        print(f"\n[{i}/{len(sql_statements)}] SQL 실행 중...")
        print(f"   {sql[:100]}...")
        
        # Supabase Python 클라이언트는 직접 SQL 실행을 지원하지 않음
        # 대신 Supabase Dashboard에서 SQL Editor를 사용하거나
        # psycopg2를 사용해야 함
        print("   ⚠️ Supabase Python 클라이언트는 직접 SQL 실행을 지원하지 않습니다.")
        print("   ℹ️ Supabase Dashboard의 SQL Editor에서 다음 SQL을 실행하세요:")
        print(f"\n{sql};")
        
    except Exception as e:
        print(f"   ❌ 오류: {e}")

print("\n" + "=" * 80)
print("✅ 테이블 생성 SQL 확인 완료")
print("=" * 80)
print("\n다음 단계:")
print("1. Supabase Dashboard (https://app.supabase.com) 접속")
print("2. SQL Editor 열기")
print("3. sql/create_project_tables.sql 파일의 내용을 복사하여 실행")

