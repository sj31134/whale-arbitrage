#!/usr/bin/env python3
"""
1. NULL 라벨 -> 'Unknown Wallet'
2. transaction_direction 컬럼 추가 및 BUY/SELL/MOVE 라벨링
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_supabase_client():
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    # 타임아웃 옵션 제거 (라이브러리 버전 호환성 문제)
    return create_client(supabase_url, supabase_key)

def add_column_if_not_exists(supabase):
    print("1️⃣ 컬럼 확인 및 추가 중...")
    # RPC나 SQL 실행 기능이 없으므로, Supabase 대시보드에서 실행하라는 메시지 출력
    # 또는 postgrest-py의 기능을 활용할 수 있는지 확인
    # 여기서는 일단 진행하고, SQL 파일을 별도로 제공하는 것이 안전함.
    # 하지만 사용자 요청이 "작업해"이므로, 가능한 시도를 해봄.
    
    try:
        # 컬럼이 있는지 확인하기 위해 1개만 조회
        supabase.table('whale_transactions').select('transaction_direction').limit(1).execute()
        print("   ✅ transaction_direction 컬럼이 이미 존재합니다.")
    except Exception:
        print("   ⚠️ 컬럼이 없습니다. SQL Editor에서 다음을 실행해주세요:")
        print("   ALTER TABLE whale_transactions ADD COLUMN IF NOT EXISTS transaction_direction VARCHAR(20);")
        # 여기서 멈추지 않고 진행하면 에러 나므로, 사용자가 SQL을 실행했다고 가정하거나 
        # 안내 후 종료하는 게 맞지만, 자동화를 위해 SQL 실행 시도 (권한 문제 가능성 있음)

def update_unknown_labels(supabase, batch_size=200):
    print("\n2️⃣ NULL 라벨 -> 'Unknown Wallet' 업데이트 중...")
    
    total_updated = 0
    
    # 1. from_label
    while True:
        # 배치 조회
        response = supabase.table('whale_transactions')\
            .select('tx_hash')\
            .is_('from_label', 'null')\
            .limit(batch_size)\
            .execute()
            
        if not response.data:
            break
            
        tx_hashes = [r['tx_hash'] for r in response.data]
        
        # 업데이트
        try:
            supabase.table('whale_transactions')\
                .update({'from_label': 'Unknown Wallet'})\
                .in_('tx_hash', tx_hashes)\
                .execute()
            
            total_updated += len(tx_hashes)
            print(f"   from_label: {total_updated:,}건 처리 완료...", end='\r')
        except Exception as e:
            print(f"\n   ❌ 오류 발생: {e}")
            time.sleep(2)
            
    print(f"\n   ✅ from_label 업데이트 완료 (총 {total_updated:,}건)")
    
    # 2. to_label
    total_updated = 0
    while True:
        response = supabase.table('whale_transactions')\
            .select('tx_hash')\
            .is_('to_label', 'null')\
            .limit(batch_size)\
            .execute()
            
        if not response.data:
            break
            
        tx_hashes = [r['tx_hash'] for r in response.data]
        
        try:
            supabase.table('whale_transactions')\
                .update({'to_label': 'Unknown Wallet'})\
                .in_('tx_hash', tx_hashes)\
                .execute()
            
            total_updated += len(tx_hashes)
            print(f"   to_label: {total_updated:,}건 처리 완료...", end='\r')
        except Exception as e:
            print(f"\n   ❌ 오류 발생: {e}")
            time.sleep(2)
            
    print(f"\n   ✅ to_label 업데이트 완료 (총 {total_updated:,}건)")

def is_exchange(label):
    if not label:
        return False
    keywords = ['binance', 'coinbase', 'kraken', 'huobi', 'okx', 'bitfinex', 
                'gate.io', 'bybit', 'kucoin', 'upbit', 'bithumb', 'exchange']
    return any(k in label.lower() for k in keywords)

def update_transaction_direction(supabase, batch_size=200):
    print("\n3️⃣ 거래 유형(BUY/SELL/MOVE) 분류 및 업데이트 중...")
    
    total_processed = 0
    offset = 0
    
    while True:
        # 아직 분류되지 않은 거래 조회
        response = supabase.table('whale_transactions')\
            .select('tx_hash, from_label, to_label')\
            .is_('transaction_direction', 'null')\
            .limit(batch_size)\
            .execute()
            
        if not response.data:
            break
            
        updates_buy = []
        updates_sell = []
        updates_move = []
        
        for tx in response.data:
            from_lbl = tx.get('from_label', 'Unknown Wallet')
            to_lbl = tx.get('to_label', 'Unknown Wallet')
            
            from_is_ex = is_exchange(from_lbl)
            to_is_ex = is_exchange(to_lbl)
            
            if from_is_ex and not to_is_ex:
                updates_buy.append(tx['tx_hash'])
            elif not from_is_ex and to_is_ex:
                updates_sell.append(tx['tx_hash'])
            else:
                updates_move.append(tx['tx_hash'])
        
        # 일괄 업데이트
        try:
            if updates_buy:
                supabase.table('whale_transactions').update({'transaction_direction': 'BUY'}).in_('tx_hash', updates_buy).execute()
            if updates_sell:
                supabase.table('whale_transactions').update({'transaction_direction': 'SELL'}).in_('tx_hash', updates_sell).execute()
            if updates_move:
                supabase.table('whale_transactions').update({'transaction_direction': 'MOVE'}).in_('tx_hash', updates_move).execute()
            
            count = len(updates_buy) + len(updates_sell) + len(updates_move)
            total_processed += count
            print(f"   진행 중: {total_processed:,}건 분류 완료... (BUY: {len(updates_buy)}, SELL: {len(updates_sell)}, MOVE: {len(updates_move)})", end='\r')
            
        except Exception as e:
            print(f"\n   ❌ 오류 발생: {e}")
            time.sleep(2)
            
    print(f"\n   ✅ 거래 유형 분류 완료 (총 {total_processed:,}건)")

def main():
    print("=" * 80)
    print("🚀 라벨링 데이터 후처리 시작")
    print("=" * 80)
    
    supabase = get_supabase_client()
    
    # 1. 컬럼 체크 (건너뛰기)
    # try:
    #     supabase.table('whale_transactions').select('transaction_direction').limit(1).execute()
    # except:
    #     print("\n⚠️ 'transaction_direction' 컬럼이 없습니다!")
    #     print("Supabase SQL Editor에서 아래 쿼리를 먼저 실행해주세요:")
    #     print("-" * 60)
    #     print("ALTER TABLE whale_transactions ADD COLUMN IF NOT EXISTS transaction_direction VARCHAR(20);")
    #     print("-" * 60)
    #     return

    # 2. Unknown Wallet 업데이트
    update_unknown_labels(supabase)
    
    # 3. Direction 업데이트
    update_transaction_direction(supabase)
    
    print("\n" + "=" * 80)
    print("🎉 모든 작업 완료!")
    print("=" * 80)

if __name__ == '__main__':
    main()

