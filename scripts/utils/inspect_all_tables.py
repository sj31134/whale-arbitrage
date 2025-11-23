#!/usr/bin/env python3
"""
Supabase 데이터베이스의 모든 테이블을 조사하는 스크립트
사용자가 제공한 테이블 이름 목록을 사용하거나 자동으로 찾습니다.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import pandas as pd
import requests

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 환경변수 로드
load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_table_info(supabase: Client, table_name: str) -> dict:
    """테이블 정보 조회 (샘플 데이터와 통계)"""
    try:
        # 샘플 데이터 조회 (1건)
        sample_response = supabase.table(table_name).select('*').limit(1).execute()
        
        # 전체 행 수 조회
        count_response = supabase.table(table_name).select('*', count='exact').execute()
        total_count = count_response.count if hasattr(count_response, 'count') else None
        
        # 컬럼 정보는 샘플 데이터의 키에서 추출
        columns = []
        if sample_response.data and len(sample_response.data) > 0:
            columns = list(sample_response.data[0].keys())
        
        return {
            'table_name': table_name,
            'total_rows': total_count,
            'columns': columns,
            'sample_data': sample_response.data[0] if sample_response.data else None
        }
    except Exception as e:
        return {
            'table_name': table_name,
            'error': str(e)
        }

def check_table_exists(supabase: Client, table_name: str) -> bool:
    """테이블 존재 여부 확인"""
    try:
        response = supabase.table(table_name).select('*').limit(0).execute()
        return True
    except Exception as e:
        error_msg = str(e).lower()
        if 'relation' in error_msg and 'does not exist' in error_msg:
            return False
        # 다른 오류는 테이블이 존재할 수도 있음
        return True

def main():
    """메인 함수"""
    print("=" * 60)
    print("📊 Supabase 데이터베이스 테이블 조사")
    print("=" * 60)
    
    # 환경 변수 확인
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
        print("💡 config/.env 파일을 확인하세요")
        sys.exit(1)
    
    print(f"\n✅ Supabase URL: {supabase_url[:30]}...")
    print(f"✅ Service Role Key: {supabase_key[:20]}...\n")
    
    # Supabase 클라이언트 생성
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Supabase 클라이언트 연결 성공\n")
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        sys.exit(1)
    
    # 사용자에게 테이블 이름 목록 입력 요청
    print("=" * 60)
    print("📝 테이블 이름 입력")
    print("=" * 60)
    print("Supabase에 있는 12개의 테이블 이름을 입력해주세요.")
    print("(쉼표로 구분하거나, 한 줄에 하나씩 입력)")
    print("예: whale_transactions, internal_transactions, price_history, ...")
    print("\n입력 (Enter로 완료):")
    
    user_input = input().strip()
    
    if user_input:
        # 쉼표로 구분된 입력 처리
        if ',' in user_input:
            table_names = [name.strip() for name in user_input.split(',')]
        else:
            # 한 줄에 하나씩 입력된 경우
            table_names = [name.strip() for name in user_input.split('\n') if name.strip()]
    else:
        # 입력이 없으면 자동으로 찾기 시도
        print("\n💡 자동으로 테이블을 찾는 중...")
        table_names = []
        
        # 알려진 테이블들
        known_tables = [
            'whale_transactions',
            'internal_transactions',
            'price_history',
        ]
        
        # 더 많은 패턴 시도
        common_patterns = [
            'transactions', 'whale_transactions', 'internal_transactions',
            'wallets', 'wallet_labels', 'labels', 'addresses',
            'prices', 'price_feeds', 'token_prices', 'price_history',
            'blocks', 'contracts', 'alerts', 'users', 'logs', 'stats',
            'sync', 'metadata', 'config', 'tokens', 'coins',
        ]
        
        all_possible = list(set(known_tables + common_patterns))
        
        for table_name in sorted(all_possible):
            if check_table_exists(supabase, table_name):
                table_names.append(table_name)
                print(f"   ✅ {table_name}")
    
    if not table_names:
        print("⚠️  테이블을 찾을 수 없습니다")
        sys.exit(1)
    
    print(f"\n✅ {len(table_names)}개의 테이블을 조사합니다: {', '.join(table_names)}\n")
    
    # 각 테이블 정보 조회
    for i, table_name in enumerate(table_names, 1):
        print("=" * 60)
        print(f"📋 테이블 {i}/{len(table_names)}: {table_name}")
        print("=" * 60)
        
        table_info = get_table_info(supabase, table_name)
        
        if 'error' in table_info:
            print(f"❌ 오류: {table_info['error']}\n")
            continue
        
        # 테이블 통계
        print(f"\n📊 테이블 통계:")
        if table_info['total_rows'] is not None:
            print(f"   총 행 수: {table_info['total_rows']:,}건")
        else:
            print(f"   총 행 수: 확인 불가")
        
        # 컬럼 정보
        print(f"\n📝 컬럼 정보 ({len(table_info['columns'])}개):")
        for col in table_info['columns']:
            print(f"   - {col}")
        
        # 샘플 데이터
        if table_info['sample_data']:
            print(f"\n🔍 샘플 데이터 (1건):")
            sample = table_info['sample_data']
            for key, value in list(sample.items())[:10]:  # 처음 10개만 표시
                # 값이 너무 길면 잘라서 표시
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + "..."
                print(f"   {key}: {value}")
            if len(sample) > 10:
                print(f"   ... (총 {len(sample)}개 필드)")
        
        print()
    
    # 요약
    print("=" * 60)
    print("📊 조사 완료")
    print("=" * 60)
    print(f"총 {len(table_names)}개의 테이블을 조사했습니다:")
    for table_name in table_names:
        print(f"  - {table_name}")

if __name__ == '__main__':
    main()



