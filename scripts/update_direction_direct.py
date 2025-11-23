#!/usr/bin/env python3
"""
transaction_direction 업데이트 스크립트 (Python 방식)
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
    return create_client(supabase_url, supabase_key)

EXCHANGE_KEYWORDS = ['binance', 'coinbase', 'kraken', 'huobi', 'okx', 'bitfinex', 'gate', 'bybit', 'kucoin', 'upbit', 'bithumb', 'crypto.com']

def classify_direction(from_label, to_label):
    from_label_lower = str(from_label).lower() if from_label else ''
    to_label_lower = str(to_label).lower() if to_label else ''
    
    from_is_exchange = any(kw in from_label_lower for kw in EXCHANGE_KEYWORDS)
    to_is_exchange = any(kw in to_label_lower for kw in EXCHANGE_KEYWORDS)
    
    if from_is_exchange and not to_is_exchange:
        return 'BUY'
    elif not from_is_exchange and to_is_exchange:
        return 'SELL'
    else:
        return 'MOVE'

def update_with_retry(supabase, tx_hash, direction, max_retries=3):
    """재시도 로직이 포함된 업데이트 함수"""
    for attempt in range(max_retries):
        try:
            supabase.table('whale_transactions')\
                .update({'transaction_direction': direction, 'updated_at': 'now()'})\
                .eq('tx_hash', tx_hash)\
                .execute()
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 지수 백오프: 1초, 2초, 4초
            else:
                return False
    return False

def main():
    print("=" * 80)
    print("🔄 transaction_direction 업데이트 (Python 직접 방식 - 개선 버전)")
    print("=" * 80)
    
    supabase = get_supabase_client()
    
    batch_size = 50  # 배치 크기 감소 (타임아웃 방지)
    total_updated = 0
    failed_txs = []
    
    while True:
        try:
            # direction이 NULL인 거래 조회
            response = supabase.table('whale_transactions')\
                .select('tx_hash, from_label, to_label')\
                .is_('transaction_direction', 'null')\
                .limit(batch_size)\
                .execute()
            
            if not response.data or len(response.data) == 0:
                print("\n✅ 모든 거래의 direction이 업데이트되었습니다!")
                break
            
            # direction 계산 및 업데이트
            batch_updated = 0
            for tx in response.data:
                direction = classify_direction(tx['from_label'], tx['to_label'])
                
                if update_with_retry(supabase, tx['tx_hash'], direction):
                    batch_updated += 1
                    total_updated += 1
                else:
                    failed_txs.append(tx['tx_hash'])
            
            print(f"\r✨ 진행 중: {total_updated:,}건 업데이트 완료 (실패: {len(failed_txs)}건)", end="", flush=True)
            time.sleep(1.0)  # 딜레이 증가 (타임아웃 방지)
            
        except Exception as e:
            print(f"\n⚠️ 배치 조회 중 오류 발생: {e}")
            print("   5초 대기 후 재시도...")
            time.sleep(5)
    
    # 실패한 거래 재시도
    if failed_txs:
        print(f"\n\n🔄 실패한 거래 {len(failed_txs)}건 재시도 중...")
        retry_updated = 0
        for tx_hash in failed_txs[:]:  # 복사본으로 순회
            try:
                # 다시 조회하여 direction 계산
                tx_resp = supabase.table('whale_transactions')\
                    .select('tx_hash, from_label, to_label')\
                    .eq('tx_hash', tx_hash)\
                    .limit(1)\
                    .execute()
                
                if tx_resp.data:
                    tx = tx_resp.data[0]
                    direction = classify_direction(tx['from_label'], tx['to_label'])
                    if update_with_retry(supabase, tx_hash, direction, max_retries=5):
                        retry_updated += 1
                        failed_txs.remove(tx_hash)
            except:
                pass
            time.sleep(0.5)
        
        total_updated += retry_updated
        print(f"   재시도 성공: {retry_updated}건")
        if failed_txs:
            print(f"   최종 실패: {len(failed_txs)}건 (수동 확인 필요)")
    
    print(f"\n\n🎉 총 {total_updated:,}건의 거래 방향을 분류했습니다.")
    print("\n📌 이제 분석 스크립트를 다시 실행하세요:")
    print("   python3 scripts/analyze_top_picks.py")

if __name__ == '__main__':
    main()

