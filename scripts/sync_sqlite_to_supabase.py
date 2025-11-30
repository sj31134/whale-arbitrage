#!/usr/bin/env python3
"""
SQLite project.db 데이터를 Supabase로 업로드
"""

import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import time
import pandas as pd
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

DB_PATH = PROJECT_ROOT / 'data' / 'project.db'


def upload_table(table_name, column_mapping=None):
    """SQLite 테이블을 Supabase로 업로드"""
    print(f"\n{'='*60}")
    print(f"📤 {table_name} 업로드")
    print("=" * 60)
    
    # 테이블 존재 여부 확인
    try:
        # 빈 쿼리로 테이블 존재 여부 확인
        supabase.table(table_name).select("*").limit(0).execute()
    except Exception as e:
        if 'not found' in str(e).lower() or 'schema cache' in str(e).lower():
            print(f"   ⚠️ 테이블 '{table_name}'이 Supabase에 존재하지 않습니다.")
            print(f"   ℹ️ Supabase Dashboard에서 다음 SQL을 실행하세요:")
            print(f"      sql/create_project_tables.sql 파일 참고")
            return 0
        else:
            # 다른 오류는 무시하고 계속 진행
            pass
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 데이터 조회
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    if not rows:
        print(f"   ⚠️ 데이터 없음")
        conn.close()
        return 0
    
    print(f"   총 {len(rows):,}건")
    
    # 컬럼명 가져오기
    columns = [desc[0] for desc in cursor.description]
    
    # 배치 업로드
    batch_size = 100
    uploaded = 0
    
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        
        # dict 변환 및 데이터 타입 처리
        data = []
        for row in batch:
            row_dict = dict(row)
            # 데이터 타입 변환
            for k, v in row_dict.items():
                if v is None:
                    row_dict[k] = None
                elif isinstance(v, datetime):
                    # datetime을 ISO 형식 문자열로 변환
                    row_dict[k] = v.isoformat()
                elif isinstance(v, str) and k in ['date', 'created_at']:
                    # 날짜 문자열 정규화 (UTC+0:00)
                    try:
                        dt = pd.to_datetime(v, utc=True)
                        row_dict[k] = dt.strftime('%Y-%m-%d') if k == 'date' else dt.isoformat()
                    except:
                        pass
                elif isinstance(v, (int, float)):
                    # NaN 처리
                    if pd.isna(v):
                        row_dict[k] = None
                    else:
                        row_dict[k] = v
            data.append(row_dict)
        
        try:
            # upsert 사용 (중복 시 업데이트)
            # on_conflict 파라미터로 unique constraint 지정
            # 테이블별 unique key 추정
            if table_name in ['binance_futures_metrics', 'futures_extended_metrics']:
                # date, symbol이 unique key
                result = supabase.table(table_name).upsert(data, on_conflict='date,symbol').execute()
            elif table_name in ['whale_daily_stats', 'whale_weekly_stats']:
                # date, coin_symbol이 unique key
                result = supabase.table(table_name).upsert(data, on_conflict='date,coin_symbol').execute()
            elif table_name == 'bitinfocharts_whale_weekly':
                # coin, week_end_date가 unique key
                result = supabase.table(table_name).upsert(data, on_conflict='coin,week_end_date').execute()
            elif 'date' in columns and 'symbol' in columns:
                result = supabase.table(table_name).upsert(data, on_conflict='date,symbol').execute()
            elif 'date' in columns:
                result = supabase.table(table_name).upsert(data, on_conflict='date').execute()
            else:
                result = supabase.table(table_name).upsert(data).execute()
            uploaded += len(batch)
        except Exception as e:
            error_msg = str(e)
            # 중복 키 오류는 이미 존재하는 데이터이므로 건너뛰기
            if 'duplicate' in error_msg.lower() or 'unique' in error_msg.lower():
                print(f"   ℹ️ 배치 {i//batch_size + 1}: 일부 데이터가 이미 존재 (건너뛰기)")
                # 개별 upsert 시도 (중복은 무시)
                for row_dict in data:
                    try:
                        if table_name in ['binance_futures_metrics', 'futures_extended_metrics']:
                            supabase.table(table_name).upsert(row_dict, on_conflict='date,symbol').execute()
                        elif table_name in ['whale_daily_stats', 'whale_weekly_stats']:
                            supabase.table(table_name).upsert(row_dict, on_conflict='date,coin_symbol').execute()
                        elif table_name == 'bitinfocharts_whale_weekly':
                            supabase.table(table_name).upsert(row_dict, on_conflict='coin,week_end_date').execute()
                        elif 'date' in row_dict and 'symbol' in row_dict:
                            supabase.table(table_name).upsert(row_dict, on_conflict='date,symbol').execute()
                        elif 'date' in row_dict:
                            supabase.table(table_name).upsert(row_dict, on_conflict='date').execute()
                        else:
                            supabase.table(table_name).upsert(row_dict).execute()
                        uploaded += 1
                    except Exception as e2:
                        # 중복이면 건너뛰기
                        if 'duplicate' not in str(e2).lower() and 'unique' not in str(e2).lower():
                            print(f"      ⚠️ 개별 upsert 오류: {str(e2)[:80]}")
            else:
                print(f"   ⚠️ 배치 {i//batch_size + 1} 오류: {error_msg[:100]}")
                # 개별 upsert 시도
                for row_dict in data:
                    try:
                        if table_name in ['binance_futures_metrics', 'futures_extended_metrics']:
                            supabase.table(table_name).upsert(row_dict, on_conflict='date,symbol').execute()
                        elif table_name in ['whale_daily_stats', 'whale_weekly_stats']:
                            supabase.table(table_name).upsert(row_dict, on_conflict='date,coin_symbol').execute()
                        elif table_name == 'bitinfocharts_whale_weekly':
                            supabase.table(table_name).upsert(row_dict, on_conflict='coin,week_end_date').execute()
                        elif 'date' in row_dict and 'symbol' in row_dict:
                            supabase.table(table_name).upsert(row_dict, on_conflict='date,symbol').execute()
                        elif 'date' in row_dict:
                            supabase.table(table_name).upsert(row_dict, on_conflict='date').execute()
                        else:
                            supabase.table(table_name).upsert(row_dict).execute()
                        uploaded += 1
                    except Exception as e2:
                        if 'duplicate' not in str(e2).lower() and 'unique' not in str(e2).lower():
                            print(f"      ⚠️ 개별 upsert 오류: {str(e2)[:80]}")
        
        if (i // batch_size + 1) % 10 == 0:
            print(f"   진행: {uploaded:,}/{len(rows):,}건")
        
        time.sleep(0.05)
    
    conn.close()
    print(f"   ✅ {uploaded:,}건 업로드 완료")
    return uploaded


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='SQLite → Supabase 데이터 동기화')
    parser.add_argument('--table', type=str, help='특정 테이블만 동기화 (예: binance_futures_metrics)')
    parser.add_argument('--skip-existing', action='store_true', help='기존 데이터 건너뛰기 (테스트용)')
    args = parser.parse_args()
    
    print("=" * 80)
    print("📊 SQLite → Supabase 데이터 동기화")
    print("=" * 80)
    
    # 모든 테이블 목록 (SQLite에서 자동 조회)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
    all_tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"\n발견된 테이블: {len(all_tables)}개")
    for table in all_tables:
        print(f"  - {table}")
    
    # 동기화할 테이블 목록 결정
    if args.table:
        if args.table in all_tables:
            tables_to_sync = [args.table]
            print(f"\n✅ 특정 테이블만 동기화: {args.table}")
        else:
            print(f"\n❌ 테이블 '{args.table}'을 찾을 수 없습니다.")
            return
    else:
        # 동기화할 테이블 목록 (우선순위 순서)
        priority_tables = [
            'binance_futures_metrics',
            'futures_extended_metrics',
            'whale_daily_stats',
            'whale_weekly_stats',
            'binance_spot_daily',
            'binance_spot_weekly',
            'bybit_spot_daily',
            'bitget_spot_daily',
            'bitinfocharts_whale',
            'bitinfocharts_whale_weekly',
            'exchange_rate',
            'upbit_daily',
        ]
        
        # 우선순위 테이블 + 나머지 테이블
        tables_to_sync = []
        for table in priority_tables:
            if table in all_tables:
                tables_to_sync.append(table)
        
        # 나머지 테이블 추가
        for table in all_tables:
            if table not in tables_to_sync:
                tables_to_sync.append(table)
        
        print(f"\n동기화 대상: {len(tables_to_sync)}개 테이블")
    
    total_uploaded = 0
    
    for table in tables_to_sync:
        try:
            cnt = upload_table(table)
            total_uploaded += cnt
        except Exception as e:
            print(f"   ❌ {table} 오류: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print(f"🎉 총 {total_uploaded:,}건 업로드 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()



