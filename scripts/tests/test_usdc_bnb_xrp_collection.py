#!/usr/bin/env python3
"""
소규모 테스트: BNB 1일 데이터로 수집 및 저장 테스트
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client
import requests

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

from collect_price_history_for_usdc_bnb_xrp import (
    get_supabase_client,
    get_crypto_id_by_symbol,
    fetch_binance_klines_by_date_range,
    save_to_price_history
)

def test_small_collection():
    """BNB 1일 데이터로 테스트"""
    print("=" * 70)
    print("소규모 테스트: BNB 1일 데이터 수집")
    print("=" * 70)
    
    # 2025년 5월 1일 하루만 테스트
    start_date = datetime(2025, 5, 1, 0, 0, 0)
    end_date = datetime(2025, 5, 1, 23, 59, 59)
    
    print(f"\n테스트 기간: {start_date.strftime('%Y-%m-%d %H:%M:%S')} ~ {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        supabase = get_supabase_client()
        
        # crypto_id 조회
        print("\n[1단계] BNB의 crypto_id 조회 중...")
        crypto_id = get_crypto_id_by_symbol(supabase, 'BNB')
        if not crypto_id:
            print("❌ BNB의 crypto_id를 찾을 수 없습니다.")
            return
        print(f"✅ crypto_id: {crypto_id}")
        
        # 바이낸스에서 데이터 조회
        print("\n[2단계] 바이낸스 API에서 데이터 조회 중...")
        klines = fetch_binance_klines_by_date_range(
            'BNBUSDT',
            start_date,
            end_date,
            interval='1h'
        )
        
        if not klines:
            print("❌ 데이터를 가져올 수 없습니다.")
            return
        
        print(f"✅ {len(klines)}건의 K-line 데이터 조회 완료")
        print(f"\n수집된 데이터 샘플 (최대 5개):")
        for i, kline in enumerate(klines[:5], 1):
            print(f"  {i}. {kline['open_time'].strftime('%Y-%m-%d %H:%M')} - Open: {kline['open_price']:.4f}, Close: {kline['close_price']:.4f}")
        
        # price_history에 저장
        print(f"\n[3단계] price_history 테이블에 저장 중...")
        saved = save_to_price_history(supabase, crypto_id, klines, 'BNB')
        print(f"✅ {saved}건 저장 완료")
        
        # 저장된 데이터 확인
        print(f"\n[4단계] 저장된 데이터 확인 중...")
        response = supabase.table('price_history').select('*', count='exact').eq('crypto_id', crypto_id).gte('timestamp', start_date.isoformat()).lte('timestamp', end_date.isoformat()).execute()
        count = response.count if hasattr(response, 'count') else len(response.data)
        print(f"✅ price_history 테이블에 {count}건 확인")
        
        if response.data:
            print(f"\n저장된 데이터 샘플 (최대 3개):")
            for i, record in enumerate(response.data[:3], 1):
                print(f"  {i}. {record.get('timestamp', 'N/A')} - Open: {record.get('open_price', 'N/A')}, Close: {record.get('close_price', 'N/A')}")
        
        print("\n" + "=" * 70)
        print("✅ 테스트 완료")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_small_collection()

