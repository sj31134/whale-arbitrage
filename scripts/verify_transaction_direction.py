#!/usr/bin/env python3
"""
transaction_direction 라벨링 결과 확인
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_supabase_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    return create_client(supabase_url, supabase_key)

def main():
    print("\n" + "=" * 80)
    print("📊 Transaction Direction 라벨링 결과 확인")
    print("=" * 80)
    
    supabase = get_supabase_client()
    
    # 1. 전체 통계
    print("\n1️⃣ 전체 거래 유형별 통계")
    print("-" * 80)
    
    try:
        response = supabase.table('whale_transactions')\
            .select('transaction_direction')\
            .execute()
        
        from collections import Counter
        stats = Counter([r.get('transaction_direction') for r in response.data])
        
        total = len(response.data)
        print(f"\n총 거래 수: {total:,}건\n")
        
        for direction in ['BUY', 'SELL', 'MOVE', None]:
            count = stats.get(direction, 0)
            percentage = (count / total * 100) if total > 0 else 0
            label = direction if direction else '미분류'
            print(f"  {label:12s}: {count:10,}건 ({percentage:5.2f}%)")
    
    except Exception as e:
        print(f"❌ 오류: {e}")
        return
    
    # 2. 코인별 통계
    print("\n2️⃣ 코인별 거래 유형 통계 (상위 10개)")
    print("-" * 80)
    
    try:
        response = supabase.table('whale_transactions')\
            .select('coin_symbol, transaction_direction')\
            .execute()
        
        from collections import defaultdict
        coin_stats = defaultdict(lambda: {'BUY': 0, 'SELL': 0, 'MOVE': 0, 'TOTAL': 0})
        
        for row in response.data:
            coin = row.get('coin_symbol', 'UNKNOWN')
            direction = row.get('transaction_direction')
            
            coin_stats[coin]['TOTAL'] += 1
            if direction in ['BUY', 'SELL', 'MOVE']:
                coin_stats[coin][direction] += 1
        
        # 정렬 (거래량 많은 순)
        sorted_coins = sorted(coin_stats.items(), key=lambda x: x[1]['TOTAL'], reverse=True)[:10]
        
        print(f"\n{'코인':<10} {'BUY':>10} {'SELL':>10} {'MOVE':>10} {'총계':>12}")
        print("-" * 80)
        
        for coin, stats in sorted_coins:
            print(f"{coin:<10} {stats['BUY']:>10,} {stats['SELL']:>10,} {stats['MOVE']:>10,} {stats['TOTAL']:>12,}")
    
    except Exception as e:
        print(f"❌ 오류: {e}")
    
    # 3. 샘플 데이터 (각 유형별 3건)
    print("\n3️⃣ 샘플 거래 데이터")
    print("-" * 80)
    
    for direction in ['BUY', 'SELL', 'MOVE']:
        print(f"\n{direction}:")
        try:
            response = supabase.table('whale_transactions')\
                .select('tx_hash, from_label, to_label, coin_symbol, amount, amount_usd')\
                .eq('transaction_direction', direction)\
                .limit(3)\
                .execute()
            
            for idx, row in enumerate(response.data, 1):
                from_label = row.get('from_label', 'Unknown')[:20]
                to_label = row.get('to_label', 'Unknown')[:20]
                coin = row.get('coin_symbol', 'N/A')
                amount = row.get('amount', 0)
                amount_usd = row.get('amount_usd', 0)
                
                print(f"  {idx}. {from_label} → {to_label}")
                print(f"     {coin}: {amount} (${amount_usd:,.2f})" if amount_usd else f"     {coin}: {amount}")
                print(f"     TX: {row['tx_hash'][:20]}...")
        
        except Exception as e:
            print(f"     ❌ 오류: {e}")
    
    # 4. 라벨 업데이트 확인
    print("\n4️⃣ 라벨 업데이트 상태")
    print("-" * 80)
    
    try:
        response = supabase.table('whale_transactions')\
            .select('from_label, to_label')\
            .execute()
        
        null_from = sum(1 for r in response.data if not r.get('from_label'))
        null_to = sum(1 for r in response.data if not r.get('to_label'))
        unknown_from = sum(1 for r in response.data if r.get('from_label') == 'Unknown Wallet')
        unknown_to = sum(1 for r in response.data if r.get('to_label') == 'Unknown Wallet')
        
        print(f"\nfrom_label:")
        print(f"  NULL: {null_from:,}건")
        print(f"  'Unknown Wallet': {unknown_from:,}건")
        
        print(f"\nto_label:")
        print(f"  NULL: {null_to:,}건")
        print(f"  'Unknown Wallet': {unknown_to:,}건")
        
        if null_from == 0 and null_to == 0:
            print("\n✅ 모든 라벨이 업데이트되었습니다!")
        else:
            print(f"\n⚠️ 아직 {null_from + null_to:,}건의 NULL 라벨이 있습니다.")
    
    except Exception as e:
        print(f"❌ 오류: {e}")
    
    print("\n" + "=" * 80)
    print("✅ 확인 완료!")
    print("=" * 80)

if __name__ == '__main__':
    main()

