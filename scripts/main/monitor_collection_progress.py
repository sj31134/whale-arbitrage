#!/usr/bin/env python3
"""
8개 코인 수집 진행 상황 모니터링
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from collections import Counter

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_SERVICE_ROLE_KEY')
)

def check_progress():
    """수집 진행 상황 확인"""
    print("\n" + "="*80)
    print("📊 8개 코인 수집 진행 상황")
    print("="*80)
    
    # whale_transactions 확인
    response = supabase.table('whale_transactions').select('coin_symbol, chain, block_timestamp').execute()
    
    coin_counts = Counter(r['coin_symbol'] for r in response.data)
    
    # 2025년 1~10월 데이터만 필터링
    from datetime import datetime
    jan_oct_data = [r for r in response.data 
                    if r.get('block_timestamp') and 
                    '2025-01' <= r['block_timestamp'][:7] <= '2025-10']
    
    jan_oct_counts = Counter(r['coin_symbol'] for r in jan_oct_data)
    
    print(f"\n전체 whale_transactions: {len(response.data):,}건")
    print(f"2025년 1~10월 데이터: {len(jan_oct_data):,}건")
    
    print("\n코인별 통계 (전체 / 2025년 1~10월):")
    for coin in sorted(set(list(coin_counts.keys()) + list(jan_oct_counts.keys()))):
        total = coin_counts.get(coin, 0)
        jan_oct = jan_oct_counts.get(coin, 0)
        print(f"  {coin:10} : {total:,}건 / {jan_oct:,}건")
    
    # 로그 파일 상태
    log_file = PROJECT_ROOT / 'collection_8coins_2025_jan_oct.log'
    if log_file.exists():
        with open(log_file, 'r') as f:
            lines = f.readlines()
            print(f"\n로그 파일: {len(lines):,}줄")
            if lines:
                print(f"최근 로그 (마지막 5줄):")
                for line in lines[-5:]:
                    print(f"  {line.rstrip()}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    check_progress()
