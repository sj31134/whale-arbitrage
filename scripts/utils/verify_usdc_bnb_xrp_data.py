#!/usr/bin/env python3
"""
USDC, BNB, XRP 데이터 검증 스크립트
"""

import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / 'config' / '.env')

def verify_collected_data():
    """수집된 데이터 검증"""
    print("=" * 70)
    print("📊 USDC, BNB, XRP 데이터 검증")
    print("=" * 70)
    
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
    
    # 검증 기간
    start_date = datetime(2025, 5, 1, 0, 0, 0)
    end_date = datetime(2025, 6, 30, 23, 59, 59)
    
    coins = {
        'USDC': '39b8e112-a234-4030-a79d-9a63470da26c',
        'BNB': 'c4796bce-0c74-49cd-9822-1b0b6990e14b',
        'XRP': '71730de3-6fe8-447a-a7a6-e5cb880f9a18'
    }
    
    print(f"\n검증 기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
    print("=" * 70)
    
    total_count = 0
    
    for coin_name, crypto_id in coins.items():
        print(f"\n[{coin_name}] 데이터 확인 중...")
        
        # 전체 건수 확인
        response = supabase.table('price_history').select('*', count='exact').eq('crypto_id', crypto_id).eq('data_source', 'binance').gte('timestamp', start_date.isoformat()).lte('timestamp', end_date.isoformat()).execute()
        
        count = response.count if hasattr(response, 'count') else len(response.data)
        total_count += count
        
        print(f"   ✅ {count}건 확인")
        
        if count > 0:
            # 최소/최대 타임스탬프 확인
            timestamps = [record.get('timestamp') for record in response.data if record.get('timestamp')]
            if timestamps:
                min_ts = min(timestamps)
                max_ts = max(timestamps)
                print(f"   📅 기간: {min_ts} ~ {max_ts}")
            
            # 샘플 데이터 확인
            sample = response.data[0] if response.data else None
            if sample:
                print(f"   📊 샘플 데이터:")
                print(f"      - Open: {sample.get('open_price', 'N/A')}")
                print(f"      - Close: {sample.get('close_price', 'N/A')}")
                print(f"      - Volume: {sample.get('volume', 'N/A')}")
        
        # 예상 건수와 비교 (61일 × 24시간 = 1,464건)
        expected_count = 1464
        if count >= expected_count * 0.95:  # 95% 이상이면 성공
            print(f"   ✅ 예상 건수 대비 충족: {count}/{expected_count} ({count/expected_count*100:.1f}%)")
        else:
            print(f"   ⚠️  예상 건수 대비 부족: {count}/{expected_count} ({count/expected_count*100:.1f}%)")
    
    print("\n" + "=" * 70)
    print("✅ 검증 완료")
    print("=" * 70)
    print(f"\n총 저장된 데이터: {total_count}건")
    print(f"예상 총 건수: {1464 * 3}건 (3개 코인 × 1,464건)")
    
    if total_count >= 1464 * 3 * 0.95:
        print(f"✅ 전체 데이터 수집 성공: {total_count}/{1464 * 3} ({total_count/(1464*3)*100:.1f}%)")
    else:
        print(f"⚠️  일부 데이터 누락 가능: {total_count}/{1464 * 3} ({total_count/(1464*3)*100:.1f}%)")

if __name__ == '__main__':
    verify_collected_data()

