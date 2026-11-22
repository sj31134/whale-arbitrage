#!/usr/bin/env python3
"""
부족한 최신 시간별 데이터 수집
price_history_btc, price_history_eth 테이블의 최신 데이터를 수집합니다.
"""

import os
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict
import requests
from dotenv import load_dotenv
from supabase import create_client

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / 'config' / '.env')

BINANCE_API_BASE = 'https://api.binance.com/api/v3'

def get_supabase_client():
    """Supabase 클라이언트 생성"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY이 설정되지 않았습니다")
    
    return create_client(supabase_url, supabase_key)

def get_latest_timestamp(supabase, table_name):
    """테이블의 최신 타임스탬프 조회"""
    try:
        response = supabase.table(table_name)\
            .select('timestamp')\
            .order('timestamp', desc=True)\
            .limit(1)\
            .execute()
        
        if response.data:
            ts = response.data[0]['timestamp']
            return datetime.fromisoformat(ts.replace('Z', '+00:00'))
        else:
            return datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    except Exception as e:
        print(f"⚠️ 최신 타임스탬프 조회 실패: {e}")
        return datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

def fetch_binance_klines(symbol: str, start_time: datetime, end_time: datetime, interval: str = '1h') -> List[Dict]:
    """바이낸스 K-line 데이터 조회"""
    all_klines = []
    current_start = start_time
    
    print(f"  📊 {symbol} 수집 중...")
    print(f"     기간: {start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')} UTC")
    
    while current_start < end_time:
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': int(current_start.timestamp() * 1000),
                'endTime': int(end_time.timestamp() * 1000),
                'limit': 1000
            }
            
            response = requests.get(f'{BINANCE_API_BASE}/klines', params=params, timeout=30)
            
            if response.status_code != 200:
                print(f"     ⚠️ API 오류 (HTTP {response.status_code}): {response.text}")
                break
            
            klines = response.json()
            
            if not klines:
                break
            
            # K-line 데이터 파싱
            for k in klines:
                kline_data = {
                    'timestamp': datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
                    'open_price': float(k[1]),
                    'high_price': float(k[2]),
                    'low_price': float(k[3]),
                    'close_price': float(k[4]),
                    'volume': float(k[5]),
                    'close_time': datetime.fromtimestamp(k[6] / 1000, tz=timezone.utc),
                    'quote_volume': float(k[7]),
                    'trade_count': int(k[8]),
                    'taker_buy_volume': float(k[9]),
                    'taker_buy_quote_volume': float(k[10])
                }
                all_klines.append(kline_data)
            
            # 다음 시작 시간 설정
            last_timestamp = datetime.fromtimestamp(klines[-1][6] / 1000, tz=timezone.utc)
            if last_timestamp >= end_time:
                break
            
            current_start = last_timestamp
            
            # Rate limit 방지
            time.sleep(0.2)
            
        except Exception as e:
            print(f"     ❌ 오류: {e}")
            break
    
    print(f"     ✅ {len(all_klines)}건 수집 완료")
    return all_klines

def save_to_table(supabase, table_name: str, klines: List[Dict], coin_symbol: str) -> int:
    """데이터를 테이블에 저장"""
    if not klines:
        return 0
    
    saved_count = 0
    batch_size = 100
    
    for i in range(0, len(klines), batch_size):
        batch = klines[i:i+batch_size]
        
        records = []
        for kline in batch:
            record = {
                'id': str(uuid.uuid4()),
                'timestamp': kline['timestamp'].isoformat(),
                'coin_symbol': coin_symbol,
                'open_price': kline['open_price'],
                'high_price': kline['high_price'],
                'low_price': kline['low_price'],
                'close_price': kline['close_price'],
                'volume': kline['volume'],
                'quote_volume': kline['quote_volume'],
                'trade_count': kline['trade_count'],
                'taker_buy_volume': kline['taker_buy_volume'],
                'taker_buy_quote_volume': kline['taker_buy_quote_volume']
            }
            records.append(record)
        
        try:
            # 중복 체크
            skipped = 0
            errors = []
            for record in records:
                try:
                    # 해당 타임스탬프가 이미 있는지 확인
                    existing = supabase.table(table_name)\
                        .select('timestamp')\
                        .eq('timestamp', record['timestamp'])\
                        .limit(1)\
                        .execute()
                    
                    if not existing.data:
                        # 중복이 아니면 삽입
                        supabase.table(table_name).insert(record).execute()
                        saved_count += 1
                    else:
                        skipped += 1
                except Exception as insert_error:
                    # 개별 레코드 삽입 오류 기록
                    errors.append(str(insert_error))
            
            if skipped > 0:
                print(f"     ⏭️  {skipped}건 중복 스킵")
            if errors:
                print(f"     ⚠️ {len(errors)}건 저장 오류:")
                for err in errors[:3]:  # 처음 3개만 출력
                    print(f"        - {err}")
            
        except Exception as e:
            print(f"     ⚠️ 저장 오류: {e}")
    
    return saved_count

def collect_missing_data():
    """부족한 데이터 수집"""
    print("=" * 80)
    print("📊 부족한 최신 시간별 데이터 수집")
    print("=" * 80)
    
    try:
        supabase = get_supabase_client()
        current_time = datetime.now(timezone.utc)
        
        coins = [
            {'symbol': 'BTCUSDT', 'table': 'price_history_btc', 'coin_symbol': 'BTC'},
            {'symbol': 'ETHUSDT', 'table': 'price_history_eth', 'coin_symbol': 'ETH'}
        ]
        
        total_saved = 0
        
        for coin in coins:
            symbol = coin['symbol']
            table = coin['table']
            coin_symbol = coin['coin_symbol']
            
            print(f"\n{'='*80}")
            print(f"📈 {symbol} ({table})")
            print(f"{'='*80}")
            
            # 최신 타임스탬프 조회
            latest_ts = get_latest_timestamp(supabase, table)
            print(f"  최신 데이터: {latest_ts.strftime('%Y-%m-%d %H:%M')} UTC")
            
            # 부족한 데이터 수집
            if latest_ts < current_time:
                # 최신 타임스탬프 다음 시간부터 현재까지
                start_time = latest_ts
                end_time = current_time
                
                klines = fetch_binance_klines(symbol, start_time, end_time)
                
                if klines:
                    saved = save_to_table(supabase, table, klines, coin_symbol)
                    total_saved += saved
                    print(f"  💾 {saved}건 저장 완료")
                else:
                    print(f"  ⚠️ 수집된 데이터 없음")
            else:
                print(f"  ✅ 최신 데이터 이미 수집됨")
        
        print("\n" + "=" * 80)
        print("✅ 작업 완료")
        print("=" * 80)
        print(f"\n총 저장: {total_saved}건")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    collect_missing_data()

