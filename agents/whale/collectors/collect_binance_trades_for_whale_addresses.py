#!/usr/bin/env python3
"""
바이낸스에서 거래 기록을 수집하여 price_history에 저장하고,
whale_address에 있는 고래 지갑 주소의 거래 기록만 whale_transactions에 추가
"""

import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client
import requests
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

# 바이낸스 API 기본 URL
BINANCE_API_BASE = "https://api.binance.com/api/v3"

# whale_address에 정의된 9개 코인 (chain_type별)
# chain_type -> (cryptocurrencies symbol, binance symbol)
COINS_BY_CHAIN = {
    'BTC': ('BTC', 'BTCUSDT'),
    'ETH': ('ETH', 'ETHUSDT'),
    'LTC': ('LTC', 'LTCUSDT'),
    'DOGE': ('DOGE', 'DOGEUSDT'),
    'VTC': ('VTC', 'VTCUSDT'),
    'BSC': ('BNB', 'BNBUSDT'),  # BSC는 BNB로 매핑
    'DOT': ('DOT', 'DOTUSDT'),
    'LINK': ('LINK', 'LINKUSDT'),
    'SOL': ('SOL', 'SOLUSDT')
}

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def get_crypto_id_by_symbol(supabase, symbol: str) -> str:
    """심볼로 crypto_id 조회"""
    try:
        response = supabase.table('cryptocurrencies').select('id').eq('symbol', symbol).limit(1).execute()
        if response.data:
            return response.data[0]['id']
        return None
    except Exception as e:
        print(f"⚠️ crypto_id 조회 실패 ({symbol}): {e}")
        return None

def get_whale_addresses(supabase) -> Dict[str, List[str]]:
    """whale_address 테이블에서 고래 지갑 주소 조회 (chain_type별)"""
    try:
        response = supabase.table('whale_address').select('chain_type, address').execute()
        
        whale_addresses = {}
        for record in response.data:
            chain_type = record.get('chain_type')
            address = record.get('address')
            
            if chain_type and address:
                if chain_type not in whale_addresses:
                    whale_addresses[chain_type] = []
                whale_addresses[chain_type].append(address)
        
        print(f"✅ 고래 지갑 주소 조회 완료: {sum(len(addrs) for addrs in whale_addresses.values())}개")
        for chain, addrs in whale_addresses.items():
            print(f"   {chain}: {len(addrs)}개")
        
        return whale_addresses
    except Exception as e:
        print(f"❌ 고래 지갑 주소 조회 실패: {e}")
        return {}

def fetch_binance_klines(symbol: str, interval: str = '1h', limit: int = 500) -> List[Dict]:
    """바이낸스에서 K-line 데이터 조회"""
    url = f"{BINANCE_API_BASE}/klines"
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # 바이낸스 K-line 형식을 딕셔너리로 변환
        klines = []
        for k in data:
            klines.append({
                'open_time': datetime.fromtimestamp(k[0] / 1000),
                'open_price': float(k[1]),
                'high_price': float(k[2]),
                'low_price': float(k[3]),
                'close_price': float(k[4]),
                'volume': float(k[5]),
                'close_time': datetime.fromtimestamp(k[6] / 1000),
                'quote_volume': float(k[7]),
                'trade_count': int(k[8]),
                'taker_buy_volume': float(k[9]),
                'taker_buy_quote_volume': float(k[10]),
            })
        
        return klines
    except Exception as e:
        print(f"⚠️ 바이낸스 API 호출 실패 ({symbol}): {e}")
        return []

def save_to_price_history(supabase, crypto_id: str, klines: List[Dict], symbol: str) -> int:
    """price_history 테이블에 저장"""
    records = []
    
    for kline in klines:
        record = {
            'crypto_id': crypto_id,
            'timestamp': kline['open_time'].isoformat(),
            'open_price': str(kline['open_price']),
            'high_price': str(kline['high_price']),
            'low_price': str(kline['low_price']),
            'close_price': str(kline['close_price']),
            'volume': str(kline['volume']),
            'quote_volume': str(kline['quote_volume']),
            'trade_count': kline['trade_count'],
            'taker_buy_volume': str(kline['taker_buy_volume']),
            'taker_buy_quote_volume': str(kline['taker_buy_quote_volume']),
            'data_source': 'binance',
            'raw_data': {
                'open_time': kline['open_time'].isoformat(),
                'close_time': kline['close_time'].isoformat(),
            }
        }
        records.append(record)
    
    if not records:
        return 0
    
    # 배치로 저장 (중복 체크)
    saved_count = 0
    batch_size = 100
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            # upsert 사용 (id가 있으면 업데이트, 없으면 추가)
            response = supabase.table('price_history').upsert(batch).execute()
            saved_count += len(batch)
        except Exception as e:
            print(f"⚠️ price_history 저장 실패 (배치 {i//batch_size + 1}): {e}")
            # 개별 저장 시도
            for record in batch:
                try:
                    supabase.table('price_history').upsert([record]).execute()
                    saved_count += 1
                except:
                    pass
    
    return saved_count

def collect_binance_trades_for_coins(supabase):
    """9개 코인에 대해 바이낸스 거래 기록 수집"""
    print("=" * 70)
    print("📊 바이낸스 거래 기록 수집")
    print("=" * 70)
    
    total_saved = 0
    
    for chain_type, (crypto_symbol, binance_symbol) in COINS_BY_CHAIN.items():
        print(f"\n[{chain_type}] {binance_symbol} 수집 중...")
        
        # crypto_id 조회
        crypto_id = get_crypto_id_by_symbol(supabase, crypto_symbol)
        if not crypto_id:
            print(f"   ⚠️ {chain_type}의 crypto_id를 찾을 수 없습니다. cryptocurrencies 테이블에 추가하세요.")
            continue
        
        # 바이낸스에서 K-line 데이터 조회
        klines = fetch_binance_klines(binance_symbol, interval='1h', limit=500)
        if not klines:
            print(f"   ⚠️ {binance_symbol} 데이터를 가져올 수 없습니다.")
            continue
        
        print(f"   ✅ {len(klines)}건의 K-line 데이터 조회 완료")
        
        # price_history에 저장
        saved = save_to_price_history(supabase, crypto_id, klines, chain_type)
        total_saved += saved
        print(f"   ✅ {saved}건을 price_history에 저장 완료")
        
        # API rate limit 방지
        time.sleep(0.5)
    
    print(f"\n✅ 총 {total_saved}건의 거래 기록을 price_history에 저장했습니다.")
    return total_saved

def filter_whale_transactions_from_price_history(supabase, whale_addresses: Dict[str, List[str]]):
    """price_history에서 고래 지갑 주소의 거래 기록만 필터링하여 whale_transactions에 추가"""
    print("\n" + "=" * 70)
    print("🐋 고래 지갑 주소 거래 기록 필터링 및 whale_transactions 추가")
    print("=" * 70)
    
    # 주의: 바이낸스 API는 개별 주소의 거래 기록을 직접 제공하지 않습니다.
    # price_history는 시장 전체의 가격 데이터이므로, 
    # 실제 블록체인에서 고래 주소의 거래를 조회해야 합니다.
    
    print("\n⚠️  주의사항:")
    print("   - 바이낸스 API는 개별 지갑 주소의 거래 기록을 제공하지 않습니다.")
    print("   - price_history는 시장 전체의 가격 데이터입니다.")
    print("   - 고래 지갑 주소의 실제 거래 기록은 블록체인에서 조회해야 합니다.")
    print("   - (예: Etherscan API, BSCScan API 등)")
    
    print("\n💡 대안:")
    print("   1. 각 체인별 블록체인 탐색기 API 사용:")
    print("      - Ethereum: Etherscan API")
    print("      - BSC: BSCScan API")
    print("      - Bitcoin: BlockCypher API 또는 Blockchain.info API")
    print("   2. whale_transactions 테이블에 직접 거래 기록 추가")
    print("   3. price_history는 가격 데이터로만 사용")
    
    # 실제 구현은 블록체인별 API를 사용해야 합니다.
    # 여기서는 구조만 제시합니다.
    
    return 0

def main():
    """메인 함수"""
    supabase = get_supabase_client()
    
    # 1. 고래 지갑 주소 조회
    whale_addresses = get_whale_addresses(supabase)
    
    if not whale_addresses:
        print("❌ 고래 지갑 주소를 찾을 수 없습니다.")
        return
    
    # 2. 바이낸스에서 거래 기록 수집하여 price_history에 저장
    collect_binance_trades_for_coins(supabase)
    
    # 3. 고래 지갑 주소의 거래 기록 필터링 (블록체인 API 필요)
    # filter_whale_transactions_from_price_history(supabase, whale_addresses)
    
    print("\n" + "=" * 70)
    print("✅ 작업 완료")
    print("=" * 70)
    print("\n다음 단계:")
    print("1. 블록체인 탐색기 API를 사용하여 고래 지갑 주소의 실제 거래 기록 조회")
    print("2. 조회한 거래 기록을 whale_transactions 테이블에 추가")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

