#!/usr/bin/env python3
"""
중복 데이터 제거
PRIMARY KEY가 있으면 중복이 불가능하지만, 
PRIMARY KEY 추가 전에 이미 중복이 있었다면 제거 필요
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))

print("=" * 70)
print("🔧 중복 데이터 제거")
print("=" * 70)

print("\n⚠️  Supabase Python 클라이언트로는 직접 SQL을 실행할 수 없습니다.")
print("   Supabase 대시보드의 SQL Editor를 사용하세요.\n")

print("📋 실행 방법:")
print("   1. Supabase 대시보드 접속")
print("   2. 좌측 메뉴에서 'SQL Editor' 클릭")
print("   3. 'New query' 클릭")
print("   4. 다음 SQL을 복사해서 실행:\n")

sql_file = PROJECT_ROOT / 'remove_duplicates.sql'
with open(sql_file, 'r', encoding='utf-8') as f:
    sql = f.read()

print("-" * 70)
print(sql)
print("-" * 70)

print("\n✅ SQL 실행 후, final_statistics.py를 다시 실행하여 확인하세요.")



