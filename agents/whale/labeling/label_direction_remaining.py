#!/usr/bin/env python3
"""
transaction_direction이 NULL인 레코드만 라벨링
배치 처리로 Supabase timeout 우회
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 거래소 키워드
EXCHANGE_KEYWORDS = [
    'binance', 'coinbase', 'kraken', 'huobi', 'okx', 
    'bitfinex', 'gate.io', 'bybit', 'kucoin', 'upbit',
    'bithumb', 'bittrex', 'gemini', 'crypto.com', 'exchange'
]

def get_supabase_client():
    return create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    )

def is_exchange(label):
    """거래소 판별"""
    if not label:
        return False
    label_lower = label.lower()
    return any(keyword in label_lower for keyword in EXCHANGE_KEYWORDS)

def get_direction(from_label, to_label):
    """거래 유형 결정"""
    from_is_ex = is_exchange(from_label)
    to_is_ex = is_exchange(to_label)
    
    if from_is_ex and not to_is_ex:
        return 'BUY'
    elif not from_is_ex and to_is_ex:
        return 'SELL'
    else:
        return 'MOVE'

def process_batch(batch_size=500):
    """배치 단위로 NULL 레코드 처리"""
    supabase = get_supabase_client()
    
    # NULL인 레코드 조회
    response = supabase.table('whale_transactions')\
        .select('id, from_label, to_label')\
        .is_('transaction_direction', 'null')\
        .limit(batch_size)\
        .execute()
    
    if not response.data:
        return 0, {'BUY': 0, 'SELL': 0, 'MOVE': 0}
    
    # 분류
    updates = {'BUY': [], 'SELL': [], 'MOVE': []}
    
    for row in response.data:
        direction = get_direction(row.get('from_label'), row.get('to_label'))
        updates[direction].append(row['id'])
    
    # 업데이트 (direction별로)
    for direction, ids in updates.items():
        if not ids:
            continue
        
        # 100개씩 나눠서 업데이트
        for i in range(0, len(ids), 100):
            batch_ids = ids[i:i+100]
            supabase.table('whale_transactions')\
                .update({'transaction_direction': direction})\
                .in_('id', batch_ids)\
                .execute()
            time.sleep(0.05)  # Rate limit
    
    counts = {k: len(v) for k, v in updates.items()}
    return len(response.data), counts

def main():
    print("=" * 80)
    print("🚀 transaction_direction NULL 레코드 라벨링")
    print("=" * 80)
    
    supabase = get_supabase_client()
    
    # 초기 NULL 수 확인
    res = supabase.table('whale_transactions').select('id', count='exact').is_('transaction_direction', 'null').limit(1).execute()
    initial_null = res.count
    print(f"\n📊 처리 대상: {initial_null:,}건")
    
    if initial_null == 0:
        print("✅ 모든 레코드가 이미 라벨링되어 있습니다.")
        return
    
    start_time = time.time()
    total_processed = 0
    total_counts = {'BUY': 0, 'SELL': 0, 'MOVE': 0}
    batch_num = 0
    
    print("\n🔄 처리 중...")
    
    while True:
        batch_num += 1
        processed, counts = process_batch(500)
        
        if processed == 0:
            break
        
        total_processed += processed
        for k, v in counts.items():
            total_counts[k] += v
        
        # 진행률 출력
        remaining = initial_null - total_processed
        progress = (total_processed / initial_null) * 100
        elapsed = time.time() - start_time
        rate = total_processed / elapsed if elapsed > 0 else 0
        eta = remaining / rate if rate > 0 else 0
        
        print(f"   배치 {batch_num}: +{processed}건 | 총 {total_processed:,}건 ({progress:.1f}%) | ETA: {eta/60:.1f}분")
        
        # 10배치마다 현황 출력
        if batch_num % 10 == 0:
            print(f"      BUY: {total_counts['BUY']:,} | SELL: {total_counts['SELL']:,} | MOVE: {total_counts['MOVE']:,}")
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 80)
    print("✅ 완료!")
    print("=" * 80)
    print(f"\n📊 결과:")
    print(f"   처리 건수: {total_processed:,}건")
    print(f"   소요 시간: {elapsed/60:.1f}분")
    print(f"\n📈 거래 유형:")
    print(f"   BUY:  {total_counts['BUY']:,}건")
    print(f"   SELL: {total_counts['SELL']:,}건")
    print(f"   MOVE: {total_counts['MOVE']:,}건")
    
    # 최종 확인
    res = supabase.table('whale_transactions').select('id', count='exact').is_('transaction_direction', 'null').limit(1).execute()
    final_null = res.count
    print(f"\n📋 남은 NULL: {final_null:,}건")

if __name__ == '__main__':
    main()



