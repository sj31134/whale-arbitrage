#!/usr/bin/env python3
"""
Supabase의 모든 테이블을 조회하는 스크립트
PostgreSQL의 pg_catalog를 통해 직접 조회 시도
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import requests
import json

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 환경변수 로드
load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_all_tables_via_rpc(supabase: Client, supabase_url: str, supabase_key: str):
    """RPC 함수를 통해 모든 테이블 조회"""
    # Supabase는 사용자 정의 RPC 함수를 만들 수 있음
    # 하지만 기본적으로 제공되는 함수는 없을 수 있음
    
    # 방법 1: pg_tables 시스템 카탈로그 조회 시도
    try:
        # Supabase REST API를 통해 pg_tables 조회
        api_url = f"{supabase_url}/rest/v1/rpc/get_all_tables"
        headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(api_url, headers=headers, json={}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                return [row.get('table_name') for row in data if row.get('table_name')]
    except Exception as e:
        print(f"⚠️  RPC 함수 조회 실패: {e}")
    
    return None

def get_all_tables_via_rest(supabase_url: str, supabase_key: str):
    """REST API를 통해 information_schema 조회"""
    tables = []
    
    # 방법 1: information_schema.tables 직접 조회
    try:
        api_url = f"{supabase_url}/rest/v1/information_schema.tables"
        headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}',
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        params = {
            'table_schema': 'eq.public',
            'table_type': 'eq.BASE TABLE',
            'select': 'table_name',
            'order': 'table_name.asc'
        }
        
        response = requests.get(api_url, headers=headers, params=params, timeout=10)
        print(f"📡 REST API 응답 코드: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                tables = [row['table_name'] for row in data if 'table_name' in row]
                print(f"✅ REST API를 통해 {len(tables)}개의 테이블 발견")
                return tables
            else:
                print(f"⚠️  응답 데이터 형식이 예상과 다릅니다: {type(data)}")
        else:
            print(f"⚠️  REST API 오류: {response.status_code}")
            print(f"   응답 내용: {response.text[:200]}")
    except Exception as e:
        print(f"⚠️  REST API 조회 실패: {e}")
    
    # 방법 2: pg_tables 시스템 뷰 조회 시도
    try:
        api_url = f"{supabase_url}/rest/v1/pg_tables"
        headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}',
            'Content-Type': 'application/json'
        }
        params = {
            'schemaname': 'eq.public',
            'select': 'tablename',
            'order': 'tablename.asc'
        }
        
        response = requests.get(api_url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                tables = [row['tablename'] for row in data if 'tablename' in row]
                print(f"✅ pg_tables를 통해 {len(tables)}개의 테이블 발견")
                return tables
    except Exception as e:
        print(f"⚠️  pg_tables 조회 실패: {e}")
    
    return tables

def brute_force_find_tables(supabase: Client, known_tables: list = None):
    """알려진 패턴으로 테이블 찾기"""
    if known_tables is None:
        known_tables = []
    
    # 매우 포괄적인 테이블 이름 패턴들
    all_patterns = [
        # 거래 관련
        'transactions', 'whale_transactions', 'internal_transactions',
        'token_transactions', 'native_transactions', 'erc20_transactions',
        'eth_transactions', 'matic_transactions',
        # 지갑 관련
        'wallets', 'wallet_labels', 'labels', 'addresses', 'address_labels',
        'wallet_addresses', 'known_addresses', 'tracked_addresses',
        'whale_wallets', 'tracked_wallets', 'monitored_addresses',
        # 가격 관련
        'prices', 'price_feeds', 'token_prices', 'price_history', 'price_updates',
        'crypto_prices', 'exchange_rates', 'market_data', 'price_data',
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
        'error_logs', 'access_logs', 'api_logs',
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
        'price_sources', 'data_sources',
        'backup', 'archives', 'historical_data',
        # 숫자 접미사가 있는 패턴
        'table_1', 'table_2', 'data_1', 'data_2',
    ]
    
    all_possible = list(set(known_tables + all_patterns))
    existing_tables = []
    
    print(f"🔍 {len(all_possible)}개의 가능한 테이블 이름을 확인 중...")
    
    for table_name in sorted(all_possible):
        try:
            response = supabase.table(table_name).select('*').limit(0).execute()
            existing_tables.append(table_name)
            print(f"   ✅ {table_name}")
        except Exception as e:
            error_msg = str(e).lower()
            if 'relation' in error_msg and 'does not exist' in error_msg:
                pass
            elif 'permission denied' in error_msg or 'pgrst' in error_msg:
                pass
    
    return existing_tables

def main():
    """메인 함수"""
    print("=" * 60)
    print("📊 Supabase 모든 테이블 조회")
    print("=" * 60)
    
    # 환경 변수 확인
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
        sys.exit(1)
    
    print(f"\n✅ Supabase URL: {supabase_url}")
    print(f"✅ Service Role Key: {supabase_key[:20]}...\n")
    
    # Supabase 클라이언트 생성
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Supabase 클라이언트 연결 성공\n")
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        sys.exit(1)
    
    # 방법 1: REST API를 통해 information_schema 조회
    print("=" * 60)
    print("방법 1: REST API를 통한 information_schema 조회")
    print("=" * 60)
    tables = get_all_tables_via_rest(supabase_url, supabase_key)
    
    if not tables:
        print("\n" + "=" * 60)
        print("방법 2: 알려진 패턴으로 테이블 찾기")
        print("=" * 60)
        known_tables = ['whale_transactions', 'internal_transactions', 'price_history']
        tables = brute_force_find_tables(supabase, known_tables)
    
    if tables:
        print(f"\n✅ 총 {len(tables)}개의 테이블 발견:")
        for i, table in enumerate(sorted(tables), 1):
            print(f"   {i:2d}. {table}")
    else:
        print("\n⚠️  테이블을 찾을 수 없습니다")
        print("💡 Supabase 대시보드에서 테이블 이름을 확인해주세요")

if __name__ == '__main__':
    main()



