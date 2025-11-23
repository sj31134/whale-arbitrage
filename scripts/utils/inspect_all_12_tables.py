#!/usr/bin/env python3
"""
Supabase 데이터베이스의 모든 12개 테이블 조사 스크립트
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import pandas as pd

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 환경변수 로드
load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 모든 테이블 목록 (스키마에서 확인)
ALL_TABLES = [
    'cryptocurrencies',
    'influencer',
    'internal_transactions',
    'market_cap_data',
    'market_data_daily',
    'news_sentiment',
    'prediction_accuracy',
    'price_history',
    'reddit_sentiment',
    'social_data',
    'whale_address',
    'whale_transactions',
]

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
        elif sample_response.data is not None and len(sample_response.data) == 0:
            # 테이블이 비어있는 경우, 스키마에서 컬럼 정보를 가져올 수 없음
            columns = ["테이블이 비어있어 컬럼 정보를 확인할 수 없습니다"]
        
        return {
            'table_name': table_name,
            'total_rows': total_count,
            'columns': columns,
            'sample_data': sample_response.data[0] if sample_response.data and len(sample_response.data) > 0 else None
        }
    except Exception as e:
        return {
            'table_name': table_name,
            'error': str(e)
        }

def main():
    """메인 함수"""
    print("=" * 70)
    print("📊 Supabase 데이터베이스 전체 테이블 조사 (12개 테이블)")
    print("=" * 70)
    
    # 환경 변수 확인
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
        print("💡 config/.env 파일을 확인하세요")
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
    
    print(f"🔍 총 {len(ALL_TABLES)}개의 테이블을 조사합니다...\n")
    
    # 각 테이블 정보 조회
    table_summaries = []
    
    for i, table_name in enumerate(ALL_TABLES, 1):
        print("=" * 70)
        print(f"📋 테이블 {i}/{len(ALL_TABLES)}: {table_name}")
        print("=" * 70)
        
        table_info = get_table_info(supabase, table_name)
        
        if 'error' in table_info:
            print(f"❌ 오류: {table_info['error']}\n")
            table_summaries.append({
                'table_name': table_name,
                'status': '오류',
                'rows': 0,
                'columns': 0
            })
            continue
        
        # 테이블 통계
        print(f"\n📊 테이블 통계:")
        if table_info['total_rows'] is not None:
            print(f"   총 행 수: {table_info['total_rows']:,}건")
            row_count = table_info['total_rows']
        else:
            print(f"   총 행 수: 확인 불가")
            row_count = 0
        
        # 컬럼 정보
        if isinstance(table_info['columns'], list) and len(table_info['columns']) > 0:
            print(f"\n📝 컬럼 정보 ({len(table_info['columns'])}개):")
            for col in table_info['columns']:
                print(f"   - {col}")
            col_count = len(table_info['columns'])
        else:
            print(f"\n📝 컬럼 정보: 확인 불가 (테이블이 비어있거나 접근 불가)")
            col_count = 0
        
        # 샘플 데이터
        if table_info['sample_data']:
            print(f"\n🔍 샘플 데이터 (1건):")
            sample = table_info['sample_data']
            display_count = min(10, len(sample))
            for key, value in list(sample.items())[:display_count]:
                # 값이 너무 길면 잘라서 표시
                if isinstance(value, str) and len(value) > 60:
                    value = value[:60] + "..."
                elif value is None:
                    value = "NULL"
                print(f"   {key}: {value}")
            if len(sample) > display_count:
                print(f"   ... (총 {len(sample)}개 필드)")
        
        table_summaries.append({
            'table_name': table_name,
            'status': '성공',
            'rows': row_count,
            'columns': col_count
        })
        
        print()
    
    # 전체 요약
    print("=" * 70)
    print("📊 전체 테이블 요약")
    print("=" * 70)
    print(f"{'테이블 이름':<30} {'상태':<10} {'행 수':>15} {'컬럼 수':>10}")
    print("-" * 70)
    
    total_rows = 0
    for summary in table_summaries:
        rows_str = f"{summary['rows']:,}" if summary['rows'] > 0 else "N/A"
        cols_str = f"{summary['columns']}" if summary['columns'] > 0 else "N/A"
        print(f"{summary['table_name']:<30} {summary['status']:<10} {rows_str:>15} {cols_str:>10}")
        if summary['rows'] > 0:
            total_rows += summary['rows']
    
    print("-" * 70)
    print(f"{'총계':<30} {'':<10} {total_rows:>15,} {'':>10}")
    print("=" * 70)
    print(f"\n✅ 총 {len(ALL_TABLES)}개의 테이블 조사 완료!")

if __name__ == '__main__':
    main()



