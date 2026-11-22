import os
from supabase import create_client
from dotenv import load_dotenv
from pathlib import Path

# Load env
load_dotenv(Path.cwd() / 'config' / '.env')

# Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

# Read SQL file
sql_path = Path('sql/rpc/update_post_process_rpc.sql')
with open(sql_path, 'r') as f:
    sql_content = f.read()

print("=" * 80)
print("🛠️ RPC 함수 생성 중: update_post_process_labels")
print("=" * 80)

try:
    # Execute SQL using Supabase REST API (rpc call not possible for DDL, need workaround or use direct connection)
    # Supabase-py client doesn't support direct SQL execution easily without specific setup.
    # However, we can try using the `pg` driver or similar if available, OR
    # we can use a predefined function if one exists.
    
    # BUT, wait. Supabase-py usually interacts via PostgREST which cannot execute DDL (CREATE FUNCTION).
    # We need to use the SQL Editor in the dashboard OR a specific "exec_sql" function if we created one earlier.
    
    # Let's check if we have an `exec_sql` function.
    
    try:
        response = supabase.rpc('exec_sql', {'query': sql_content}).execute()
        print("✅ exec_sql 함수를 통해 생성 성공!")
    except Exception as e:
        print(f"⚠️ exec_sql 시도 실패: {e}")
        print("\n🚨 중요: Python 클라이언트(PostgREST)로는 'CREATE FUNCTION' 같은 DDL을 직접 실행할 수 없습니다.")
        print("   따라서 이 SQL을 Supabase 대시보드의 SQL Editor에서 직접 실행해주셔야 합니다.")
        print(f"\n   파일 경로: {sql_path}")
        print("\n   [SQL 내용 복사]")
        print("-" * 20)
        print(sql_content[:500] + "\n... (생략) ...")
        print("-" * 20)

except Exception as e:
    print(f"❌ 오류 발생: {e}")

