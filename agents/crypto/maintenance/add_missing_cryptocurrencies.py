#!/usr/bin/env python3
"""cryptocurrencies 테이블에 누락된 코인 추가"""

import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / 'config' / '.env')

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

# 추가할 코인 목록
COINS_TO_ADD = [
    {'symbol': 'BTC', 'name': 'Bitcoin', 'binance_symbol': 'BTCUSDT'},
    {'symbol': 'ETH', 'name': 'Ethereum', 'binance_symbol': 'ETHUSDT'},
    {'symbol': 'LTC', 'name': 'Litecoin', 'binance_symbol': 'LTCUSDT'},
    {'symbol': 'DOGE', 'name': 'Dogecoin', 'binance_symbol': 'DOGEUSDT'},
    {'symbol': 'VTC', 'name': 'Vertcoin', 'binance_symbol': 'VTCUSDT'},
    {'symbol': 'BNB', 'name': 'Binance Coin', 'binance_symbol': 'BNBUSDT'},  # BSC
    {'symbol': 'DOT', 'name': 'Polkadot', 'binance_symbol': 'DOTUSDT'},
    {'symbol': 'LINK', 'name': 'Chainlink', 'binance_symbol': 'LINKUSDT'},
    {'symbol': 'SOL', 'name': 'Solana', 'binance_symbol': 'SOLUSDT'},
]

def add_missing_cryptocurrencies():
    """누락된 코인 추가"""
    supabase = get_supabase_client()
    
    print("=" * 70)
    print("📊 cryptocurrencies 테이블에 누락된 코인 추가")
    print("=" * 70)
    
    added_count = 0
    existing_count = 0
    
    for coin in COINS_TO_ADD:
        symbol = coin['symbol']
        name = coin['name']
        binance_symbol = coin['binance_symbol']
        
        # 이미 존재하는지 확인
        try:
            response = supabase.table('cryptocurrencies').select('id').eq('symbol', symbol).execute()
            if response.data:
                print(f"   ✅ {symbol} ({name}): 이미 존재함")
                existing_count += 1
                continue
        except Exception as e:
            print(f"   ⚠️ {symbol} 확인 중 오류: {e}")
        
        # 추가
        try:
            record = {
                'symbol': symbol,
                'name': name,
                'binance_symbol': binance_symbol,
                'is_active': True
            }
            
            response = supabase.table('cryptocurrencies').insert(record).execute()
            if response.data:
                print(f"   ✅ {symbol} ({name}): 추가 완료")
                added_count += 1
            else:
                print(f"   ⚠️ {symbol} ({name}): 추가 실패")
        except Exception as e:
            print(f"   ⚠️ {symbol} ({name}) 추가 중 오류: {e}")
    
    print("\n" + "=" * 70)
    print(f"✅ 완료: {added_count}개 추가, {existing_count}개 이미 존재")
    print("=" * 70)

if __name__ == '__main__':
    try:
        add_missing_cryptocurrencies()
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()



