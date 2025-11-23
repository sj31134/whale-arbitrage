#!/usr/bin/env python3
"""
Supabase 데이터베이스 테이블 조사 스크립트
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

def list_all_tables(supabase: Client, supabase_url: str, supabase_key: str) -> list:
    """
    Supabase에서 사용 가능한 모든 테이블 목록 조회
    여러 방법을 시도하여 모든 테이블을 찾음
    """
    existing_tables = []
    
    # 방법 1: REST API를 통해 information_schema 조회 시도
    try:
        # Supabase REST API 엔드포인트
        api_url = f"{supabase_url}/rest/v1/information_schema.tables"
        headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}',
            'Content-Type': 'application/json'
        }
        params = {
            'table_schema': 'eq.public',
            'table_type': 'eq.BASE TABLE',
            'select': 'table_name',
            'order': 'table_name'
        }
        
        response = requests.get(api_url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                tables = [row['table_name'] for row in data]
                print(f"✅ REST API를 통해 {len(tables)}개의 테이블 발견")
                return tables
    except Exception as e:
        print(f"⚠️  REST API 조회 실패: {e}")
    
    # 방법 2: 사용자 입력으로 테이블 이름 받기 (대화형 모드)
    # 방법 3: 알려진 테이블들과 일반적인 패턴 시도
    print("💡 알려진 테이블과 일반적인 패턴을 시도합니다...")
    
    # 알려진 테이블들
    known_tables = [
        'whale_transactions',
        'internal_transactions',
    ]
    
    # 일반적인 테이블 이름 패턴들 (더 많은 패턴 추가)
    common_patterns = [
        # 거래 관련
        'transactions', 'whale_transactions', 'internal_transactions',
        'token_transactions', 'native_transactions', 'erc20_transactions',
        # 지갑 관련
        'wallets', 'wallet_labels', 'labels', 'addresses', 'address_labels',
        'wallet_addresses', 'known_addresses', 'tracked_addresses',
        # 가격 관련
        'prices', 'price_feeds', 'token_prices', 'price_history', 'price_updates',
        'crypto_prices', 'exchange_rates', 'market_data',
        # 블록 관련
        'blocks', 'block_data', 'block_info', 'blockchain_data',
        # 컨트랙트 관련
        'contracts', 'contract_data', 'contract_info', 'smart_contracts',
        'token_contracts', 'contract_addresses',
        # 알림 관련
        'alerts', 'notifications', 'alert_history', 'alert_logs',
        # 사용자 관련
        'users', 'accounts', 'user_settings', 'user_preferences',
        # 로그 관련
        'logs', 'events', 'event_logs', 'transaction_logs', 'system_logs',
        'error_logs', 'access_logs',
        # 통계 관련
        'stats', 'statistics', 'daily_stats', 'hourly_stats', 'weekly_stats',
        'monthly_stats', 'aggregated_stats',
        # 동기화 관련
        'sync', 'sync_status', 'sync_logs', 'sync_history',
        # 기타
        'metadata', 'config', 'settings', 'cache', 'tokens', 'coins',
        'exchanges', 'markets', 'pairs', 'trading_pairs',
        # 추가 패턴들
        'function_signatures', 'method_signatures', 'abi_data',
        'github_data', 'dataset_sync', 'external_data',
        'whale_wallets', 'tracked_wallets', 'monitored_addresses',
        'price_sources', 'data_sources', 'api_logs',
        'backup', 'archives', 'historical_data',
    ]
    
    # 모든 가능한 테이블 이름 시도
    all_possible_tables = list(set(known_tables + common_patterns))
    
    print(f"🔍 {len(all_possible_tables)}개의 가능한 테이블 이름을 확인 중...")
    
    for table_name in sorted(all_possible_tables):
        try:
            # 테이블 존재 여부 확인 (빈 쿼리로 시도)
            response = supabase.table(table_name).select('*').limit(0).execute()
            existing_tables.append(table_name)
            print(f"   ✅ {table_name}")
        except Exception as e:
            # 테이블이 없거나 접근 권한이 없는 경우
            error_msg = str(e).lower()
            if 'relation' in error_msg and 'does not exist' in error_msg:
                # 테이블이 존재하지 않음
                pass
            elif 'permission denied' in error_msg or 'pgrst' in error_msg:
                # 권한 문제 또는 PostgREST 오류
                pass
            else:
                # 다른 오류 - 테이블이 존재할 수도 있음
                # 하지만 확실하지 않으므로 추가하지 않음
                pass
    
    return existing_tables

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
    
    # 테이블 목록 조회
    print("🔍 테이블 목록 조회 중...\n")
    tables = list_all_tables(supabase, supabase_url, supabase_key)
    
    if not tables:
        print("⚠️  접근 가능한 테이블을 찾을 수 없습니다")
        print("💡 알려진 테이블들을 직접 확인합니다...\n")
        tables = ['whale_transactions', 'internal_transactions']
    
    print(f"✅ {len(tables)}개의 테이블 발견: {', '.join(tables)}\n")
    
    # 각 테이블 정보 조회
    for i, table_name in enumerate(tables, 1):
        print("=" * 60)
        print(f"📋 테이블 {i}/{len(tables)}: {table_name}")
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
    print(f"총 {len(tables)}개의 테이블을 조사했습니다:")
    for table_name in tables:
        print(f"  - {table_name}")

if __name__ == '__main__':
    main()

