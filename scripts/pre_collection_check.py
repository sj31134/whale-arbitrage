#!/usr/bin/env python3
"""
데이터 수집 실행 전 환경 검증 스크립트

모든 요구사항이 충족되었는지 확인:
- Supabase 연결
- API 키 설정
- 필요한 Python 패키지
- 데이터베이스 테이블 존재
- BSC 고래 주소 확인
- 디스크 공간
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 색상 코드
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_header():
    """헤더 출력"""
    print("=" * 70)
    print("🔍 데이터 수집 환경 검증")
    print("=" * 70)
    print()

def check_supabase_connection():
    """Supabase 연결 확인"""
    print("1. Supabase 연결 테스트...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print(f"   {RED}✗ 실패{RESET}: 환경 변수가 설정되지 않았습니다")
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)
        
        # 간단한 쿼리로 연결 테스트
        response = supabase.table('cryptocurrencies').select('id').limit(1).execute()
        
        print(f"   {GREEN}✓ 성공{RESET}: Supabase 연결 정상")
        return True
    except Exception as e:
        print(f"   {RED}✗ 실패{RESET}: {e}")
        return False

def check_api_keys():
    """API 키 확인"""
    print("\n2. API 키 확인...")
    
    etherscan_key = os.getenv('ETHERSCAN_API_KEY')
    
    if etherscan_key:
        masked_key = etherscan_key[:10] + '...' if len(etherscan_key) > 10 else etherscan_key
        print(f"   {GREEN}✓ ETHERSCAN_API_KEY{RESET}: {masked_key}")
        return True
    else:
        print(f"   {RED}✗ ETHERSCAN_API_KEY{RESET}: 설정되지 않음")
        return False

def check_python_packages():
    """필요한 Python 패키지 확인"""
    print("\n3. Python 패키지 확인...")
    
    packages = {
        'supabase': 'supabase',
        'requests': 'requests',
        'beautifulsoup4': 'bs4',
        'lxml': 'lxml',
        'python-dotenv': 'dotenv'
    }
    
    all_installed = True
    for package_name, import_name in packages.items():
        try:
            __import__(import_name)
            print(f"   {GREEN}✓ {package_name}{RESET}")
        except ImportError:
            print(f"   {RED}✗ {package_name}{RESET}: 설치 필요")
            all_installed = False
    
    if not all_installed:
        print(f"\n   설치 명령어: pip install beautifulsoup4 lxml")
    
    return all_installed

def check_database_tables():
    """데이터베이스 테이블 확인"""
    print("\n4. 데이터베이스 테이블 확인...")
    
    try:
        from supabase import create_client
        supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
        
        tables = [
            'cryptocurrencies',
            'price_history',
            'whale_address',
            'whale_transactions'
        ]
        
        all_exist = True
        for table in tables:
            try:
                response = supabase.table(table).select('*').limit(1).execute()
                print(f"   {GREEN}✓ {table}{RESET}")
            except Exception as e:
                print(f"   {RED}✗ {table}{RESET}: {e}")
                all_exist = False
        
        return all_exist
        
    except Exception as e:
        print(f"   {RED}✗ 실패{RESET}: {e}")
        return False

def check_bsc_addresses():
    """BSC 고래 주소 확인"""
    print("\n5. BSC 고래 주소 확인...")
    
    try:
        from supabase import create_client
        supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
        
        response = supabase.table('whale_address')\
            .select('*', count='exact')\
            .eq('chain_type', 'BSC')\
            .execute()
        
        count = response.count if hasattr(response, 'count') else len(response.data) if response.data else 0
        
        if count > 0:
            print(f"   {GREEN}✓ BSC 주소{RESET}: {count}개")
            return True
        else:
            print(f"   {YELLOW}⚠ BSC 주소{RESET}: 0개 (수집할 주소가 없습니다)")
            return False
        
    except Exception as e:
        print(f"   {RED}✗ 실패{RESET}: {e}")
        return False

def check_btc_addresses():
    """BTC 고래 주소 확인"""
    print("\n6. BTC 고래 주소 확인...")
    
    try:
        from supabase import create_client
        supabase = create_client(
            os.getenv('SUPABASE_URL'),
            os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        )
        
        response = supabase.table('whale_address')\
            .select('*', count='exact')\
            .eq('chain_type', 'BTC')\
            .execute()
        
        count = response.count if hasattr(response, 'count') else len(response.data) if response.data else 0
        
        if count > 0:
            print(f"   {GREEN}✓ BTC 주소{RESET}: {count}개")
            return True
        else:
            print(f"   {YELLOW}⚠ BTC 주소{RESET}: 0개 (수집할 주소가 없습니다)")
            return False
        
    except Exception as e:
        print(f"   {RED}✗ 실패{RESET}: {e}")
        return False

def check_checkpoint_files():
    """체크포인트 파일 확인"""
    print("\n7. 체크포인트 파일 확인...")
    
    checkpoint_file = PROJECT_ROOT / 'collection_checkpoint.json'
    
    if checkpoint_file.exists():
        print(f"   {GREEN}✓ 기존 체크포인트 발견{RESET}: {checkpoint_file}")
        print(f"   재개 모드로 실행됩니다")
        return True
    else:
        print(f"   {YELLOW}⚠ 체크포인트 없음{RESET}: 처음부터 시작합니다")
        return True

def check_disk_space():
    """디스크 공간 확인"""
    print("\n8. 디스크 공간 확인...")
    
    try:
        stats = shutil.disk_usage(PROJECT_ROOT)
        free_gb = stats.free / (1024 ** 3)
        
        if free_gb > 5:
            print(f"   {GREEN}✓ 여유 공간{RESET}: {free_gb:.2f} GB")
            return True
        elif free_gb > 1:
            print(f"   {YELLOW}⚠ 여유 공간{RESET}: {free_gb:.2f} GB (최소 요구사항)")
            return True
        else:
            print(f"   {RED}✗ 여유 공간{RESET}: {free_gb:.2f} GB (부족)")
            return False
        
    except Exception as e:
        print(f"   {YELLOW}⚠ 확인 실패{RESET}: {e}")
        return True

def check_collection_scripts():
    """수집 스크립트 존재 확인"""
    print("\n9. 수집 스크립트 확인...")
    
    scripts = [
        'collect_price_history_hourly.py',
        'collect_btc_whale_transactions.py',
        'scripts/collectors/bsc_hybrid_collector.py',
        'run_parallel_collection.py'
    ]
    
    all_exist = True
    for script in scripts:
        script_path = PROJECT_ROOT / script
        if script_path.exists():
            print(f"   {GREEN}✓ {script}{RESET}")
        else:
            print(f"   {RED}✗ {script}{RESET}: 파일 없음")
            all_exist = False
    
    return all_exist

def print_summary(results):
    """결과 요약"""
    print("\n" + "=" * 70)
    print("📋 검증 결과 요약")
    print("=" * 70)
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    failed = total - passed
    
    print(f"\n전체: {total}개 항목")
    print(f"성공: {GREEN}{passed}개{RESET}")
    print(f"실패: {RED}{failed}개{RESET}")
    
    if failed == 0:
        print(f"\n{GREEN}✓ 모든 검증 통과! 데이터 수집을 시작할 수 있습니다.{RESET}")
        print("\n다음 명령어로 수집을 시작하세요:")
        print("  python3 run_parallel_collection.py")
        return True
    else:
        print(f"\n{RED}✗ 일부 검증 실패. 위의 문제를 해결 후 다시 시도하세요.{RESET}")
        return False

def main():
    """메인 함수"""
    print_header()
    
    results = {
        'supabase': check_supabase_connection(),
        'api_keys': check_api_keys(),
        'packages': check_python_packages(),
        'tables': check_database_tables(),
        'bsc_addresses': check_bsc_addresses(),
        'btc_addresses': check_btc_addresses(),
        'checkpoint': check_checkpoint_files(),
        'disk_space': check_disk_space(),
        'scripts': check_collection_scripts()
    }
    
    success = print_summary(results)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())

