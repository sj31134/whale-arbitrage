#!/usr/bin/env python3
"""
BUY/SELL 부재 원인 진단 스크립트
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_supabase_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    return create_client(supabase_url, supabase_key)

def main():
    print("=" * 80)
    print("🔍 BUY/SELL 부재 원인 진단")
    print("=" * 80)
    
    supabase = get_supabase_client()
    
    # 1. 전체 거래 수
    total_res = supabase.table('whale_transactions').select('*', count='exact').execute()
    total_count = total_res.count
    print(f"\n📊 1. 전체 거래 데이터")
    print(f"   - 총 거래 수: {total_count:,}건")
    
    # 2. transaction_direction 분포 (전체)
    print(f"\n📊 2. transaction_direction 상태 (샘플 10,000건)")
    sample = supabase.table('whale_transactions').select('transaction_direction').limit(10000).execute()
    
    if sample.data:
        from collections import Counter
        direction_counts = Counter([row['transaction_direction'] for row in sample.data])
        for direction, count in direction_counts.items():
            print(f"   - {direction}: {count:,}건 ({count/len(sample.data)*100:.1f}%)")
    
    # 3. from_label과 to_label 상태
    print(f"\n📊 3. from_label / to_label 상태 (샘플 1,000건)")
    label_sample = supabase.table('whale_transactions').select('from_label, to_label').limit(1000).execute()
    
    from_null = sum(1 for row in label_sample.data if not row.get('from_label') or row.get('from_label') == 'Unknown Wallet')
    to_null = sum(1 for row in label_sample.data if not row.get('to_label') or row.get('to_label') == 'Unknown Wallet')
    
    print(f"   - from_label NULL 또는 Unknown Wallet: {from_null}/{len(label_sample.data)} ({from_null/len(label_sample.data)*100:.1f}%)")
    print(f"   - to_label NULL 또는 Unknown Wallet: {to_null}/{len(label_sample.data)*100:.1f}%)")
    
    # 4. 거래소 라벨이 있는 거래 샘플
    print(f"\n📊 4. 거래소 관련 라벨 확인 (샘플 20건)")
    exchange_keywords = ['binance', 'coinbase', 'kraken', 'huobi', 'okx', 'bitfinex', 'gate', 'bybit', 'kucoin', 'upbit', 'bithumb', 'crypto.com']
    
    # from_label에 거래소가 있는 경우
    print("\n   [from_label에 거래소 이름이 있는 거래 - BUY 후보]")
    for kw in exchange_keywords[:3]:  # 처음 3개만
        res = supabase.table('whale_transactions')\
            .select('tx_hash, from_label, to_label, transaction_direction, amount, coin_symbol')\
            .ilike('from_label', f'%{kw}%')\
            .limit(5)\
            .execute()
        if res.data:
            print(f"\n   키워드 '{kw}' 결과 ({len(res.data)}건):")
            for row in res.data[:2]:
                print(f"      from: {row['from_label'][:30]:<30} -> to: {row['to_label'][:30] if row['to_label'] else 'NULL':<30} | direction: {row['transaction_direction']}")
            break
    
    # to_label에 거래소가 있는 경우
    print("\n   [to_label에 거래소 이름이 있는 거래 - SELL 후보]")
    for kw in exchange_keywords[:3]:
        res = supabase.table('whale_transactions')\
            .select('tx_hash, from_label, to_label, transaction_direction, amount, coin_symbol')\
            .ilike('to_label', f'%{kw}%')\
            .limit(5)\
            .execute()
        if res.data:
            print(f"\n   키워드 '{kw}' 결과 ({len(res.data)}건):")
            for row in res.data[:2]:
                print(f"      from: {row['from_label'][:30] if row['from_label'] else 'NULL':<30} -> to: {row['to_label'][:30]:<30} | direction: {row['transaction_direction']}")
            break
    
    # 5. whale_address 테이블의 거래소 데이터 확인
    print(f"\n📊 5. whale_address 테이블의 거래소 정보")
    wa_res = supabase.table('whale_address').select('address, name_tag, chain_type').limit(100).execute()
    
    if wa_res.data:
        exchange_wallets = [row for row in wa_res.data if any(kw in str(row.get('name_tag', '')).lower() for kw in exchange_keywords)]
        print(f"   - 전체 고래 주소: {len(wa_res.data)}건 (샘플 100건 기준)")
        print(f"   - 거래소 주소: {len(exchange_wallets)}건")
        if exchange_wallets:
            print(f"\n   샘플 거래소 주소 (처음 5개):")
            for w in exchange_wallets[:5]:
                print(f"      {w['name_tag'][:40]:<40} | {w['chain_type']}")
    
    # 6. 결론 및 원인 분석
    print(f"\n" + "=" * 80)
    print("💡 원인 분석 결과")
    print("=" * 80)
    
    if direction_counts.get('MOVE', 0) > direction_counts.get('BUY', 0) + direction_counts.get('SELL', 0):
        print("\n⚠️ 문제 1: transaction_direction이 대부분 'MOVE'로 설정되어 있음")
        print("   원인: ")
        print("   - from_label과 to_label이 모두 'Unknown Wallet'이거나 NULL")
        print("   - 또는 양쪽 모두 거래소가 아닌 경우")
        print("   해결책:")
        print("   - whale_address 테이블에 더 많은 거래소/고래 주소 추가")
        print("   - 라벨 업데이트 스크립트 재실행")
    
    if from_null > 700 or to_null > 700:
        print("\n⚠️ 문제 2: 라벨이 제대로 업데이트되지 않음")
        print("   원인:")
        print("   - whale_address 테이블의 주소가 부족")
        print("   - 또는 주소 매칭 로직 문제")
        print("   해결책:")
        print("   - whale_address 데이터 보강 필요")
        print("   - scripts/labeling/update_whale_transaction_labels.py 재실행")
    
    if len(exchange_wallets) < 10:
        print("\n⚠️ 문제 3: whale_address에 거래소 주소가 부족함")
        print("   원인:")
        print("   - 수집된 고래 주소 중 거래소 주소가 거의 없음")
        print("   해결책:")
        print("   - Etherscan/BSCScan의 거래소 주소 크롤링")
        print("   - 또는 알려진 거래소 주소를 수동으로 whale_address에 추가")

if __name__ == '__main__':
    main()

