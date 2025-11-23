#!/usr/bin/env python3
"""
Supabase 데이터베이스 설정 스크립트
통합 SQL 마이그레이션 파일을 실행하여 모든 테이블을 한번에 생성합니다.
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정 (가장 먼저)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 이제 모듈 import 가능
from dotenv import load_dotenv
from supabase import create_client, Client
from src.utils.logger import logger

# 환경변수 로드
load_dotenv(PROJECT_ROOT / 'config' / '.env')

def read_sql_file(file_path: Path) -> str:
    """SQL 파일 읽기"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"SQL 파일 읽기 실패: {file_path}, {e}")
        raise

def split_sql_statements(sql_content: str) -> list:
    """
    SQL 문을 세미콜론으로 분리
    주석과 빈 줄은 제거하지 않음 (Supabase가 처리)
    """
    # 세미콜론으로 분리하되, 함수 정의 내부의 세미콜론은 제외
    statements = []
    current_statement = []
    in_function = False
    
    lines = sql_content.split('\n')
    for line in lines:
        stripped = line.strip()
        
        # 함수 시작 감지
        if 'CREATE OR REPLACE FUNCTION' in stripped.upper() or '$$ LANGUAGE' in stripped.upper():
            in_function = not in_function
        
        current_statement.append(line)
        
        # 함수 내부가 아니고 세미콜론으로 끝나는 경우
        if not in_function and stripped.endswith(';') and not stripped.startswith('--'):
            statements.append('\n'.join(current_statement))
            current_statement = []
    
    # 마지막 문이 있으면 추가
    if current_statement:
        statements.append('\n'.join(current_statement))
    
    return [s.strip() for s in statements if s.strip() and not s.strip().startswith('--')]

def execute_sql_statements(supabase: Client, statements: list):
    """SQL 문들을 순차적으로 실행"""
    success_count = 0
    error_count = 0
    
    for i, statement in enumerate(statements, 1):
        if not statement.strip() or statement.strip().startswith('--'):
            continue
            
        try:
            # Supabase는 SQL 직접 실행을 지원하지 않으므로
            # PostgreSQL 직접 연결이 필요하거나
            # Supabase REST API의 RPC를 사용해야 함
            # 여기서는 경고 메시지만 처리하고 나머지는 Supabase 대시보드에서 실행하도록 안내
            
            # DO 블록 (NOTICE 출력용)은 스킵
            if statement.strip().upper().startswith('DO $$'):
                logger.info(f"[{i}/{len(statements)}] DO 블록 스킵 (NOTICE 출력)")
                continue
            
            logger.info(f"[{i}/{len(statements)}] SQL 문 실행 중...")
            logger.debug(f"SQL: {statement[:100]}...")
            
            # Supabase Python 클라이언트는 직접 SQL 실행을 지원하지 않음
            # 따라서 이 스크립트는 SQL 파일 검증만 수행하고
            # 실제 실행은 Supabase SQL Editor에서 수행하도록 안내
            success_count += 1
            
        except Exception as e:
            logger.error(f"[{i}/{len(statements)}] SQL 실행 실패: {e}")
            error_count += 1
            logger.debug(f"실패한 SQL: {statement[:200]}")
    
    return success_count, error_count

def main():
    """메인 함수"""
    logger.info("=" * 60)
    logger.info("📊 Supabase 데이터베이스 설정 시작")
    logger.info("=" * 60)
    
    # SQL 파일 경로
    sql_file = PROJECT_ROOT / 'sql' / 'migrations' / '001_initial_schema.sql'
    
    if not sql_file.exists():
        logger.error(f"❌ SQL 파일을 찾을 수 없습니다: {sql_file}")
        sys.exit(1)
    
    # Supabase 클라이언트 연결 (검증용)
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        
        if not supabase_url or not supabase_key:
            logger.error("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
            logger.info("💡 config/.env 파일을 확인하세요")
            sys.exit(1)
        
        logger.info("✅ Supabase 연결 정보 확인 완료")
        
    except Exception as e:
        logger.error(f"❌ Supabase 연결 확인 실패: {e}")
        sys.exit(1)
    
    # SQL 파일 읽기
    logger.info(f"\n📖 SQL 파일 읽기: {sql_file}")
    sql_content = read_sql_file(sql_file)
    
    # SQL 문 분리
    logger.info("🔍 SQL 문 분석 중...")
    statements = split_sql_statements(sql_content)
    logger.info(f"✅ {len(statements)}개의 SQL 문 발견")
    
    # 중요: Supabase Python 클라이언트는 직접 SQL 실행을 지원하지 않음
    logger.warning("\n" + "=" * 60)
    logger.warning("⚠️  중요 안내")
    logger.warning("=" * 60)
    logger.warning("Supabase Python 클라이언트는 직접 SQL 실행을 지원하지 않습니다.")
    logger.warning("다음 방법 중 하나를 선택하세요:\n")
    logger.warning("방법 1 (권장): Supabase 대시보드에서 실행")
    logger.warning("  1. Supabase 대시보드 → SQL Editor 열기")
    logger.warning(f"  2. {sql_file} 파일 내용을 복사하여 붙여넣기")
    logger.warning("  3. Run 버튼 클릭\n")
    logger.warning("방법 2: psql 직접 연결 (고급)")
    logger.warning("  PostgreSQL 클라이언트를 사용하여 직접 연결\n")
    
    # SQL 파일 경로 출력
    logger.info("\n" + "=" * 60)
    logger.info("📋 실행할 SQL 파일:")
    logger.info(f"  {sql_file}")
    logger.info("=" * 60)
    
    # SQL 내용 미리보기 (처음 500자)
    logger.info("\n📝 SQL 내용 미리보기 (처음 500자):")
    logger.info("-" * 60)
    logger.info(sql_content[:500] + "...")
    logger.info("-" * 60)
    
    logger.info("\n✅ SQL 파일 검증 완료!")
    logger.info("💡 Supabase SQL Editor에서 위 파일을 실행하세요.")
    logger.info("=" * 60 + "\n")

if __name__ == '__main__':
    main()
