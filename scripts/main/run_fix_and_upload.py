#!/usr/bin/env python3
"""
전체 프로세스 실행:
1. PRIMARY KEY 추가 (수동 실행 필요 안내)
2. CSV 데이터 업로드
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

def check_primary_key():
    """PRIMARY KEY가 있는지 확인"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    supabase = create_client(supabase_url, supabase_key)
    
    # 테이블 정보 조회 시도 (간접적으로 확인)
    try:
        # 중복 데이터가 있는지 확인 (PRIMARY KEY가 없으면 중복 가능)
        response = supabase.table('whale_address').select('id,chain_type').limit(1000).execute()
        
        # id와 chain_type 조합의 중복 확인
        seen = set()
        duplicates = []
        for record in response.data:
            key = (record.get('id'), record.get('chain_type'))
            if key in seen:
                duplicates.append(key)
            seen.add(key)
        
        if duplicates:
            print("⚠️  중복 데이터 발견 (PRIMARY KEY가 없을 가능성)")
            print(f"   중복된 (id, chain_type) 조합: {len(duplicates)}개")
            return False
        
        # upsert 테스트 (PRIMARY KEY가 있으면 정상 작동)
        test_record = {
            'id': '__TEST_PRIMARY_KEY_CHECK__',
            'chain_type': '__TEST__',
            'address': 'test'
        }
        
        try:
            # upsert 시도
            supabase.table('whale_address').upsert([test_record]).execute()
            # 테스트 레코드 삭제
            supabase.table('whale_address').delete().eq('id', '__TEST_PRIMARY_KEY_CHECK__').eq('chain_type', '__TEST__').execute()
            print("✅ PRIMARY KEY가 있는 것으로 보입니다 (upsert 테스트 성공)")
            return True
        except Exception as e:
            error_msg = str(e).lower()
            if 'primary key' in error_msg or 'unique constraint' in error_msg:
                print("❌ PRIMARY KEY가 없는 것으로 보입니다")
                return False
            else:
                print(f"⚠️  PRIMARY KEY 확인 중 오류: {e}")
                return False
                
    except Exception as e:
        print(f"⚠️  PRIMARY KEY 확인 중 오류: {e}")
        return False

def main():
    print("=" * 70)
    print("🔧 whale_address 테이블 문제 해결 및 데이터 업로드")
    print("=" * 70)
    
    # 1. PRIMARY KEY 확인
    print("\n[1단계] PRIMARY KEY 확인 중...")
    has_pk = check_primary_key()
    
    if not has_pk:
        print("\n" + "=" * 70)
        print("⚠️  PRIMARY KEY가 없습니다. 먼저 PRIMARY KEY를 추가해야 합니다.")
        print("=" * 70)
        print("\n📋 실행 방법:")
        print("   1. Supabase 대시보드 접속: https://supabase.com/dashboard")
        print("   2. 프로젝트 선택")
        print("   3. 좌측 메뉴에서 'SQL Editor' 클릭")
        print("   4. 'New query' 클릭")
        print("   5. 다음 파일의 SQL을 복사해서 실행:")
        print(f"      {PROJECT_ROOT / 'sql' / 'fix_whale_address_primary_key.sql'}")
        print("\n   또는 다음 명령어로 SQL 내용 확인:")
        print(f"   cat {PROJECT_ROOT / 'sql' / 'fix_whale_address_primary_key.sql'}")
        print("\n   SQL 실행 후, 이 스크립트를 다시 실행하세요.")
        return
    
    # 2. 데이터 업로드
    print("\n[2단계] CSV 데이터 업로드 중...")
    print("-" * 70)
    
    # update_whale_address_supabase.py 실행
    from update_whale_address_supabase import main as upload_main
    upload_main()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)



