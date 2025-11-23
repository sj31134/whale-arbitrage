#!/usr/bin/env python3
"""
PostgreSQL 직접 연결로 거래 유형 라벨링
Supabase API timeout 우회
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import execute_batch
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_db_connection():
    """Supabase PostgreSQL 직접 연결"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_password = os.getenv('SUPABASE_DB_PASSWORD')  # 필요시 추가
    
    # Supabase URL에서 프로젝트 ID 추출
    # 예: https://xxxxx.supabase.co -> xxxxx
    parsed = urlparse(supabase_url)
    project_id = parsed.netloc.split('.')[0]
    
    # Supabase PostgreSQL 연결 정보
    # 형식: postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
    
    print("PostgreSQL 연결 정보를 입력해주세요.")
    print("\nSupabase 대시보드 > Project Settings > Database > Connection string 에서 확인:")
    print("또는 .env 파일에 SUPABASE_DB_PASSWORD를 추가하세요.\n")
    
    if not supabase_password:
        supabase_password = input("PostgreSQL 비밀번호: ").strip()
    
    connection_string = f"postgresql://postgres.{project_id}:{supabase_password}@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres"
    
    try:
        conn = psycopg2.connect(connection_string)
        print("✅ PostgreSQL 연결 성공!")
        return conn
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        print("\n다른 연결 문자열을 시도합니다...")
        
        # 대체 연결 문자열 (포트 5432)
        alt_connection_string = f"postgresql://postgres:{supabase_password}@db.{project_id}.supabase.co:5432/postgres"
        conn = psycopg2.connect(alt_connection_string)
        print("✅ PostgreSQL 연결 성공! (대체 포트)")
        return conn

def add_column_if_not_exists(conn):
    """transaction_direction 컬럼 추가"""
    print("\n1️⃣ transaction_direction 컬럼 추가 중...")
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            ALTER TABLE whale_transactions 
            ADD COLUMN IF NOT EXISTS transaction_direction VARCHAR(20);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_whale_tx_direction 
            ON whale_transactions(transaction_direction);
        """)
        
        conn.commit()
        print("   ✅ 컬럼 추가 완료")
        
    except Exception as e:
        conn.rollback()
        print(f"   ℹ️ {e}")
    finally:
        cursor.close()

def update_unknown_labels(conn):
    """NULL 라벨을 'Unknown Wallet'로 업데이트"""
    print("\n2️⃣ NULL 라벨 업데이트 중...")
    
    cursor = conn.cursor()
    
    try:
        # from_label
        print("   from_label 처리 중...")
        cursor.execute("""
            UPDATE whale_transactions
            SET from_label = 'Unknown Wallet'
            WHERE from_label IS NULL;
        """)
        from_count = cursor.rowcount
        print(f"   ✅ from_label: {from_count:,}건 업데이트")
        
        # to_label
        print("   to_label 처리 중...")
        cursor.execute("""
            UPDATE whale_transactions
            SET to_label = 'Unknown Wallet'
            WHERE to_label IS NULL;
        """)
        to_count = cursor.rowcount
        print(f"   ✅ to_label: {to_count:,}건 업데이트")
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        print(f"   ❌ 오류: {e}")
    finally:
        cursor.close()

def label_transaction_direction(conn):
    """거래 유형 라벨링"""
    print("\n3️⃣ 거래 유형 라벨링 중...")
    
    cursor = conn.cursor()
    
    exchange_keywords = [
        '%binance%', '%coinbase%', '%kraken%', '%huobi%', '%okx%',
        '%bitfinex%', '%gate.io%', '%bybit%', '%kucoin%', 
        '%upbit%', '%bithumb%', '%bittrex%', '%gemini%',
        '%crypto.com%', '%exchange%'
    ]
    
    try:
        # BUY: 거래소 → 일반
        print("   BUY 라벨링 중...")
        cursor.execute("""
            UPDATE whale_transactions
            SET transaction_direction = 'BUY'
            WHERE transaction_direction IS NULL
            AND (
                from_label ILIKE ANY(%s)
            )
            AND NOT (
                to_label ILIKE ANY(%s)
            );
        """, (exchange_keywords, exchange_keywords))
        buy_count = cursor.rowcount
        print(f"   ✅ BUY: {buy_count:,}건")
        
        # SELL: 일반 → 거래소
        print("   SELL 라벨링 중...")
        cursor.execute("""
            UPDATE whale_transactions
            SET transaction_direction = 'SELL'
            WHERE transaction_direction IS NULL
            AND NOT (
                from_label ILIKE ANY(%s)
            )
            AND (
                to_label ILIKE ANY(%s)
            );
        """, (exchange_keywords, exchange_keywords))
        sell_count = cursor.rowcount
        print(f"   ✅ SELL: {sell_count:,}건")
        
        # MOVE: 나머지
        print("   MOVE 라벨링 중...")
        cursor.execute("""
            UPDATE whale_transactions
            SET transaction_direction = 'MOVE'
            WHERE transaction_direction IS NULL;
        """)
        move_count = cursor.rowcount
        print(f"   ✅ MOVE: {move_count:,}건")
        
        conn.commit()
        
        print(f"\n   📊 총 {buy_count + sell_count + move_count:,}건 라벨링 완료")
        
    except Exception as e:
        conn.rollback()
        print(f"   ❌ 오류: {e}")
        raise
    finally:
        cursor.close()

def show_statistics(conn):
    """결과 통계 출력"""
    print("\n4️⃣ 결과 확인")
    print("=" * 80)
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                transaction_direction,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
            FROM whale_transactions
            WHERE transaction_direction IS NOT NULL
            GROUP BY transaction_direction
            ORDER BY count DESC;
        """)
        
        print("\n거래 유형별 통계:")
        print(f"{'유형':<15} {'건수':>15} {'비율':>10}")
        print("-" * 80)
        
        total = 0
        for row in cursor.fetchall():
            direction, count, percentage = row
            print(f"{direction:<15} {count:>15,} {percentage:>9.2f}%")
            total += count
        
        print("-" * 80)
        print(f"{'총계':<15} {total:>15,}")
        
        # 샘플 데이터
        print("\n샘플 데이터 (각 유형별 3건):")
        for direction in ['BUY', 'SELL', 'MOVE']:
            print(f"\n{direction}:")
            cursor.execute("""
                SELECT tx_hash, from_label, to_label, coin_symbol, amount
                FROM whale_transactions
                WHERE transaction_direction = %s
                ORDER BY block_timestamp DESC
                LIMIT 3;
            """, (direction,))
            
            for idx, row in enumerate(cursor.fetchall(), 1):
                tx_hash, from_label, to_label, coin, amount = row
                print(f"  {idx}. {from_label[:20]} → {to_label[:20]}")
                print(f"     {coin}: {amount}")
                print(f"     TX: {tx_hash[:20]}...")
        
    except Exception as e:
        print(f"❌ 통계 조회 오류: {e}")
    finally:
        cursor.close()

def main():
    print("\n" + "=" * 80)
    print("🚀 PostgreSQL 직접 연결로 거래 유형 라벨링")
    print("   (Supabase API timeout 우회)")
    print("=" * 80)
    
    try:
        # PostgreSQL 연결
        conn = get_db_connection()
        
        # 1. 컬럼 추가
        add_column_if_not_exists(conn)
        
        # 2. Unknown Wallet 업데이트
        update_unknown_labels(conn)
        
        # 3. 거래 유형 라벨링
        label_transaction_direction(conn)
        
        # 4. 결과 확인
        show_statistics(conn)
        
        # 연결 종료
        conn.close()
        
        print("\n" + "=" * 80)
        print("✅ 모든 작업 완료!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

