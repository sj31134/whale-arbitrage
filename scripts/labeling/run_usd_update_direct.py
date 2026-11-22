#!/usr/bin/env python3
"""
amount_usd 직접 업데이트 스크립트 (RPC 미사용 버전)
- SQL 함수 생성 없이 Python에서 직접 계산하여 업데이트합니다.
- 속도는 조금 느리지만 확실하게 동작합니다.
"""

import os
import sys
import time
import pandas as pd
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

def update_usd_direct(supabase, batch_size=100):
    # 1. 업데이트 대상 조회 (NULL인 것)
    print("🔍 업데이트 대상 조회 중...")
    
    # 먼저 코인 심볼과 ID 매핑 가져오기
    crypto_map = {}
    c_res = supabase.table('cryptocurrencies').select('id, symbol').execute()
    for item in c_res.data:
        crypto_map[item['symbol']] = item['id']
        
    # 트랜잭션 가져오기
    response = supabase.table('whale_transactions')\
        .select('tx_hash, amount, coin_symbol, block_timestamp')\
        .is_('amount_usd', 'null')\
        .limit(batch_size)\
        .execute()
        
    txs = response.data
    if not txs:
        return 0
        
    print(f"   - {len(txs)}건의 대상을 찾았습니다. 가격 매칭 시작...")
    
    updated_count = 0
    
    for tx in txs:
        try:
            symbol = tx['coin_symbol']
            if symbol not in crypto_map:
                continue
                
            crypto_id = crypto_map[symbol]
            timestamp = tx['block_timestamp']
            
            # 시간 절삭 (단순 문자열 처리로 'YYYY-MM-DDTHH:00:00' 형식 만들기)
            # ISO 포맷 가정: 2025-11-22T09:12:34... -> 2025-11-22T09:00:00
            ts_str = timestamp.split(':')[0] + ":00:00"
            
            # 가격 조회 (캐싱하면 좋지만 일단 단순하게)
            # 해당 시간대의 가격이 있는지 확인
            price_res = supabase.table('price_history')\
                .select('close_price')\
                .eq('crypto_id', crypto_id)\
                .gte('timestamp', ts_str)\
                .limit(1)\
                .execute()
                
            if price_res.data:
                price = float(price_res.data[0]['close_price'])
                amount = float(tx['amount'])
                amount_usd = amount * price
                
                # 업데이트
                supabase.table('whale_transactions')\
                    .update({'amount_usd': amount_usd, 'updated_at': 'now()'})\
                    .eq('tx_hash', tx['tx_hash'])\
                    .execute()
                updated_count += 1
                print(f"\r   - 업데이트 진행: {updated_count}/{len(txs)}", end="", flush=True)
            else:
                # 가격 데이터가 없으면... 일단 패스하거나 0으로? 패스
                pass
                
        except Exception as e:
            print(f" [Error: {e}]", end="")
            
    print()
    return updated_count

def main():
    print("=" * 80)
    print("💰 amount_usd 직접 업데이트 (Python 방식)")
    print("=" * 80)
    
    supabase = get_supabase_client()
    total_processed = 0
    
    while True:
        try:
            count = update_usd_direct(supabase, batch_size=50) # 타임아웃 방지 위해 작게
            if count == 0:
                print("\n✅ 더 이상 업데이트할 데이터가 없거나, 가격 정보를 찾지 못했습니다.")
                break
            total_processed += count
            print(f"✨ 누적 완료: {total_processed:,}건")
            time.sleep(0.5)
        except Exception as e:
            print(f"\n❌ 스크립트 오류: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()

