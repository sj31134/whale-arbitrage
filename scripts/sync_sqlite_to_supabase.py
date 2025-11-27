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
        
        # dict 변환
        data = []
        for row in batch:
            row_dict = dict(row)
            # None 값 처리
            for k, v in row_dict.items():
                if v is None:
                    row_dict[k] = None
            data.append(row_dict)
        
        try:
            # upsert 사용 (중복 시 업데이트)
            supabase.table(table_name).upsert(data).execute()
            uploaded += len(batch)
        except Exception as e:
            print(f"   ⚠️ 배치 {i//batch_size + 1} 오류: {str(e)[:100]}")
            # 개별 삽입 시도
            for row_dict in data:
                try:
                    supabase.table(table_name).upsert(row_dict).execute()
                    uploaded += 1
                except:
                    pass
        
        if (i // batch_size + 1) % 10 == 0:
            print(f"   진행: {uploaded:,}/{len(rows):,}건")
        
        time.sleep(0.05)
    
    conn.close()
    print(f"   ✅ {uploaded:,}건 업로드 완료")
    return uploaded


def main():
    print("=" * 80)
    print("📊 SQLite → Supabase 데이터 동기화")
    print("=" * 80)
    
    tables = [
        'binance_futures_metrics',
        'binance_spot_daily',
        'binance_spot_weekly',
        'bitget_spot_daily',
        'bitinfocharts_whale',
        'exchange_rate',
        'upbit_daily',
    ]
    
    total_uploaded = 0
    
    for table in tables:
        try:
            cnt = upload_table(table)
            total_uploaded += cnt
        except Exception as e:
            print(f"   ❌ {table} 오류: {e}")
    
    print("\n" + "=" * 80)
    print(f"🎉 총 {total_uploaded:,}건 업로드 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()



