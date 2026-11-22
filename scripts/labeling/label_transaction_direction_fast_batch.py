#!/usr/bin/env python3
"""
초고속 거래 유형 라벨링 (작은 배치 + 병렬 처리)
Supabase API timeout 우회
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Set

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 거래소 키워드
EXCHANGE_KEYWORDS = [
    'binance', 'coinbase', 'kraken', 'huobi', 'okx', 
    'bitfinex', 'gate.io', 'bybit', 'kucoin', 'upbit',
    'bithumb', 'bittrex', 'gemini', 'crypto.com', 'exchange'
]

def get_supabase_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    return create_client(supabase_url, supabase_key)

def is_exchange(label):
    """거래소 판별"""
    if not label:
        return False
    label_lower = label.lower()
    return any(keyword in label_lower for keyword in EXCHANGE_KEYWORDS)

def process_labels_chunk(coin_symbol: str) -> dict:
    """코인별로 라벨 처리 (Unknown Wallet 업데이트 + Direction 라벨링)"""
    supabase = get_supabase_client()
    
    try:
        # 1. 해당 코인의 거래 조회
        response = supabase.table('whale_transactions')\
            .select('tx_hash, from_label, to_label')\
            .eq('coin_symbol', coin_symbol)\
            .execute()
        
        if not response.data:
            return {
                'coin': coin_symbol,
                'total': 0,
                'from_updated': 0,
                'to_updated': 0,
                'buy': 0,
                'sell': 0,
                'move': 0
            }
        
        # 2. 분류
        from_updates = []  # NULL -> Unknown Wallet
        to_updates = []    # NULL -> Unknown Wallet
        buy_updates = []
        sell_updates = []
        move_updates = []
        
        for tx in response.data:
            tx_hash = tx['tx_hash']
            from_label = tx.get('from_label')
            to_label = tx.get('to_label')
            
            # Unknown Wallet 업데이트 필요
            if not from_label:
                from_updates.append(tx_hash)
                from_label = 'Unknown Wallet'
            
            if not to_label:
                to_updates.append(tx_hash)
                to_label = 'Unknown Wallet'
            
            # 거래 유형 분류
            from_is_ex = is_exchange(from_label)
            to_is_ex = is_exchange(to_label)
            
            if from_is_ex and not to_is_ex:
                buy_updates.append(tx_hash)
            elif not from_is_ex and to_is_ex:
                sell_updates.append(tx_hash)
            else:
                move_updates.append(tx_hash)
        
        # 3. Bulk 업데이트 (100개씩 나눠서)
        batch_size = 100
        
        # from_label 업데이트
        for i in range(0, len(from_updates), batch_size):
            batch = from_updates[i:i + batch_size]
            supabase.table('whale_transactions')\
                .update({'from_label': 'Unknown Wallet'})\
                .in_('tx_hash', batch)\
                .execute()
            time.sleep(0.1)  # Rate limit 방지
        
        # to_label 업데이트
        for i in range(0, len(to_updates), batch_size):
            batch = to_updates[i:i + batch_size]
            supabase.table('whale_transactions')\
                .update({'to_label': 'Unknown Wallet'})\
                .in_('tx_hash', batch)\
                .execute()
            time.sleep(0.1)
        
        # transaction_direction 업데이트
        for direction, updates in [('BUY', buy_updates), ('SELL', sell_updates), ('MOVE', move_updates)]:
            for i in range(0, len(updates), batch_size):
                batch = updates[i:i + batch_size]
                supabase.table('whale_transactions')\
                    .update({'transaction_direction': direction})\
                    .in_('tx_hash', batch)\
                    .execute()
                time.sleep(0.1)
        
        return {
            'coin': coin_symbol,
            'total': len(response.data),
            'from_updated': len(from_updates),
            'to_updated': len(to_updates),
            'buy': len(buy_updates),
            'sell': len(sell_updates),
            'move': len(move_updates)
        }
        
    except Exception as e:
        print(f"❌ {coin_symbol} 처리 오류: {e}")
        return {
            'coin': coin_symbol,
            'total': 0,
            'from_updated': 0,
            'to_updated': 0,
            'buy': 0,
            'sell': 0,
            'move': 0,
            'error': str(e)
        }

def add_column_if_not_exists():
    """transaction_direction 컬럼 확인"""
    print("\n1️⃣ transaction_direction 컬럼 확인 중...")
    supabase = get_supabase_client()
    
    try:
        supabase.table('whale_transactions')\
            .select('transaction_direction')\
            .limit(1)\
            .execute()
        print("   ✅ transaction_direction 컬럼 존재")
        return True
    except:
        print("   ⚠️ transaction_direction 컬럼이 없습니다!")
        print("\n   Supabase SQL Editor에서 아래 명령 실행 필요:")
        print("   " + "-" * 70)
        print("   ALTER TABLE whale_transactions ADD COLUMN transaction_direction VARCHAR(20);")
        print("   CREATE INDEX idx_whale_tx_direction ON whale_transactions(transaction_direction);")
        print("   " + "-" * 70)
        return False

def get_all_coins() -> List[str]:
    """모든 코인 심볼 조회"""
    print("\n2️⃣ 코인 목록 조회 중...")
    supabase = get_supabase_client()
    
    try:
        response = supabase.table('whale_transactions')\
            .select('coin_symbol')\
            .execute()
        
        coins = list(set(row['coin_symbol'] for row in response.data if row.get('coin_symbol')))
        coins.sort()
        
        print(f"   ✅ {len(coins)}개 코인 발견")
        return coins
        
    except Exception as e:
        print(f"   ❌ 오류: {e}")
        return []

def main():
    print("\n" + "=" * 80)
    print("🚀 초고속 거래 유형 라벨링 (코인별 병렬 처리)")
    print("=" * 80)
    
    start_time = time.time()
    
    # 1. 컬럼 확인
    if not add_column_if_not_exists():
        return
    
    # 2. 모든 코인 조회
    coins = get_all_coins()
    
    if not coins:
        print("❌ 처리할 코인이 없습니다.")
        return
    
    print(f"\n코인 목록: {', '.join(coins[:10])}{'...' if len(coins) > 10 else ''}")
    
    # 3. 병렬 처리
    print("\n3️⃣ 코인별 병렬 처리 시작...")
    print("-" * 80)
    
    total_stats = {
        'total': 0,
        'from_updated': 0,
        'to_updated': 0,
        'buy': 0,
        'sell': 0,
        'move': 0
    }
    
    processed = 0
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_labels_chunk, coin): coin for coin in coins}
        
        for future in as_completed(futures):
            result = future.result()
            
            processed += 1
            
            # 통계 누적
            for key in ['total', 'from_updated', 'to_updated', 'buy', 'sell', 'move']:
                total_stats[key] += result.get(key, 0)
            
            # 진행 상황 출력
            coin = result['coin']
            total = result['total']
            buy = result['buy']
            sell = result['sell']
            move = result['move']
            
            print(f"[{processed:2d}/{len(coins):2d}] {coin:10s}: "
                  f"총 {total:6,}건 | "
                  f"BUY {buy:5,} | SELL {sell:5,} | MOVE {move:5,}")
            
            # 에러 표시
            if 'error' in result:
                print(f"        ⚠️ 오류: {result['error']}")
    
    elapsed = time.time() - start_time
    
    # 4. 최종 결과
    print("\n" + "=" * 80)
    print("✅ 처리 완료!")
    print("=" * 80)
    print(f"소요 시간: {elapsed/60:.1f}분")
    print(f"\n총 거래: {total_stats['total']:,}건")
    print(f"  - from_label 업데이트: {total_stats['from_updated']:,}건")
    print(f"  - to_label 업데이트: {total_stats['to_updated']:,}건")
    print(f"\n거래 유형:")
    print(f"  - BUY:  {total_stats['buy']:,}건 ({total_stats['buy']/total_stats['total']*100:.1f}%)")
    print(f"  - SELL: {total_stats['sell']:,}건 ({total_stats['sell']/total_stats['total']*100:.1f}%)")
    print(f"  - MOVE: {total_stats['move']:,}건 ({total_stats['move']/total_stats['total']*100:.1f}%)")
    
    # 5. 샘플 확인
    print("\n4️⃣ 샘플 데이터 확인")
    print("-" * 80)
    
    supabase = get_supabase_client()
    
    for direction in ['BUY', 'SELL', 'MOVE']:
        try:
            response = supabase.table('whale_transactions')\
                .select('tx_hash, from_label, to_label, coin_symbol, amount')\
                .eq('transaction_direction', direction)\
                .limit(3)\
                .execute()
            
            print(f"\n{direction}:")
            for idx, row in enumerate(response.data, 1):
                from_label = row.get('from_label', 'N/A')[:20]
                to_label = row.get('to_label', 'N/A')[:20]
                print(f"  {idx}. {from_label} → {to_label}")
                print(f"     {row['coin_symbol']}: {row['amount']}")
        except Exception as e:
            print(f"  ❌ 오류: {e}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()

